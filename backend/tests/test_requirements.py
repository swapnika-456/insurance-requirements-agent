"""
==============================================================================
File: backend/tests/test_requirements.py
Purpose: Unit and integration tests for BRD and User Story generation.
Architecture: Backend Testing Suite / Requirements Tests
==============================================================================
"""

import os
import pytest
from app.services.llm.mock import MockLLMProvider
from app.services.retrieval import RetrievalService
from app.services.requirements import RequirementsService
from app.models.requirement import RequirementPackageRecord


def test_requirements_service_e2e(client, sample_pdf_paths, db_session):
    """
    Tests end-to-end requirements generation:
    1. Ingest PDF document.
    2. Run RequirementsService with MockLLMProvider and RetrievalService.
    3. Assert BRD sections (scope, business rules, functional/non-functional requirements).
    4. Assert User Stories with Given-When-Then BDD acceptance criteria.
    5. Assert citations and persistence in SQLite.
    """
    auto_pdf_path = sample_pdf_paths["auto"]
    with open(auto_pdf_path, "rb") as f:
        upload_res = client.post("/api/v1/documents/upload", files={"file": ("auto_req.pdf", f, "application/pdf")})
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["id"]

    mock_llm = MockLLMProvider()
    retrieval_svc = RetrievalService(persist_directory="./data/test_chroma")
    service = RequirementsService(llm_provider=mock_llm, retrieval_service=retrieval_svc)

    response = service.generate_requirements(document_id=doc_id, db=db_session)
    assert response.document_id == doc_id
    assert response.brd is not None
    assert len(response.brd.business_rules) >= 3
    assert len(response.brd.functional_requirements) >= 3
    assert len(response.user_stories) >= 2

    # Check Gherkin criteria
    first_story = response.user_stories[0]
    assert first_story.story_id == "US-001"
    assert len(first_story.acceptance_criteria) >= 2
    ac = first_story.acceptance_criteria[0]
    assert ac.given != ""
    assert ac.when != ""
    assert ac.then != ""

    # Check persistence in SQLite
    persisted = db_session.query(RequirementPackageRecord).filter(RequirementPackageRecord.document_id == doc_id).first()
    assert persisted is not None
    assert persisted.cost_usd > 0


def test_requirements_api_routes(client, sample_pdf_paths):
    """
    Integration test for requirements API endpoints:
    POST /api/v1/requirements/{doc_id}/generate
    GET /api/v1/requirements/{doc_id}
    """
    auto_pdf_path = sample_pdf_paths["auto"]
    with open(auto_pdf_path, "rb") as f:
        upload_res = client.post("/api/v1/documents/upload", files={"file": ("auto_api_req.pdf", f, "application/pdf")})
    doc_id = upload_res.json()["id"]

    # Generate requirements via POST
    gen_res = client.post(f"/api/v1/requirements/{doc_id}/generate")
    assert gen_res.status_code == 200, gen_res.text
    data = gen_res.json()
    assert data["document_id"] == doc_id
    assert len(data["brd"]["functional_requirements"]) > 0

    # Fetch requirements via GET
    get_res = client.get(f"/api/v1/requirements/{doc_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == data["id"]
