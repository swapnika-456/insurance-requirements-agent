"""
==============================================================================
File: backend/tests/test_audit.py
Purpose: Comprehensive unit and integration tests for Phase 5:
         Human-in-the-Loop review, immutable audit trail, cost analytics,
         and cascading document deletion.
Architecture: Test Layer / Governance & Compliance Tests
==============================================================================
"""

import os
import json
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import SessionLocal, Base, engine
from app.services.llm.mock import MockLLMProvider
from app.services.extraction import ExtractionService
from app.services.requirements import RequirementsService
from app.services.retrieval import RetrievalService
from app.api.deps import (
    get_llm_provider,
    get_extraction_service,
    get_requirements_service,
    get_retrieval_service
)
from app.models.document import Document, DocumentChunk
from app.models.extraction import ProductExtractionRecord
from app.models.requirement import RequirementPackageRecord
from app.models.audit import AuditLogRecord
from samples.generate_samples import generate_auto_policy_pdf

client = TestClient(app)

_mock_llm = MockLLMProvider()
_retrieval_svc = RetrievalService()
_extraction_svc = ExtractionService(llm_provider=_mock_llm)
_requirements_svc = RequirementsService(llm_provider=_mock_llm, retrieval_service=_retrieval_svc)

app.dependency_overrides[get_llm_provider] = lambda: _mock_llm
app.dependency_overrides[get_extraction_service] = lambda: _extraction_svc
app.dependency_overrides[get_requirements_service] = lambda: _requirements_svc
app.dependency_overrides[get_retrieval_service] = lambda: _retrieval_svc


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield


