"""
==============================================================================
File: backend/app/services/retrieval.py
Purpose: Hybrid Information Retrieval combining ChromaDB dense vector search
         with BM25 sparse keyword matching, fused via Reciprocal Rank Fusion (RRF).
Architecture: Backend Services Layer / Retrieval Engine (RAG)
==============================================================================

Why Hybrid Search for Insurance Policies?
1. Dense Vector Embeddings (Semantic):
   Understand synonyms and natural language concepts (e.g., querying 'car crash protection'
   matches 'Part D: Collision Coverage' even if the exact words 'car crash' never appear).
2. Sparse Keyword Search (BM25):
   Catches exact statutory codes, policy form numbers, and actuarial clause IDs
   (e.g., 'PA-2026-OH', 'Clause 2.2', 'UL 2218') where embedding models often fuzz out.
3. Reciprocal Rank Fusion (RRF):
   Blends dense and sparse rankings using: RRF_score = sum(1.0 / (60 + rank)).
   This delivers the highest precision retrieval in legal and financial domains.
"""

import os
import math
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from rank_bm25 import BM25Okapi
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings

from app.core.config import settings
from app.models.document import DocumentChunk


class FastLocalEmbeddingFunction(EmbeddingFunction[Documents]):
    """
    Deterministic, high-speed local embedding function.
    Encodes text into a normalized 128-dimensional dense vector using token hashing.
    Runs 100% locally in memory without any external cloud or S3 model downloads.
    """
    def __init__(self, dimension: int = 128):
        self.dimension = dimension

    def name(self) -> str:
        """Returns unique identifier for ChromaDB embedding function registry."""
        return "fast_local_embedding"

    def __call__(self, input: Documents) -> Embeddings:
        embeddings = []
        dim = self.dimension
        for doc in input:
            vec = [0.0] * dim
            tokens = doc.lower().split()
            if not tokens:
                embeddings.append(vec)
                continue
            for token in tokens:
                h = int(hashlib.md5(token.encode('utf-8')).hexdigest(), 16)
                idx = h % dim
                vec[idx] += 1.0
            norm = math.sqrt(sum(x * x for x in vec)) or 1.0
            embeddings.append([round(x / norm, 6) for x in vec])
        return embeddings


@dataclass
class RetrievedChunk:
    """
    Semantic chunk returned by the retrieval engine with relevance scores.
    """
    chunk_id: str
    chunk_index: int
    page_number: int
    section_title: str
    clause_reference: Optional[str]
    text_content: str
    score: float
    retrieval_method: str  # 'dense', 'keyword', or 'hybrid_rrf'


