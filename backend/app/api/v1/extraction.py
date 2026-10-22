"""
==============================================================================
File: backend/app/api/v1/extraction.py
Purpose: RESTful API controller endpoints for Structured Product Extraction.
Architecture: Backend API Controllers / Extraction Endpoints
==============================================================================
"""

import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_extraction_service
from app.models.document import Document
from app.models.extraction import ProductExtractionRecord
from app.schemas.product import ProductExtractionResponse, StructuredProductExtraction
from app.services.extraction import ExtractionService

router = APIRouter(prefix="/extractions", tags=["Product Extraction"])


@router.post(
    "/{document_id}",
    response_model=ProductExtractionResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger structured product extraction on an ingested document"
)
def run_extraction(
    document_id: str,
    db: Session = Depends(get_db),
    extraction_service: ExtractionService = Depends(get_extraction_service)
):
    """
    Executes grounded structured extraction using Pydantic schema enforcement:
    1. Gathers all semantic chunks for the document.
    2. Extracts coverages, limits, deductibles, rating factors, rules, exclusions, endorsements.
    3. Validates that every citation has a verbatim quote from the source text.
    4. Computes token usage, latency, and USD cost.
    5. Flags items requiring human review if confidence < 0.75.
    """
    try:
        return extraction_service.extract_product(document_id=document_id, db=db)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Extraction failure: {str(e)}"
        )


@router.get(
    "/{document_id}",
    response_model=ProductExtractionResponse,
    summary="Get previously extracted structured product data for a document"
)
def get_extraction(
    document_id: str,
    db: Session = Depends(get_db)
):
    """Retrieves existing product extraction data from SQLite."""
    record = (
        db.query(ProductExtractionRecord)
        .filter(ProductExtractionRecord.document_id == document_id)
        .first()
    )
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No extraction found for document '{document_id}'. Run POST /api/v1/extractions/{document_id} first."
        )

    parsed_data = StructuredProductExtraction.model_validate_json(record.raw_json)

    return ProductExtractionResponse(
        id=record.id,
        document_id=record.document_id,
        status=record.status,
        model_name=record.model_name,
        prompt_tokens=record.prompt_tokens,
        completion_tokens=record.completion_tokens,
        cost_usd=record.cost_usd,
        needs_review_count=record.needs_review_count,
        data=parsed_data
    )
