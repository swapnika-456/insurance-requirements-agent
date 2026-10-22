"""
==============================================================================
File: backend/app/models/requirement.py
Purpose: SQLAlchemy ORM models for storing generated BRDs and User Stories.
Architecture: Backend Data Models / Requirements Persistence
==============================================================================
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class RequirementPackageRecord(Base):
    """
    Persisted requirements package containing generated BRD and User Stories.
    """
    __tablename__ = "requirement_packages"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    document_id = Column(String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String, nullable=False, default="draft")
    model_name = Column(String, nullable=False)
    prompt_tokens = Column(Integer, nullable=False, default=0)
    completion_tokens = Column(Integer, nullable=False, default=0)
    cost_usd = Column(Float, nullable=False, default=0.0)
    brd_json = Column(Text, nullable=False)
    user_stories_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    document = relationship("Document")