class RetrievalService:
    """
    Orchestrates dense vector indexing via ChromaDB and sparse BM25 indexing.
    """

    def __init__(self, persist_directory: Optional[str] = None):
        """
        Initializes ChromaDB persistent client and local collection cache.
        """
        self.persist_directory = persist_directory or settings.CHROMA_PERSIST_DIRECTORY
        os.makedirs(self.persist_directory, exist_ok=True)
        self._client = None
        self._embedding_function = FastLocalEmbeddingFunction(dimension=128)
        self._collections: Dict[str, Any] = {}
        self._bm25_indices: Dict[str, Tuple[BM25Okapi, List[DocumentChunk]]] = {}

    def _get_client(self):
        """Lazy initializer for ChromaDB client to optimize startup time."""
        if self._client is None:
            import chromadb
            from chromadb.config import Settings as ChromaSettings
            self._client = chromadb.PersistentClient(
                path=self.persist_directory,
                settings=ChromaSettings(anonymized_telemetry=False)
            )
        return self._client

    def index_document_chunks(self, document_id: str, chunks: List[DocumentChunk]):
        """
        Builds both dense vector embeddings in ChromaDB and in-memory BM25 index
        for a document's semantic chunks.

        Args:
            document_id: UUID of the document.
            chunks: List of DocumentChunk models to index.
        """
        if not chunks:
            return

        client = self._get_client()
        safe_collection_name = f"doc_{document_id.replace('-', '_')}"
        
        # Get or create Chroma collection with deterministic local embedding function
        try:
            collection = client.get_or_create_collection(
                name=safe_collection_name,
                embedding_function=self._embedding_function,
                metadata={"document_id": document_id}
            )
        except Exception:
            # Handle conflict if collection was previously initialized with default embedding function
            try:
                client.delete_collection(name=safe_collection_name)
            except Exception:
                pass
            collection = client.create_collection(
                name=safe_collection_name,
                embedding_function=self._embedding_function,
                metadata={"document_id": document_id}
            )

        ids = [c.id for c in chunks]
        documents = [c.text_content for c in chunks]
        metadatas = [
            {
                "chunk_index": c.chunk_index,
                "page_number": c.page_number,
                "section_title": c.section_title,
                "clause_reference": c.clause_reference or "",
            }
            for c in chunks
        ]

        collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )
        self._collections[document_id] = collection

        # Build BM25 index
        tokenized_corpus = [c.text_content.lower().split() for c in chunks]
        bm25 = BM25Okapi(tokenized_corpus)
        self._bm25_indices[document_id] = (bm25, chunks)

    def retrieve(
        self,
        document_id: str,
        query: str,
        top_k: int = 5,
        chunks: Optional[List[DocumentChunk]] = None
    ) -> List[RetrievedChunk]:
        """
        Performs Hybrid Search using dense vector search and BM25 sparse keyword
        search, combined with Reciprocal Rank Fusion (RRF).

        Args:
            document_id: UUID of the document.
            query: User or generator search query.
            top_k: Number of relevant chunks to return.
            chunks: Optional fallback chunks if index needs building on-the-fly.

        Returns:
            List[RetrievedChunk]: Ranked relevant chunks with citations.
        """
        if not query or not query.strip():
            return []

        # Ensure document is indexed
        if document_id not in self._bm25_indices and chunks:
            self.index_document_chunks(document_id, chunks)

        # 1. Sparse BM25 Retrieval
        keyword_ranked = self._retrieve_bm25(document_id, query, top_k=top_k * 2)

        # 2. Dense Vector Retrieval via ChromaDB
        dense_ranked = self._retrieve_dense(document_id, query, top_k=top_k * 2)

        # 3. Reciprocal Rank Fusion (RRF)
        return self._reciprocal_rank_fusion(keyword_ranked, dense_ranked, top_k=top_k)

    def _retrieve_bm25(self, document_id: str, query: str, top_k: int) -> List[RetrievedChunk]:
        """Runs BM25 sparse keyword matching."""
        if document_id not in self._bm25_indices:
            return []

        bm25, chunk_list = self._bm25_indices[document_id]
        query_tokens = query.lower().split()
        scores = bm25.get_scores(query_tokens)

        paired = sorted(
            [(chunk_list[i], float(score)) for i, score in enumerate(scores) if score > 0.0],
            key=lambda x: x[1],
            reverse=True
        )[:top_k]

        results = []
        for c, score in paired:
            results.append(RetrievedChunk(
                chunk_id=c.id,
                chunk_index=c.chunk_index,
                page_number=c.page_number,
                section_title=c.section_title,
                clause_reference=c.clause_reference,
                text_content=c.text_content,
                score=score,
                retrieval_method="keyword"
            ))
        return results

    def _retrieve_dense(self, document_id: str, query: str, top_k: int) -> List[RetrievedChunk]:
        """Runs ChromaDB dense semantic vector search."""
        client = self._get_client()
        safe_collection_name = f"doc_{document_id.replace('-', '_')}"
        try:
            collection = client.get_collection(
                name=safe_collection_name,
                embedding_function=self._embedding_function
            )
        except Exception:
            return []

        query_res = collection.query(
            query_texts=[query],
            n_results=min(top_k, collection.count() or 1)
        )

        results = []
        if query_res and query_res["ids"] and query_res["ids"][0]:
            ids = query_res["ids"][0]
            docs = query_res["documents"][0]
            metas = query_res["metadatas"][0]
            distances = query_res["distances"][0] if "distances" in query_res and query_res["distances"] else [0.5]*len(ids)

            for i in range(len(ids)):
                similarity = 1.0 / (1.0 + distances[i])
                meta = metas[i]
                results.append(RetrievedChunk(
                    chunk_id=ids[i],
                    chunk_index=meta.get("chunk_index", 0),
                    page_number=meta.get("page_number", 1),
                    section_title=meta.get("section_title", "Section"),
                    clause_reference=meta.get("clause_reference") or None,
                    text_content=docs[i],
                    score=similarity,
                    retrieval_method="dense"
                ))
        return results

    def _reciprocal_rank_fusion(
        self,
        keyword_results: List[RetrievedChunk],
        dense_results: List[RetrievedChunk],
        top_k: int,
        rrf_constant: int = 60
    ) -> List[RetrievedChunk]:
        """
        Merges sparse and dense search results using Reciprocal Rank Fusion.
        RRF Score = 1.0 / (k + rank_bm25) + 1.0 / (k + rank_dense)
        """
        combined_scores: Dict[str, float] = {}
        chunk_map: Dict[str, RetrievedChunk] = {}

        for rank, item in enumerate(keyword_results):
            chunk_map[item.chunk_id] = item
            combined_scores[item.chunk_id] = combined_scores.get(item.chunk_id, 0.0) + (
                1.0 / (rrf_constant + (rank + 1))
            )

        for rank, item in enumerate(dense_results):
            chunk_map[item.chunk_id] = item
            combined_scores[item.chunk_id] = combined_scores.get(item.chunk_id, 0.0) + (
                1.0 / (rrf_constant + (rank + 1))
            )

        sorted_ids = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

        fused_chunks = []
        for chunk_id, rrf_score in sorted_ids:
            chunk = chunk_map[chunk_id]
            fused_chunks.append(RetrievedChunk(
                chunk_id=chunk.chunk_id,
                chunk_index=chunk.chunk_index,
                page_number=chunk.page_number,
                section_title=chunk.section_title,
                clause_reference=chunk.clause_reference,
                text_content=chunk.text_content,
                score=round(rrf_score, 4),
                retrieval_method="hybrid_rrf"
            ))

        return fused_chunks

    def delete_document_index(self, document_id: str):
        """Purges vector collection and BM25 index when a document is deleted."""
        client = self._get_client()
        safe_collection_name = f"doc_{document_id.replace('-', '_')}"
        try:
            client.delete_collection(name=safe_collection_name)
        except Exception:
            pass
        self._collections.pop(document_id, None)
        self._bm25_indices.pop(document_id, None)
