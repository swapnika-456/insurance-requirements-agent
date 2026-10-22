"""
==============================================================================
File: backend/tests/test_extraction.py
Purpose: Unit and integration tests for Structured Product Extraction,
         citation verification, confidence thresholds, and cost telemetry.
Architecture: Backend Testing Suite / Extraction Tests
==============================================================================
"""

import os
import pytest
from app.schemas.citation import Citation
from app.schemas.product import StructuredProductExtraction
from app.services.llm.mock import MockLLMProvider
from app.services.llm.cost import calculate_cost
from app.services.extraction import ExtractionService
from app.models.document import Document
from app.models.extraction import ProductExtractionRecord


def test_citation_confidence_validation():
    """Verifies that confidence < 0.75 triggers needs_review=True."""
    high_conf = Citation(
        page_number=1,
        clause_reference="Clause 1",
        exact_quote="Full replacement cost",
        confidence_score=0.95
    )
    assert high_conf.needs_review is False

    low_conf = Citation(
        page_number=2,
        clause_reference="Clause 2",
        exact_quote="Ambiguous deductible clause",
        confidence_score=0.60
    )
    assert low_conf.needs_review is True


def test_cost_calculation_formulas():
    """Verifies USD pricing calculation per token tiers."""
    # 1,000,000 prompt tokens + 1,000,000 completion tokens on gemini-2.5-flash
    # Price: 0.075 + 0.30 = $0.375
    cost = calculate_cost("gemini-2.5-flash", 1_000_000, 1_000_000)
    assert cost == 0.375

    # 10,000 prompt + 2,000 completion tokens
    cost_small = calculate_cost("gemini-2.5-flash", 10_000, 2_000)
    expected = (10_000 * 0.000000075) + (2_000 * 0.00000030)
    assert abs(cost_small - round(expected, 6)) < 1e-6


def test_mock_llm_provider_generation():
    """Verifies that MockLLMProvider generates a validated schema object."""
    provider = MockLLMProvider()
    response = provider.generate_structured(
        prompt="Extract Personal Auto Policy",
        response_schema=StructuredProductExtraction
    )
    assert response.data is not None
    assert isinstance(response.data, StructuredProductExtraction)
    assert response.data.line_of_business.value == "Personal Auto"
    assert len(response.data.coverages) >= 3
    assert len(response.data.deductibles) >= 2
    assert response.cost_usd > 0
    assert response.total_tokens > 0


def test_extraction_service_e2e(client, sample_pdf_paths, db_session):
    """
    Tests end-to-end extraction workflow:
    1. Upload auto policy PDF via API.
    2. Execute extraction using ExtractionService with MockLLMProvider.
    3. Verify all insurance elements (coverages, deductibles, rating factors, rules).
    4. Verify that extraction record is persisted in SQLite.
    """
    auto_pdf_path = sample_pdf_paths["auto"]
    with open(auto_pdf_path, "rb") as f:
        upload_res = client.post("/api/v1/documents/upload", files={"file": ("auto.pdf", f, "application/pdf")})
    
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["id"]

    mock_llm = MockLLMProvider()
    service = ExtractionService(llm_provider=mock_llm)

    extraction_res = service.extract_product(document_id=doc_id, db=db_session)
    assert extraction_res.document_id == doc_id
    assert extraction_res.data.line_of_business.value == "Personal Auto"
    
    # Check coverages
    coverage_names = [c.coverage_name for c in extraction_res.data.coverages]
    assert any("Bodily Injury" in name for name in coverage_names)
    assert any("Collision" in name for name in coverage_names)

    # Check deductibles
    deductibles = [d.amount_or_formula for d in extraction_res.data.deductibles]
    assert any("$500" in d for d in deductibles)

    # Check rating factors
    rf_codes = [rf.factor_code for rf in extraction_res.data.rating_factors if rf.factor_code]
    assert "RF-1" in rf_codes
    assert "RF-2" in rf_codes

    # Check underwriting rules
    rule_ids = [r.rule_id for r in extraction_res.data.underwriting_rules]
    assert "UW-1" in rule_ids
    assert "UW-2" in rule_ids

    # Check persistence in SQLite
    persisted = db_session.query(ProductExtractionRecord).filter(ProductExtractionRecord.document_id == doc_id).first()
    assert persisted is not None
    assert persisted.status in ["completed", "needs_review"]
    assert persisted.cost_usd > 0


def test_extraction_api_routes(client, sample_pdf_paths):
    """
    Integration test for extraction REST routes:
    POST /api/v1/extractions/{doc_id}
    GET /api/v1/extractions/{doc_id}
    """
    auto_pdf_path = sample_pdf_paths["auto"]
    with open(auto_pdf_path, "rb") as f:
        upload_res = client.post("/api/v1/documents/upload", files={"file": ("auto_api.pdf", f, "application/pdf")})
    doc_id = upload_res.json()["id"]

    # Trigger extraction via POST
    extract_post = client.post(f"/api/v1/extractions/{doc_id}")
    assert extract_post.status_code == 200, extract_post.text
    data = extract_post.json()
    assert data["document_id"] == doc_id
    assert data["data"]["product_name"]["value"] is not None

    # Fetch extraction via GET
    extract_get = client.get(f"/api/v1/extractions/{doc_id}")
    assert extract_get.status_code == 200
    assert extract_get.json()["id"] == data["id"]
