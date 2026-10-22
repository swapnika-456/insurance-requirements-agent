"""
==============================================================================
File: backend/tests/test_retrieval.py
Purpose: Unit and integration tests for Hybrid Retrieval (ChromaDB + BM25 + RRF).
Architecture: Backend Testing Suite / Retrieval Tests
==============================================================================
"""

import pytest
from app.services.retrieval import RetrievalService
from app.services.ingestion import IngestionService
from app.models.document import DocumentChunk


def test_hybrid_retrieval_indexing_and_search(sample_pdf_paths):
    """
    Verifies indexing chunks into ChromaDB and BM25, and executing hybrid search
    with Reciprocal Rank Fusion.
    """
    # 1. Ingest sample auto policy to get real chunks
    ingest_svc = IngestionService()
    with open(sample_pdf_paths["auto"], "rb") as f:
        ingest_res = ingest_svc.ingest_pdf_bytes(f.read(), "sample_auto.pdf")

    # Convert to DocumentChunk objects
    chunks = [
        DocumentChunk(
            id=f"chk-{i}",
            document_id="doc-test-123",
            chunk_index=c.chunk_index,
            page_number=c.page_number,
            section_title=c.section_title,
            clause_reference=c.clause_reference,
            text_content=c.text_content,
            token_count=c.token_count
        )
        for i, c in enumerate(ingest_res.chunks)
    ]

    retrieval_svc = RetrievalService(persist_directory="./data/test_chroma")
    retrieval_svc.index_document_chunks("doc-test-123", chunks)

    # Search for Collision deductible
    results = retrieval_svc.retrieve("doc-test-123", "collision deductible amount", top_k=3)
    assert len(results) > 0
    assert any("500" in r.text_content or "collision" in r.text_content.lower() for r in results)
    assert all(r.retrieval_method == "hybrid_rrf" for r in results)

    # Search for rating factors
    rf_results = retrieval_svc.retrieve("doc-test-123", "driver age rating factor RF-1", top_k=3)
    assert len(rf_results) > 0
    assert any("RF-1" in r.text_content or "age" in r.text_content.lower() for r in rf_results)

    # Clean up test collection
    retrieval_svc.delete_document_index("doc-test-123")


def test_empty_query_retrieval():
    """Verifies that empty query returns empty list without error."""
    retrieval_svc = RetrievalService(persist_directory="./data/test_chroma")
    results = retrieval_svc.retrieve("non-existent-doc", "")
    assert results == []
