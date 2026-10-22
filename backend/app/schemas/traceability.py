"""
==============================================================================
File: backend/app/schemas/traceability.py
Purpose: Pydantic v2 schemas for Data Models, REST API Contracts,
         Bidirectional Traceability Matrices, and Automated Gap Reports.
Architecture: Backend Data Transfer Layer / Traceability Schemas
==============================================================================

Why Bidirectional Traceability in Insurance?
In regulated insurance IT delivery:
1. Every software artifact (API endpoint, database table, user story) must prove
   statutory authorization by tracing backward to a filed policy clause.
2. Every filed policy clause must be implemented in software (forward traceability).
Gaps represent catastrophic delivery risks:
- Uncovered Source Clause = Policy feature sold to customers but missing in software (unpriced risk).
- Orphan Requirement = Feature engineered in software with no filed policy backing (statutory violation).
"""

from typing import List, Optional
from pydantic import BaseModel, Field
from app.schemas.citation import Citation


class EntityField(BaseModel):
    """Specific attribute within a core insurance data entity."""
    field_name: str = Field(description="Name of column or property (e.g., 'bodily_injury_limit')")
    data_type: str = Field(description="Primitive or structured type (e.g., 'String', 'Decimal', 'Integer', 'Date')")
    is_required: bool = Field(default=True, description="Whether field is mandatory")
    description: str = Field(description="Semantic definition of the field")
    citation: Optional[Citation] = Field(default=None, description="Source policy citation")


class DataEntity(BaseModel):
    """Core domain entity (e.g., 'Policy', 'Vehicle', 'Driver', 'CoverageLimit')."""
    entity_name: str = Field(description="Name of the entity (e.g., 'Driver', 'Vehicle', 'Dwelling')")
    description: str = Field(description="Business role of this entity in policy administration")
    fields: List[EntityField] = Field(default_factory=list, description="Attributes of this entity")
    relationships: List[str] = Field(default_factory=list, description="Relationships (e.g., 'One Policy has Many Vehicles')")


class ProductDataModel(BaseModel):
    """Complete product data model specification."""
    entities: List[DataEntity] = Field(default_factory=list, description="Domain entities")


class APIParameter(BaseModel):
    """Request parameter or query flag in REST endpoint."""
    name: str = Field(description="Parameter name")
    in_location: str = Field(description="'path', 'query', or 'body'")
    param_type: str = Field(description="Data type")
    required: bool = Field(default=True)
    description: str = Field(description="Purpose of parameter")


class APIEndpoint(BaseModel):
    """REST API endpoint contract specification (OpenAPI 3.1 style)."""
    endpoint_id: str = Field(description="Unique endpoint ID (e.g., 'API-001')")
    http_method: str = Field(description="'POST', 'GET', 'PUT', or 'DELETE'")
    path: str = Field(description="URL path (e.g., '/quotes/auto/rate')")
    summary: str = Field(description="Operation summary")
    request_schema_summary: str = Field(description="Input payload structure summary")
    response_schema_summary: str = Field(description="Output payload structure summary")
    citation: Optional[Citation] = Field(default=None, description="Source policy citation")


class APIContract(BaseModel):
    """Complete REST API contract specification."""
    title: str = Field(description="API Contract Title")
    base_path: str = Field(default="/api/v1")
    endpoints: List[APIEndpoint] = Field(default_factory=list, description="Exposed REST endpoints")


class TraceabilityRow(BaseModel):
    """
    A single horizontal traceability slice mapping:
    Requirement -> User Story -> Data Model Element -> API Endpoint -> Source Clause & Page.
    """
    requirement_id: str = Field(description="REQ-xxx ID")
    requirement_title: str = Field(description="Requirement title")
    user_story_id: Optional[str] = Field(default=None, description="US-xxx ID")
    data_model_element: Optional[str] = Field(default=None, description="Entity.field or Entity name")
    api_endpoint: Optional[str] = Field(default=None, description="METHOD /path")
    source_clause: Optional[str] = Field(default=None, description="Policy section or clause name")
    source_page: Optional[int] = Field(default=None, description="1-indexed source PDF page number")
    has_gap: bool = Field(default=False, description="True if any link in the chain is broken or missing")
    gap_reason: Optional[str] = Field(default=None, description="Diagnosis of gap if has_gap is True")


class GapReport(BaseModel):
    """
    Automated gap detection analysis report.
    """
    uncovered_clauses: List[str] = Field(
        default_factory=list,
        description="Source clauses in the policy with no mapped software requirement (Missed Feature Risk)"
    )
    orphan_requirements: List[str] = Field(
        default_factory=list,
        description="Requirements with no valid source policy clause citation (Hallucination Risk)"
    )
    total_source_clauses: int = Field(description="Total legal clauses identified in policy")
    covered_source_clauses: int = Field(description="Count of clauses mapped to at least 1 requirement")
    coverage_percentage: float = Field(description="Clause implementation coverage percentage")


class TraceabilityMatrixResponse(BaseModel):
    """
    Complete Traceability Package response including matrix rows, gap report,
    data model, and API contract.
    """
    id: str = Field(description="Traceability package UUID")
    document_id: str = Field(description="Source document UUID")
    status: str = Field(description="'completed' or 'needs_review'")
    data_model: ProductDataModel = Field(description="Generated product data model")
    api_contract: APIContract = Field(description="Generated REST API contract")
    matrix: List[TraceabilityRow] = Field(description="Traceability matrix rows")
    gap_report: GapReport = Field(description="Automated gap analysis report")
