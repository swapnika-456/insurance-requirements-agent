"""
==============================================================================
File: backend/app/schemas/document.py
Purpose: Pydantic v2 schemas (Data Transfer Objects) for Document and Chunk APIs.
Architecture: Backend API Layer / Request-Response Validation
==============================================================================

What is Pydantic v2?
Pydantic is Python's leading data validation library. It enforces data types at runtime.
When a client sends an HTTP request or receives a JSON response, Pydantic parses,
validates, and serializes the data according to these schema classes. If invalid
data is provided, Pydantic automatically returns a 422 Unprocessable Entity error
with exact field-level diagnostics.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ChunkResponse(BaseModel):
    """
    Schema for an individual extracted document chunk returned in API responses.
    """
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="Unique UUID of the chunk")
    document_id: str = Field(description="Parent document UUID")
    chunk_index: int = Field(description="Sequential index of the chunk in the document")
    page_number: int = Field(description="1-indexed source PDF page number")
    section_title: str = Field(description="Heading of the section")
    parent_section: Optional[str] = Field(default=None, description="Enclosing parent section")
    clause_reference: Optional[str] = Field(default=None, description="Specific clause title or code")
    text_content: str = Field(description="Extracted text body of the clause")
    token_count: int = Field(description="Approximate token count")
    created_at: datetime = Field(description="Timestamp when chunk was extracted")


class DocumentResponse(BaseModel):
    """
    Schema for document metadata returned when listing or querying documents.
    """
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="Unique document UUID")
    filename: str = Field(description="Uploaded PDF filename")
    file_size_bytes: int = Field(description="PDF file size in bytes")
    page_count: int = Field(description="Total number of pages in the PDF")
    line_of_business: Optional[str] = Field(default=None, description="Inferred or extracted insurance LOB")
    status: str = Field(description="Pipeline status (ingested, extracted, etc.)")
    created_at: datetime = Field(description="Upload timestamp")
    chunk_count: int = Field(default=0, description="Total number of semantic chunks extracted")


class DocumentDetailResponse(DocumentResponse):
    """
    Detailed document schema including the full list of extracted chunks.
    Used for inspecting clause chunking and page citations.
    """
    chunks: List[ChunkResponse] = Field(default_factory=list, description="Extracted clause chunks")


class DocumentListResponse(BaseModel):
    """
    Schema for paginated or aggregated list of all documents.
    """
    documents: List[DocumentResponse] = Field(description="List of ingested documents")
    total_count: int = Field(description="Total count of documents in the system")


class DeleteDocumentResponse(BaseModel):
    """
    Confirmation schema returned when a document and its artifacts are deleted.
    """
    success: bool = Field(description="True if document and chunks were deleted")
    document_id: str = Field(description="UUID of deleted document")
    message: str = Field(description="Human-readable status message")
