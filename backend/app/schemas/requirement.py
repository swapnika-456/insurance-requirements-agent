"""
==============================================================================
File: backend/app/schemas/requirement.py
Purpose: Pydantic v2 schemas for Business Requirements Documents (BRD),
         Agile User Stories with Gherkin Acceptance Criteria, and citations.
Architecture: Backend Data Transfer Layer / Requirements Schemas
==============================================================================

Why Formal Requirements Generation in Insurance?
Core insurance systems (Guidewire, Duck Creek, custom rating engines) require
precision specifications:
1. Business Rules (BR-xxx): Underwriting and rating logic directly translating policy wording.
2. Functional Requirements (REQ-xxx): Software capabilities needed to quote, rate, and bind.
3. User Stories (US-xxx): Agile development tickets with Gherkin (Given-When-Then) criteria
   ready for immediate import into Jira or Azure DevOps.
Every generated item MUST cite the exact policy clause and page.
"""

from typing import List, Optional
from pydantic import BaseModel, Field
from app.schemas.citation import Citation


class BusinessRuleItem(BaseModel):
    """Specific legal, rating, or underwriting rule mandated by policy terms."""
    rule_id: str = Field(description="Unique business rule ID (e.g., 'BR-001')")
    name: str = Field(description="Short title of the rule")
    description: str = Field(description="Detailed business logic and constraints")
    citation: Citation = Field(description="Provenance link to source policy clause")


class FunctionalRequirementItem(BaseModel):
    """Software system capability required to administer the insurance product."""
    req_id: str = Field(description="Unique requirement ID (e.g., 'REQ-001')")
    title: str = Field(description="Requirement title")
    description: str = Field(description="Detailed functional specification")
    priority: str = Field(default="High", description="Priority: 'High', 'Medium', or 'Low'")
    citation: Citation = Field(description="Provenance link to source policy clause")


class NonFunctionalRequirementItem(BaseModel):
    """System quality constraints (Auditability, Security, Performance)."""
    nfr_id: str = Field(description="Unique NFR ID (e.g., 'NFR-001')")
    category: str = Field(description="'Compliance', 'Auditability', 'Security', or 'Latency'")
    description: str = Field(description="Constraint specification")


class AcceptanceCriterion(BaseModel):
    """Gherkin BDD scenario for automated test generation."""
    criterion_id: str = Field(description="Scenario ID (e.g., 'AC-01')")
    scenario_title: str = Field(description="Brief scenario summary")
    given: str = Field(description="Precondition / initial system state")
    when: str = Field(description="Trigger action or user input")
    then: str = Field(description="Expected outcome or system response")


class UserStoryItem(BaseModel):
    """Agile User Story ready for Jira execution with Gherkin acceptance criteria."""
    story_id: str = Field(description="Unique story ID (e.g., 'US-001')")
    title: str = Field(description="Story headline")
    as_a: str = Field(description="Persona (e.g., 'Applicant', 'Underwriter', 'Rating Engine')")
    i_want: str = Field(description="Desired action or capability")
    so_that: str = Field(description="Business value or benefit achieved")
    linked_requirement_id: str = Field(description="Traceability link to REQ-xxx")
    acceptance_criteria: List[AcceptanceCriterion] = Field(
        default_factory=list,
        description="Gherkin Given-When-Then criteria"
    )
    citations: List[Citation] = Field(
        default_factory=list,
        description="Source citations supporting this story"
    )


class BusinessRequirementsDocument(BaseModel):
    """Complete Business Requirements Document (BRD) model."""
    document_title: str = Field(description="Title of the BRD")
    scope: str = Field(description="Executive scope and boundaries of the delivery")
    business_rules: List[BusinessRuleItem] = Field(default_factory=list, description="Extracted business rules")
    functional_requirements: List[FunctionalRequirementItem] = Field(default_factory=list, description="Functional requirements")
    non_functional_requirements: List[NonFunctionalRequirementItem] = Field(default_factory=list, description="Non-functional requirements")
    assumptions: List[str] = Field(default_factory=list, description="Delivery assumptions")
    open_questions: List[str] = Field(default_factory=list, description="Clarifications needed from carrier actuaries")


class RequirementsPackage(BaseModel):
    """Aggregated requirements package containing BRD and User Stories."""
    brd: BusinessRequirementsDocument = Field(description="Business Requirements Document")
    user_stories: List[UserStoryItem] = Field(default_factory=list, description="Agile User Stories")


class RequirementsResponse(BaseModel):
    """API Response wrapper for generated requirements with cost and audit telemetry."""
    id: str = Field(description="Requirements record UUID")
    document_id: str = Field(description="Source document UUID")
    status: str = Field(description="'completed' or 'needs_review'")
    model_name: str = Field(description="LLM provider used")
    prompt_tokens: int = Field(description="Input tokens")
    completion_tokens: int = Field(description="Output tokens")
    cost_usd: float = Field(description="Generation cost in USD")
    brd: BusinessRequirementsDocument = Field(description="Generated BRD")
    user_stories: List[UserStoryItem] = Field(description="Generated User Stories")