def test_audit_trail_and_human_review_e2e(tmp_path):
    """
    Validates end-to-end governance flow:
    1. Document upload logs DOCUMENT_INGESTED.
    2. Extraction logs EXTRACTION_GENERATED with cost.
    3. Requirements logs REQUIREMENTS_GENERATED.
    4. Human approves a requirement -> status updated to APPROVED.
    5. Human edits a user story -> description updated, audit diff recorded.
    6. Human rejects an item -> status updated to REJECTED.
    7. Cost summary endpoint accurately aggregates metrics.
    8. CSV export produces compliance-ready spreadsheet.
    9. Cascading delete purges document and chunks but preserves audit history.
    """
    pdf_path = os.path.join(tmp_path, "sample_auto_review.pdf")
    generate_auto_policy_pdf(pdf_path)

    # 1. Upload document
    with open(pdf_path, "rb") as f:
        res = client.post("/api/v1/documents/upload", files={"file": ("sample_auto_review.pdf", f, "application/pdf")})
    assert res.status_code == 201
    doc_id = res.json()["id"]

    # 2. Extract structured product data
    ext_res = client.post(f"/api/v1/extractions/{doc_id}")
    assert ext_res.status_code == 200
    assert ext_res.json()["cost_usd"] > 0

    # 3. Generate requirements package
    req_res = client.post(f"/api/v1/requirements/{doc_id}/generate")
    assert req_res.status_code == 200
    req_data = req_res.json()
    first_req_id = req_data["brd"]["functional_requirements"][0]["req_id"]
    first_story_id = req_data["user_stories"][0]["story_id"]

    # 4. Human Review - Approve Requirement
    approve_payload = {
        "target_type": "REQUIREMENT",
        "target_id": first_req_id,
        "document_id": doc_id,
        "decision": "APPROVED",
        "reviewer_name": "Chief Underwriting Officer",
        "reason": "Statutory limit verified against state schedule"
    }
    app_res = client.post("/api/v1/review/decision", json=approve_payload)
    assert app_res.status_code == 200
    assert app_res.json()["new_status"] == "APPROVED"

    # Verify requirement in DB has status APPROVED
    updated_req_res = client.get(f"/api/v1/requirements/{doc_id}")
    assert updated_req_res.json()["brd"]["functional_requirements"][0]["status"] == "APPROVED"
    assert updated_req_res.json()["brd"]["functional_requirements"][0]["reviewed_by"] == "Chief Underwriting Officer"

    # 5. Human Review - Edit User Story
    edit_payload = {
        "target_type": "USER_STORY",
        "target_id": first_story_id,
        "document_id": doc_id,
        "decision": "EDITED",
        "reviewer_name": "Lead Business Analyst",
        "reason": "Clarified underwriting threshold logic",
        "edit_payload": {
            "title": "US-AUTO-001 (Underwriter Modified): Validated Threshold",
            "so_that": "Underwriting fraud is minimized at quote binding"
        }
    }
    edit_res = client.post("/api/v1/review/decision", json=edit_payload)
    assert edit_res.status_code == 200
    assert edit_res.json()["new_status"] == "EDITED"

    # Verify user story in DB is updated
    updated_story_res = client.get(f"/api/v1/requirements/{doc_id}")
    updated_story = updated_story_res.json()["user_stories"][0]
    assert updated_story["status"] == "EDITED"
    assert "Underwriter Modified" in updated_story["title"]
    assert updated_story["so_that"] == "Underwriting fraud is minimized at quote binding"

    # 6. Human Review - Reject Item
    reject_payload = {
        "target_type": "REQUIREMENT",
        "target_id": first_req_id,
        "document_id": doc_id,
        "decision": "REJECTED",
        "reviewer_name": "Compliance Auditor",
        "reason": "Missing endorsement rider 402B"
    }
    rej_res = client.post("/api/v1/review/decision", json=reject_payload)
    assert rej_res.status_code == 200
    assert rej_res.json()["new_status"] == "REJECTED"

    # 7. Check Audit Logs endpoint
    audit_logs_res = client.get("/api/v1/audit/logs")
    assert audit_logs_res.status_code == 200
    logs = audit_logs_res.json()
    assert len(logs) >= 5
    actions = [l["action"] for l in logs]
    assert "DOCUMENT_INGESTED" in actions
    assert "EXTRACTION_GENERATED" in actions
    assert "REQUIREMENTS_GENERATED" in actions
    assert "ITEM_APPROVED" in actions
    assert "ITEM_EDITED" in actions
    assert "ITEM_REJECTED" in actions

    # 8. Check Cost Summary endpoint
    cost_res = client.get("/api/v1/audit/cost-summary")
    assert cost_res.status_code == 200
    cost_data = cost_res.json()
    assert cost_data["total_operations"] >= 5
    assert cost_data["total_tokens"] > 0
    assert cost_data["total_cost_usd"] > 0
    assert len(cost_data["documents_breakdown"]) >= 1
    assert "EXTRACTION" in cost_data["phase_breakdown"]
    assert "REQUIREMENTS" in cost_data["phase_breakdown"]

    # 9. Check CSV Export
    csv_res = client.get("/api/v1/audit/export-csv")
    assert csv_res.status_code == 200
    assert "text/csv" in csv_res.headers["content-type"]
    assert "Audit ID,Timestamp (UTC)" in csv_res.text
    assert "Chief Underwriting Officer" in csv_res.text

    # 10. Cascading Document Deletion
    del_res = client.delete(f"/api/v1/documents/{doc_id}")
    assert del_res.status_code == 200

    # Verify document no longer exists
    get_del_res = client.get(f"/api/v1/documents/{doc_id}")
    assert get_del_res.status_code == 404

    # Verify downstream requirement record is deleted
    db = SessionLocal()
    pkg = db.query(RequirementPackageRecord).filter(RequirementPackageRecord.document_id == doc_id).first()
    assert pkg is None

    # Verify audit trail PERSISTS even after document deletion!
    post_del_logs = client.get("/api/v1/audit/logs")
    post_actions = [l["action"] for l in post_del_logs.json()]
    assert "DOCUMENT_DELETED" in post_actions
    db.close()
