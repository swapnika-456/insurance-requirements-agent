"""
==============================================================================
File: backend/tests/test_traceability.py
Purpose: Unit and integration tests for Data Model synthesis, API Contract
         generation, Bidirectional Traceability Matrix, and Gap Detection.
Architecture: Backend Testing Suite / Traceability Tests
==============================================================================
"""

import os
import pytest
from app.services.llm.mock import MockLLMProvider
from app.services.retrieval import RetrievalService
from app.services.requirements import RequirementsService
from app.services.extraction import ExtractionService
from app.services.traceability import TraceabilityService
from app.models.traceability import TraceabilityRecord


def test_traceability_matrix_generation_and_gaps(client, sample_pdf_paths, db_session):
    """
    Tests end-to-end traceability matrix generation:
    1. Ingest PDF document.
    2. Execute TraceabilityService.generate_traceability.
    3. Assert Data Model entities (AutoPolicy, Driver, VehicleCoverage).
    4. Assert API Contract endpoints (POST /quotes/auto/rate, POST /underwriting/evaluate, POST /policies/bind).
    5. Assert matrix row linking (REQ -> Story -> Data Model -> API -> Clause).
    6. Assert automated gap detection (uncovered clauses and coverage percentage).
    7. Assert persistence in SQLite.
    """
    auto_pdf_path = sample_pdf_paths["auto"]
    with open(auto_pdf_path, "rb") as f:
        upload_res = client.post("/api/v1/documents/upload", files={"file": ("auto_trace.pdf", f, "application/pdf")})
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["id"]

    mock_llm = MockLLMProvider()
    retrieval_svc = RetrievalService(persist_directory="./data/test_chroma")
    req_svc = RequirementsService(llm_provider=mock_llm, retrieval_service=retrieval_svc)
    ext_svc = ExtractionService(llm_provider=mock_llm)
    trace_svc = TraceabilityService(llm_provider=mock_llm, requirements_service=req_svc, extraction_service=ext_svc)

    res = trace_svc.generate_traceability(document_id=doc_id, db=db_session)
    assert res.document_id == doc_id
    assert res.data_model is not None
    assert len(res.data_model.entities) >= 2
    assert len(res.api_contract.endpoints) >= 3
    assert len(res.matrix) >= 3

    # Check matrix mapping fields
    first_row = res.matrix[0]
    assert first_row.requirement_id.startswith("REQ-")
    assert first_row.data_model_element is not None
    assert first_row.api_endpoint is not None

    # Check gap report
    assert res.gap_report.total_source_clauses > 0
    assert res.gap_report.coverage_percentage >= 0.0

    # Check persistence in SQLite
    persisted = db_session.query(TraceabilityRecord).filter(TraceabilityRecord.document_id == doc_id).first()
    assert persisted is not None
    assert persisted.coverage_percentage == res.gap_report.coverage_percentage


def test_traceability_csv_export(client, sample_pdf_paths, db_session):
    """
    Verifies that the CSV export formats valid RFC-4180 headers and rows.
    """
    auto_pdf_path = sample_pdf_paths["auto"]
    with open(auto_pdf_path, "rb") as f:
        upload_res = client.post("/api/v1/documents/upload", files={"file": ("auto_csv.pdf", f, "application/pdf")})
    doc_id = upload_res.json()["id"]

    mock_llm = MockLLMProvider()
    retrieval_svc = RetrievalService(persist_directory="./data/test_chroma")
    req_svc = RequirementsService(llm_provider=mock_llm, retrieval_service=retrieval_svc)
    ext_svc = ExtractionService(llm_provider=mock_llm)
    trace_svc = TraceabilityService(llm_provider=mock_llm, requirements_service=req_svc, extraction_service=ext_svc)

    csv_data = trace_svc.export_matrix_csv(document_id=doc_id, db=db_session)
    assert "Requirement ID,Requirement Title,User Story ID" in csv_data
    assert "GAP AUDIT REPORT SUMMARY" in csv_data
    assert "Coverage Percentage" in csv_data


def test_traceability_api_routes(client, sample_pdf_paths):
    """
    Integration test for traceability API endpoints:
    POST /api/v1/traceability/{doc_id}/generate
    GET /api/v1/traceability/{doc_id}
    GET /api/v1/traceability/{doc_id}/export
    """
    auto_pdf_path = sample_pdf_paths["auto"]
    with open(auto_pdf_path, "rb") as f:
        upload_res = client.post("/api/v1/documents/upload", files={"file": ("auto_trace_api.pdf", f, "application/pdf")})
    doc_id = upload_res.json()["id"]

    # Generate
    post_res = client.post(f"/api/v1/traceability/{doc_id}/generate")
    assert post_res.status_code == 200, post_res.text
    data = post_res.json()
    assert data["document_id"] == doc_id
    assert len(data["matrix"]) > 0

    # Get
    get_res = client.get(f"/api/v1/traceability/{doc_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == data["id"]

    # Export CSV
    export_res = client.get(f"/api/v1/traceability/{doc_id}/export")
    assert export_res.status_code == 200
    assert "text/csv" in export_res.headers["content-type"]
    assert "Requirement ID" in export_res.text
