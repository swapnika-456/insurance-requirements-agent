"""
==============================================================================
File: backend/app/api/v1/traceability.py
Purpose: RESTful API controller endpoints for generating, querying, and
         exporting the Traceability Matrix and Gap Analysis.
Architecture: Backend API Controllers / Traceability Endpoints
==============================================================================
"""

import json
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_traceability_service
from app.models.traceability import TraceabilityRecord
from app.schemas.traceability import (
    TraceabilityMatrixResponse, ProductDataModel, APIContract,
    TraceabilityRow, GapReport
)
from app.services.traceability import TraceabilityService

router = APIRouter(prefix="/traceability", tags=["Traceability Matrix & Gap Analysis"])


@router.post(
    "/{document_id}/generate",
    response_model=TraceabilityMatrixResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate Bidirectional Traceability Matrix, Data Model, API Contract, and Gap Report"
)
def generate_traceability(
    document_id: str,
    db: Session = Depends(get_db),
    traceability_service: TraceabilityService = Depends(get_traceability_service)
):
    """
    Constructs the end-to-end traceability matrix:
    1. Maps REQ -> User Story -> Data Model Element -> API Endpoint -> Source Clause.
    2. Runs graph gap detection for uncovered clauses and orphan requirements.
    3. Computes statutory coverage percentage.
    """
    try:
        return traceability_service.generate_traceability(document_id=document_id, db=db)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Traceability generation failed: {str(e)}"
        )


@router.get(
    "/{document_id}",
    response_model=TraceabilityMatrixResponse,
    summary="Get existing Traceability Matrix and Gap Report for a document"
)
def get_traceability(
    document_id: str,
    db: Session = Depends(get_db),
    traceability_service: TraceabilityService = Depends(get_traceability_service)
):
    """Retrieves existing traceability matrix or generates it on-demand."""
    record = (
        db.query(TraceabilityRecord)
        .filter(TraceabilityRecord.document_id == document_id)
        .first()
    )
    if not record:
        # Generate on-demand if not yet materialized
        return traceability_service.generate_traceability(document_id=document_id, db=db)

    data_model = ProductDataModel.model_validate_json(record.data_model_json)
    api_contract = APIContract.model_validate_json(record.api_contract_json)
    raw_rows = json.loads(record.matrix_json)
    matrix = [TraceabilityRow.model_validate(r) for r in raw_rows]
    gap_report = GapReport.model_validate_json(record.gap_report_json)

    return TraceabilityMatrixResponse(
        id=record.id,
        document_id=record.document_id,
        status=record.status,
        data_model=data_model,
        api_contract=api_contract,
        matrix=matrix,
        gap_report=gap_report
    )


@router.get(
    "/{document_id}/export",
    summary="Export Traceability Matrix as a CSV file"
)
def export_traceability_csv(
    document_id: str,
    db: Session = Depends(get_db),
    traceability_service: TraceabilityService = Depends(get_traceability_service)
):
    """
    Exports the complete traceability matrix and gap analysis summary as an RFC-4180 CSV file.
    """
    try:
        csv_content = traceability_service.export_matrix_csv(document_id=document_id, db=db)
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=traceability_matrix_{document_id[:8]}.csv"
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"CSV export failed: {str(e)}"
        )
