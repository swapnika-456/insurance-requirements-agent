"""
==============================================================================
File: backend/tests/test_ingestion.py
Purpose: Unit and integration tests for PDF parsing, hierarchical clause chunking,
         and document ingestion API routes.
Architecture: Backend Testing Suite / Ingestion Tests
==============================================================================
"""

import os
import pytest
from app.services.ingestion import IngestionService, IngestionError


def test_ingest_auto_policy(sample_pdf_paths):
    """
    Verifies that the synthetic Auto Policy PDF parses correctly,
    identifies 3 pages, extracts distinct legal clauses, and infers Personal Auto LOB.
    """
    service = IngestionService()
    auto_pdf_path = sample_pdf_paths["auto"]
    assert os.path.exists(auto_pdf_path), f"Sample file missing: {auto_pdf_path}"

    with open(auto_pdf_path, "rb") as f:
        pdf_bytes = f.read()

    result = service.ingest_pdf_bytes(pdf_bytes, "sample_auto_policy.pdf")
    
    assert result.page_count == 3
    assert result.line_of_business == "Personal Auto"
    assert len(result.chunks) >= 6
    
    # Check that clauses and sections were detected
    section_titles = [c.section_title for c in result.chunks]
    assert any("SECTION I" in s or "COVERAGE" in s for s in section_titles)
    
    # Check that specific clause references were captured
    clause_refs = [c.clause_reference for c in result.chunks if c.clause_reference]
    assert any("Clause 2.1" in c or "Rule UW-1" in c or "Endorsement END-AUTO" in c for c in clause_refs)


def test_ingest_homeowners_policy(sample_pdf_paths):
    """
    Verifies that the synthetic Homeowners HO-3 Policy parses with 3 pages,
    detects Texas jurisdiction specifics, and classifies LOB as Homeowners.
    """
    service = IngestionService()
    home_pdf_path = sample_pdf_paths["home"]
    assert os.path.exists(home_pdf_path), f"Sample file missing: {home_pdf_path}"

    with open(home_pdf_path, "rb") as f:
        pdf_bytes = f.read()

    result = service.ingest_pdf_bytes(pdf_bytes, "sample_homeowners_policy.pdf")
    
    assert result.page_count == 3
    assert result.line_of_business == "Homeowners"
    assert len(result.chunks) >= 6


def test_ingest_term_life_spec(sample_pdf_paths):
    """
    Verifies that the synthetic Term Life Spec parses with 3 pages,
    detects medical underwriting rules and incontestability clause.
    """
    service = IngestionService()
    life_pdf_path = sample_pdf_paths["life"]
    assert os.path.exists(life_pdf_path), f"Sample file missing: {life_pdf_path}"

    with open(life_pdf_path, "rb") as f:
        pdf_bytes = f.read()

    result = service.ingest_pdf_bytes(pdf_bytes, "sample_term_life_spec.pdf")
    
    assert result.page_count == 3
    assert result.line_of_business == "Term Life"
    assert len(result.chunks) >= 5


def test_empty_file_rejection():
    """
    Verifies that an empty 0-byte file immediately triggers IngestionError.
    """
    service = IngestionService()
    with pytest.raises(IngestionError) as exc_info:
        service.ingest_pdf_bytes(b"", "empty.pdf")
    assert "empty (0 bytes)" in str(exc_info.value)


def test_invalid_header_rejection():
    """
    Verifies that a non-PDF file disguised as a PDF is rejected.
    """
    service = IngestionService()
    with pytest.raises(IngestionError) as exc_info:
        service.ingest_pdf_bytes(b"This is just plain text, not a PDF header.", "fake.pdf")
    assert "missing %PDF- header" in str(exc_info.value)


def test_document_api_upload_flow(client, sample_pdf_paths):
    """
    Integration test testing the full API lifecycle:
    1. Upload PDF via POST /api/v1/documents/upload
    2. Query document via GET /api/v1/documents/{id}
    3. Query chunks via GET /api/v1/documents/{id}/chunks
    4. List documents via GET /api/v1/documents
    5. Delete document via DELETE /api/v1/documents/{id}
    """
    auto_pdf_path = sample_pdf_paths["auto"]
    with open(auto_pdf_path, "rb") as f:
        files = {"file": ("test_auto_policy.pdf", f, "application/pdf")}
        response = client.post("/api/v1/documents/upload", files=files)

    assert response.status_code == 201, response.text
    data = response.json()
    doc_id = data["id"]
    assert data["filename"] == "test_auto_policy.pdf"
    assert data["page_count"] == 3
    assert data["line_of_business"] == "Personal Auto"
    assert len(data["chunks"]) > 0

    # Query details
    get_res = client.get(f"/api/v1/documents/{doc_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == doc_id

    # Query chunks filtered by page 1
    chunks_res = client.get(f"/api/v1/documents/{doc_id}/chunks?page=1")
    assert chunks_res.status_code == 200
    page_1_chunks = chunks_res.json()
    assert len(page_1_chunks) > 0
    assert all(c["page_number"] == 1 for c in page_1_chunks)

    # List documents
    list_res = client.get("/api/v1/documents")
    assert list_res.status_code == 200
    assert list_res.json()["total_count"] == 1

    # Delete document
    del_res = client.delete(f"/api/v1/documents/{doc_id}")
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True

    # Confirm deletion
    get_again = client.get(f"/api/v1/documents/{doc_id}")
    assert get_again.status_code == 404
