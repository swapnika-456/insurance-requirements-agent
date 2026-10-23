"""
==============================================================================
File: backend/app/models/audit.py
Purpose: SQLAlchemy ORM model for immutable audit log and review actions.
Architecture: Backend Data Models / Audit & Compliance Layer
==============================================================================

Compliance Design Principles:
1. Append-Only Immutability:
   Every system action (AI generation, token usage, cost expenditure) and
   human action (approve, reject, edit) produces a new immutable record.
   Records are never updated or deleted in place.
2. Historical Integrity:
   Even if an active Document is deleted, audit records referencing that
   document retain their historical lineage (document_id, document_name,
   actor, cost, and timestamp) for Department of Insurance (DOI) audits.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, DateTime, Text

from app.core.database import Base


def generate_uuid() -> str:
    """Generates a string UUID4 for primary keys."""
    return str(uuid.uuid4())


class AuditLogRecord(Base):
    """
    Append-only audit trail capturing every AI inference and human review decision.
    """
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    
    # Document reference (not a hard foreign key so audit trails survive document deletion)
    document_id = Column(String(36), nullable=True, index=True)
    document_name = Column(String(255), nullable=True)
    
    # Action and Actor taxonomy
    action = Column(String(50), nullable=False, index=True)
    actor = Column(String(50), nullable=False, default="AI_SYSTEM", index=True)
    
    # Target entity
    target_type = Column(String(50), nullable=False, index=True)
    target_id = Column(String(100), nullable=False)
    
    # AI Governance / Cost tracking
    model_name = Column(String(100), nullable=True)
    prompt_version = Column(String(50), nullable=True)
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    cached_tokens = Column(Integer, default=0)
    cost_usd = Column(Float, default=0.0)
    
    # Rich details (JSON string: before/after payloads, reasons, citations)
    details_json = Column(Text, nullable=True)

    def to_dict(self) -> dict:
        """Serializes the audit record to a dictionary."""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "document_id": self.document_id,
            "document_name": self.document_name,
            "action": self.action,
            "actor": self.actor,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "model_name": self.model_name,
            "prompt_version": self.prompt_version,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cached_tokens": self.cached_tokens,
            "cost_usd": self.cost_usd,
            "details_json": self.details_json
        }
