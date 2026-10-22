"""
==============================================================================
File: backend/app/services/extraction.py
Purpose: Structured Product Extraction orchestrator with citation verification
         and confidence score validation.
Architecture: Backend Services Layer / Extraction Engine
==============================================================================

Grounding Guardrails:
LLMs can occasionally fabricate plausible-sounding policy limits or hallucinate
quotes. Our ExtractionService incorporates a programmatic citation verifier:
1. Every extracted `exact_quote` is checked against the raw text of the document chunks.
2. If the quote is missing or mutated, the confidence score is slashed to 0.40,
   and the item is automatically flagged with `needs_review = True`.
3. If an insurance term is genuinely absent from the document, the model is strictly
   instructed to return null or an empty list.
"""

import json
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentChunk
from app.models.extraction import ProductExtractionRecord
from app.schemas.product import (
    StructuredProductExtraction, ProductExtractionResponse, CoverageItem,
    DeductibleItem, RatingFactorItem, UnderwritingRuleItem, ExclusionItem,
    EndorsementItem
)
from app.schemas.citation import Citation
from app.services.llm.base import LLMProvider, StructuredLLMResponse


class ExtractionService:
    """
    Orchestrates the extraction of structured insurance product models from chunks,
    validates verbatim citations, and persists extraction results.
    """

    def __init__(self, llm_provider: LLMProvider):
        """
        Initializes the service with an injected LLM provider (Gemini or Mock).
        """
        self.llm = llm_provider

    def extract_product(self, document_id: str, db: Session) -> ProductExtractionResponse:
        """
        Runs structured product extraction on the specified document.

        Args:
            document_id: UUID of the ingested document.
            db: Active SQLAlchemy database session.

        Returns:
            ProductExtractionResponse: Validated product data, citations, and cost telemetry.

        Raises:
            ValueError: If document or chunks do not exist.
        """
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            raise ValueError(f"Document '{document_id}' not found.")

        chunks = (
            db.query(DocumentChunk)
            .filter(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index.asc())
            .all()
        )
        if not chunks:
            raise ValueError(f"No semantic chunks found for document '{document_id}'.")

        # Compile full chunk text map for citation verification: {page_num: full_text}
        page_text_map: Dict[int, str] = {}
        for c in chunks:
            page_text_map[c.page_number] = page_text_map.get(c.page_number, "") + "\n" + c.text_content

        # Assemble prompt with indexed chunks
        chunk_snippets = []
        for c in chunks:
            ref_str = f" [Clause: {c.clause_reference}]" if c.clause_reference else ""
            chunk_snippets.append(
                f"--- CHUNK {c.chunk_index} (Page {c.page_number}, Section: '{c.section_title}'{ref_str}) ---\n"
                f"{c.text_content}"
            )
        document_context = "\n\n".join(chunk_snippets)

        prompt = (
            f"You are a senior insurance product analyst. Ingest the following insurance product document "
            f"and extract structured product specifications into the required schema.\n\n"
            f"DOCUMENT TITLE: {doc.filename}\n"
            f"LINE OF BUSINESS HINT: {doc.line_of_business or 'Unknown'}\n\n"
            f"DOCUMENT TEXT CHUNKS:\n"
            f"{document_context}\n\n"
            f"EXTRACTION GUARDRAILS:\n"
            f"1. Extract: product_name, line_of_business, state_or_jurisdiction, effective_date, "
            f"coverages, deductibles, rating_factors, underwriting_rules, exclusions, endorsements.\n"
            f"2. CITATION MANDATE: Every single item MUST carry a Citation object with:\n"
            f"   - page_number (integer)\n"
            f"   - clause_reference (string)\n"
            f"   - exact_quote (must be a verbatim quote from the text above!)\n"
            f"   - confidence_score (float 0.0 to 1.0)\n"
            f"3. ABSOLUTE TRUTHFULNESS: If any field (e.g., deductibles, rating factors, endorsements) "
            f"is NOT specified in the document, return null or an empty list. NEVER invent or assume."
        )

        system_instruction = (
            "You are an insurance actuarial and underwriting specification system. "
            "You extract strictly grounded product artifacts without hallucination."
        )

        # Call LLM Provider for structured JSON
        response: StructuredLLMResponse = self.llm.generate_structured(
            prompt=prompt,
            response_schema=StructuredProductExtraction,
            system_instruction=system_instruction,
            temperature=0.0
        )

        extracted_data: StructuredProductExtraction = response.data

        # Programmatic Citation Verification
        needs_review_count = self._verify_citations(extracted_data, page_text_map)

        # Persist or update extraction in database
        status_flag = "needs_review" if needs_review_count > 0 else "completed"
        existing_record = (
            db.query(ProductExtractionRecord)
            .filter(ProductExtractionRecord.document_id == document_id)
            .first()
        )

        raw_json_str = extracted_data.model_dump_json()

        if existing_record:
            existing_record.status = status_flag
            existing_record.model_name = response.model_name
            existing_record.prompt_tokens = response.prompt_tokens
            existing_record.completion_tokens = response.completion_tokens
            existing_record.cost_usd = response.cost_usd
            existing_record.needs_review_count = needs_review_count
            existing_record.raw_json = raw_json_str
            record = existing_record
        else:
            record = ProductExtractionRecord(
                document_id=document_id,
                status=status_flag,
                model_name=response.model_name,
                prompt_tokens=response.prompt_tokens,
                completion_tokens=response.completion_tokens,
                cost_usd=response.cost_usd,
                needs_review_count=needs_review_count,
                raw_json=raw_json_str
            )
            db.add(record)

        # Update document status to 'extracted'
        doc.status = "extracted"
        db.commit()
        db.refresh(record)

        return ProductExtractionResponse(
            id=record.id,
            document_id=record.document_id,
            status=record.status,
            model_name=record.model_name,
            prompt_tokens=record.prompt_tokens,
            completion_tokens=record.completion_tokens,
            cost_usd=record.cost_usd,
            needs_review_count=record.needs_review_count,
            data=extracted_data
        )

    def _verify_citations(
        self,
        extraction: StructuredProductExtraction,
        page_text_map: Dict[int, str]
    ) -> int:
        """
        Validates all citation quotes against actual page text.
        Returns the number of citations flagged for review.
        """
        flagged_count = 0

        def check_citation(citation: Citation):
            nonlocal flagged_count
            quote_clean = citation.exact_quote.strip().lower()
            page_text = page_text_map.get(citation.page_number, "").lower()

            # Verify if quote snippet exists on claimed page or anywhere in document
            if quote_clean in page_text:
                citation.confidence_score = max(citation.confidence_score, 0.95)
                citation.needs_review = False
            else:
                # Check document-wide in case page number was slightly misattributed
                found_anywhere = any(quote_clean in text.lower() for text in page_text_map.values())
                if found_anywhere:
                    citation.confidence_score = 0.80
                    citation.needs_review = False
                else:
                    # Quote could not be verified verbatim -> flag for human reviewer
                    citation.confidence_score = 0.40
                    citation.needs_review = True
                    flagged_count += 1

        # Check top-level citations
        check_citation(extraction.product_name.citation)
        check_citation(extraction.line_of_business.citation)
        check_citation(extraction.state_or_jurisdiction.citation)
        if extraction.effective_date:
            check_citation(extraction.effective_date.citation)

        # Check list citations
        for item in extraction.coverages:
            check_citation(item.citation)
        for item in extraction.deductibles:
            check_citation(item.citation)
        for item in extraction.rating_factors:
            check_citation(item.citation)
        for item in extraction.underwriting_rules:
            check_citation(item.citation)
        for item in extraction.exclusions:
            check_citation(item.citation)
        for item in extraction.endorsements:
            check_citation(item.citation)

        return flagged_count
