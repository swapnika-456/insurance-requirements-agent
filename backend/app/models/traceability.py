"""
==============================================================================
File: backend/app/models/traceability.py
Purpose: SQLAlchemy ORM model for storing generated Data Models, API Contracts,
         Traceability Matrices, and Gap Reports.
Architecture: Backend Data Models / Traceability Persistence
==============================================================================
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class TraceabilityRecord(Base):
    """
    Persisted traceability package containing data models, API specs,
    bipartite traceability mappings, and automated gap detections.
    """
    __tablename__ = "traceability_records"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    document_id = Column(String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String, nullable=False, default="completed")
    coverage_percentage = Column(Float, nullable=False, default=0.0)
    data_model_json = Column(Text, nullable=False)
    api_contract_json = Column(Text, nullable=False)
    matrix_json = Column(Text, nullable=False)
    gap_report_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    document = relationship("Document")
