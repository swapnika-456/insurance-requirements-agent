"""
==============================================================================
File: backend/app/models/extraction.py
Purpose: SQLAlchemy ORM model for storing digitized Product Extractions,
         citation metrics, and token cost telemetry.
Architecture: Backend Data Models / Extraction Persistence
==============================================================================
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class ProductExtractionRecord(Base):
    """
    Persisted structured extraction associated with an ingested policy document.
    """
    __tablename__ = "product_extractions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    document_id = Column(String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String, nullable=False, default="completed")
    model_name = Column(String, nullable=False)
    prompt_tokens = Column(Integer, nullable=False, default=0)
    completion_tokens = Column(Integer, nullable=False, default=0)
    cost_usd = Column(Float, nullable=False, default=0.0)
    needs_review_count = Column(Integer, nullable=False, default=0)
    raw_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    document = relationship("Document")
