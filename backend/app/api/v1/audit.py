"""
==============================================================================
File: backend/app/api/v1/audit.py
Purpose: REST API endpoints for Human-in-the-Loop review actions, audit logging,
         token usage accounting, and CSV compliance export.
Architecture: Backend API Layer / Governance Endpoints
==============================================================================
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.services.audit import AuditService
from app.schemas.audit import (
    ReviewActionRequest,
    ReviewActionResponse,
    AuditLogEntry,
    CostSummaryResponse
)

router = APIRouter(prefix="", tags=["Audit & Review"])
audit_service = AuditService()


@router.post(
    "/review/decision",
    response_model=ReviewActionResponse,
    summary="Record human reviewer decision (Approve / Reject / Edit)"
)
def record_review_decision(
    request: ReviewActionRequest,
    db: Session = Depends(get_db)
):
    """
    Records an underwriter's approval, rejection, or edit on a requirement,
    user story, or extraction item, persisting state changes and audit events.
    """
    return audit_service.apply_review_decision(db=db, request=request)


@router.get(
    "/audit/logs",
    response_model=List[AuditLogEntry],
    summary="List immutable audit trail events"
)
def list_audit_logs(
    document_id: Optional[str] = Query(None, description="Filter by document ID"),
    action: Optional[str] = Query(None, description="Filter by action type"),
    actor: Optional[str] = Query(None, description="Filter by actor"),
    target_type: Optional[str] = Query(None, description="Filter by target type"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    Retrieves filtered chronological audit records for compliance reporting.
    """
    return audit_service.get_audit_logs(
        db=db,
        document_id=document_id,
        action=action,
        actor=actor,
        target_type=target_type,
        limit=limit,
        offset=offset
    )


@router.get(
    "/audit/cost-summary",
    response_model=CostSummaryResponse,
    summary="Get cumulative and per-document AI token and dollar cost metrics"
)
def get_cost_summary(
    db: Session = Depends(get_db)
):
    """
    Aggregates LLM prompt tokens, completion tokens, cached tokens, and USD costs.
    """
    return audit_service.get_cost_summary(db=db)


@router.get(
    "/audit/export-csv",
    summary="Download audit trail as compliance-ready CSV"
)
def export_audit_csv(
    db: Session = Depends(get_db)
):
    """
    Generates and returns an audit trail CSV spreadsheet.
    """
    csv_content = audit_service.export_audit_csv(db=db)
    return PlainTextResponse(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit_trail_report.csv"}
    )
