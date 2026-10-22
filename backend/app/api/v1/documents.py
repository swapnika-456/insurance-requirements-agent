"""
==============================================================================
File: backend/app/api/v1/documents.py
Purpose: RESTful API controller endpoints for Document ingestion, inspection,
         and deletion.
Architecture: Backend API Controllers / Document Endpoints
==============================================================================

Design Rule - Thin Routes, Thick Services:
Routes in this module are strictly responsible for:
1. Receiving HTTP requests and validating payloads via Pydantic/FastAPI.
2. Invoking the appropriate business logic in `IngestionService`.
3. Managing database transactions via the injected SQLAlchemy session.
4. Returning standardized HTTP status codes and typed response models.
No heavy PDF parsing or string manipulation logic lives in these route functions.
"""

import os
import shutil
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.api.deps import get_ingestion_service
from app.models.document import Document, DocumentChunk
from app.schemas.document import (
    DocumentResponse, DocumentDetailResponse, DocumentListResponse,
    ChunkResponse, DeleteDocumentResponse
)
from app.services.ingestion import IngestionService, IngestionError

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post(
    "/upload",
    response_model=DocumentDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and ingest an insurance product PDF"
)
async def upload_document(
    file: UploadFile = File(..., description="Insurance product PDF document (synthetic sample)"),
    db: Session = Depends(get_db),
    ingestion_service: IngestionService = Depends(get_ingestion_service)
):
    """
    Ingests an uploaded insurance product PDF document:
    1. Validates that the file is a PDF.
    2. Parses text page-by-page while tracking exact page numbers and font hierarchy.
    3. Segments legal text into section-aware clause chunks.
    4. Persists the document metadata and chunks into SQLite.
    5. Stores the raw PDF in the local uploads directory.
    
    Returns:
        DocumentDetailResponse: Document metadata and all extracted clause chunks.
    """
    filename = file.filename or "uploaded_document.pdf"
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file extension for '{filename}'. Only PDF files are supported."
        )

    try:
        content = await file.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not read uploaded file: {str(e)}"
        )

    # Execute ingestion service
    try:
        result = ingestion_service.ingest_pdf_bytes(content, filename)
    except IngestionError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal parser failure: {str(e)}"
        )

    # Save physical file to local upload directory
    os.makedirs(settings.UPLOAD_DIRECTORY, exist_ok=True)
    saved_file_path = os.path.join(settings.UPLOAD_DIRECTORY, f"{filename}")
    # Prevent collision if same file name uploaded multiple times
    counter = 1
    base_name, ext = os.path.splitext(filename)
    while os.path.exists(saved_file_path):
        saved_file_path = os.path.join(settings.UPLOAD_DIRECTORY, f"{base_name}_{counter}{ext}")
        counter += 1

    try:
        with open(saved_file_path, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to persist file to disk: {str(e)}"
        )

    # Create Document record
    doc_record = Document(
        filename=filename,
        file_path=saved_file_path,
        file_size_bytes=result.file_size_bytes,
        page_count=result.page_count,
        line_of_business=result.line_of_business,
        status="ingested"
    )
    db.add(doc_record)
    db.flush()  # Generates doc_record.id

    # Create DocumentChunk records
    chunk_records = []
    for c in result.chunks:
        chunk = DocumentChunk(
            document_id=doc_record.id,
            chunk_index=c.chunk_index,
            page_number=c.page_number,
            section_title=c.section_title,
            parent_section=c.parent_section,
            clause_reference=c.clause_reference,
            text_content=c.text_content,
            token_count=c.token_count
        )
        chunk_records.append(chunk)

    db.add_all(chunk_records)
    db.commit()
    db.refresh(doc_record)

    # Convert chunks to response DTOs
    chunk_dtos = [ChunkResponse.model_validate(c) for c in doc_record.chunks]

    return DocumentDetailResponse(
        id=doc_record.id,
        filename=doc_record.filename,
        file_size_bytes=doc_record.file_size_bytes,
        page_count=doc_record.page_count,
        line_of_business=doc_record.line_of_business,
        status=doc_record.status,
        created_at=doc_record.created_at,
        chunk_count=len(chunk_dtos),
        chunks=chunk_dtos
    )


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="List all ingested documents"
)
def list_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Retrieves all ingested documents with chunk counts."""
    query = db.query(Document).order_by(Document.created_at.desc())
    total = query.count()
    documents = query.offset(skip).limit(limit).all()

    doc_responses = []
    for d in documents:
        doc_responses.append(DocumentResponse(
            id=d.id,
            filename=d.filename,
            file_size_bytes=d.file_size_bytes,
            page_count=d.page_count,
            line_of_business=d.line_of_business,
            status=d.status,
            created_at=d.created_at,
            chunk_count=len(d.chunks)
        ))

    return DocumentListResponse(documents=doc_responses, total_count=total)


@router.get(
    "/{document_id}",
    response_model=DocumentDetailResponse,
    summary="Get document details and all semantic clause chunks"
)
def get_document(
    document_id: str,
    db: Session = Depends(get_db)
):
    """Retrieves a single document by ID including its complete list of extracted clause chunks."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' not found."
        )

    chunk_dtos = [ChunkResponse.model_validate(c) for c in doc.chunks]

    return DocumentDetailResponse(
        id=doc.id,
        filename=doc.filename,
        file_size_bytes=doc.file_size_bytes,
        page_count=doc.page_count,
        line_of_business=doc.line_of_business,
        status=doc.status,
        created_at=doc.created_at,
        chunk_count=len(chunk_dtos),
        chunks=chunk_dtos
    )


@router.get(
    "/{document_id}/chunks",
    response_model=List[ChunkResponse],
    summary="Get extracted chunks for a document"
)
def get_document_chunks(
    document_id: str,
    page: Optional[int] = Query(None, ge=1, description="Filter chunks by source page number"),
    db: Session = Depends(get_db)
):
    """Retrieves chunks for a document, optionally filtered by page number."""
    query = db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id)
    if page:
        query = query.filter(DocumentChunk.page_number == page)
    
    chunks = query.order_by(DocumentChunk.chunk_index.asc()).all()
    if not chunks:
        # Check if parent document exists
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document with ID '{document_id}' not found."
            )
    return [ChunkResponse.model_validate(c) for c in chunks]


@router.delete(
    "/{document_id}",
    response_model=DeleteDocumentResponse,
    summary="Delete a document and all its chunks"
)
def delete_document(
    document_id: str,
    db: Session = Depends(get_db)
):
    """
    Deletes a document from the database and disk:
    1. Cascades deletion of all DocumentChunks in SQLite.
    2. Deletes the underlying PDF file on disk.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' not found."
        )

    # Remove file on disk if it exists
    if os.path.exists(doc.file_path):
        try:
            os.remove(doc.file_path)
        except OSError:
            pass  # Continue to remove DB records even if disk unlink fails

    db.delete(doc)
    db.commit()

    return DeleteDocumentResponse(
        success=True,
        document_id=document_id,
        message=f"Document '{doc.filename}' and all associated chunks were successfully deleted."
    )
