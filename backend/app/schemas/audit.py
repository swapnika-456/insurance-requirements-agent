"""
==============================================================================
File: backend/app/schemas/audit.py
Purpose: Pydantic schemas for Human-in-the-Loop review actions, audit logging,
         and enterprise token/cost analytics.
Architecture: Backend API Contracts / Audit & Governance Layer
==============================================================================
"""

from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field


class ReviewActionRequest(BaseModel):
    """
    Payload for a human reviewer approving, rejecting, or editing an AI generated artifact.
    """
    target_type: Literal["EXTRACTION_ITEM", "REQUIREMENT", "USER_STORY"] = Field(
        ...,
        description="The category of artifact being reviewed."
    )
    target_id: str = Field(
        ...,
        description="ID of the item (e.g., REQ-AUTO-001, US-AUTO-001, or extraction field key)."
    )
    decision: Literal["APPROVED", "REJECTED", "EDITED"] = Field(
        ...,
        description="Human reviewer decision."
    )
    reviewer_name: str = Field(
        default="Senior Underwriting Analyst",
        description="Name or email of the human reviewer."
    )
    document_id: Optional[str] = Field(
        default=None,
        description="Optional document ID containing the item to disambiguate identical IDs."
    )
    edit_payload: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Updated fields if the decision is EDITED (e.g., modified description, rule, or limits)."
    )
    reason: Optional[str] = Field(
        default=None,
        description="Mandatory or recommended justification explaining the edit or rejection."
    )


class ReviewActionResponse(BaseModel):
    """Result of a human review decision."""
    success: bool
    audit_id: str
    target_type: str
    target_id: str
    new_status: str
    reviewer: str
    timestamp: str
    message: str


class AuditLogEntry(BaseModel):
    """Immutable audit record entry."""
    id: str
    timestamp: str
    document_id: Optional[str] = None
    document_name: Optional[str] = None
    action: str
    actor: str
    target_type: str
    target_id: str
    model_name: Optional[str] = None
    prompt_version: Optional[str] = None
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    cost_usd: float = 0.0
    details_json: Optional[str] = None


class DocumentCostBreakdown(BaseModel):
    """Aggregated token and dollar metrics for a specific document."""
    document_id: str
    document_name: str
    operations_count: int
    total_tokens: int
    total_cost_usd: float


class CostSummaryResponse(BaseModel):
    """High-level token governance and financial breakdown."""
    total_operations: int
    total_input_tokens: int
    total_output_tokens: int
    total_cached_tokens: int
    total_tokens: int
    total_cost_usd: float
    documents_breakdown: List[DocumentCostBreakdown]
    phase_breakdown: Dict[str, float]
