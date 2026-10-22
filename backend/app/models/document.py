"""
==============================================================================
File: backend/app/models/document.py
Purpose: SQLAlchemy ORM models for Ingested Documents and Section Chunks.
Architecture: Backend Data Models / Ingestion Persistence Layer
==============================================================================

Why Separate Documents and Chunks in SQL?
While vector databases (like ChromaDB) store embeddings for similarity search,
relational databases (like SQLite/PostgreSQL) are the single source of truth for:
1. Document lifecycles and metadata (file size, page counts, upload timestamps).
2. Exact page coordinates and hierarchical section lineages.
3. Foreign-key relationships to downstream artifacts (BRDs, audit logs).
When a user deletes a document, SQLite's CASCADE DELETE ensures all associated
chunks, extractions, and requirements are cleanly expunged without leaving orphan rows.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


def generate_uuid() -> str:
    """Generates a string UUID4 for primary keys."""
    return str(uuid.uuid4())


class Document(Base):
    """
    Represents an uploaded insurance product document (Policy Form, Filing, or Spec).
    
    Attributes:
        id: Unique identifier (UUID4 string).
        filename: Original file name uploaded by the user.
        file_path: Absolute or relative disk path where the PDF is stored.
        file_size_bytes: Size of the PDF file in bytes.
        page_count: Total number of pages extracted from the PDF.
        line_of_business: Insurance category (e.g., Personal Auto, Homeowners, Life).
        status: Current pipeline state ('uploaded', 'ingested', 'extracted', 'failed').
        created_at: UTC timestamp when the document was received.
        chunks: One-to-many relationship to the DocumentChunk instances.
    """
    __tablename__ = "documents"

    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    page_count = Column(Integer, nullable=False, default=0)
    line_of_business = Column(String, nullable=True)
    status = Column(String, nullable=False, default="ingested")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Cascading delete ensures that deleting a document purges all its chunks
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    """
    Represents a discrete semantic section or clause chunk extracted from a document.
    
    Attributes:
        id: Unique chunk identifier (UUID4 string).
        document_id: Foreign key reference to parent Document.
        chunk_index: Sequential index of the chunk within the document (0, 1, 2...).
        page_number: 1-indexed page number in the source PDF where this chunk appears.
        section_title: Title of the top-level section (e.g., 'SECTION I - COVERAGES').
        parent_section: Enclosing parent container if nested.
        clause_reference: Specific clause number or title (e.g., 'Clause 2.1: Bodily Injury').
        text_content: The full textual body of the clause or section.
        token_count: Approximate token count for LLM context window planning.
        created_at: UTC timestamp when the chunk was extracted.
    """
    __tablename__ = "document_chunks"

    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    document_id = Column(String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    page_number = Column(Integer, nullable=False)
    section_title = Column(String, nullable=False)
    parent_section = Column(String, nullable=True)
    clause_reference = Column(String, nullable=True)
    text_content = Column(Text, nullable=False)
    token_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    document = relationship("Document", back_populates="chunks")
