"""
==============================================================================
File: backend/app/schemas/product.py
Purpose: Pydantic v2 schemas for Structured Product Extraction.
Architecture: Backend Data Transfer Layer / Product Extraction Schema
==============================================================================

Schema Enforcement:
This schema forces the LLM to output rigorously structured insurance components
(Coverages, Limits, Deductibles, Rating Factors, Underwriting Rules, Exclusions,
Endorsements, Jurisdiction, Effective Date). Every item encapsulates its own
Citation object. Unknown fields default to None and are NEVER guessed.
"""

from typing import List, Optional
from pydantic import BaseModel, Field
from app.schemas.citation import Citation


class CitedString(BaseModel):
    """A scalar string value paired with its mandatory citation proof."""
    value: str = Field(description="The extracted textual value")
    citation: Citation = Field(description="Source clause and quote provenance")


class CoverageItem(BaseModel):
    """Specific protection offered with limit and deductible."""
    coverage_name: str = Field(description="Name of coverage (e.g., 'Bodily Injury Liability')")
    limit: str = Field(description="Stated limit (e.g., '$250,000 per person / $500,000 per accident')")
    deductible: Optional[str] = Field(default=None, description="Deductible if applicable (e.g., '$500')")
    citation: Citation = Field(description="Citation anchoring this coverage to the policy")


class DeductibleItem(BaseModel):
    """Specific out-of-pocket loss threshold per peril."""
    peril_or_coverage: str = Field(description="Peril or coverage (e.g., 'Collision', 'Windstorm and Hail')")
    amount_or_formula: str = Field(description="Fixed dollar amount or percentage formula (e.g., '$500' or '2%')")
    citation: Citation = Field(description="Citation anchoring this deductible")


class RatingFactorItem(BaseModel):
    """Actuarial rating parameter used to compute premium."""
    factor_name: str = Field(description="Rating variable (e.g., 'Driver Age Tiers', 'Protection Class')")
    factor_code: Optional[str] = Field(default=None, description="Actuarial code if noted (e.g., 'RF-1', 'RF-PPC')")
    description_or_formula: str = Field(description="Tier values, multiplicative factor, or rating rule")
    citation: Citation = Field(description="Citation anchoring this rating factor")


class UnderwritingRuleItem(BaseModel):
    """Risk acceptance gatekeeper condition."""
    rule_id: str = Field(description="Rule identifier (e.g., 'UW-1', 'Rule UW-HO-1')")
    condition: str = Field(description="Eligibility threshold (e.g., 'Minimum driver age 18')")
    underwriting_action: str = Field(description="'Decline', 'Refer to Underwriter', 'Standard Bind', or 'Surcharge'")
    citation: Citation = Field(description="Citation anchoring this underwriting rule")


class ExclusionItem(BaseModel):
    """Peril or situation explicitly not covered."""
    exclusion_title: str = Field(description="Exclusion heading (e.g., 'Flood Exclusion', 'Commercial Rideshare')")
    description: str = Field(description="Detailed scope of the exclusion")
    citation: Citation = Field(description="Citation anchoring this exclusion")


class EndorsementItem(BaseModel):
    """Optional rider or endorsement amending the base contract."""
    endorsement_code: str = Field(description="Form code (e.g., 'END-AUTO-01', 'HO-TX-04', 'R-LIFE-01')")
    title: str = Field(description="Title of rider (e.g., '24/7 Roadside Assistance', 'Water Backup')")
    coverage_modification: str = Field(description="What this endorsement adds or modifies")
    premium_impact: Optional[str] = Field(default=None, description="Additional surcharge or cost if specified")
    citation: Citation = Field(description="Citation anchoring this endorsement")


class StructuredProductExtraction(BaseModel):
    """
    Root extraction model representing the complete digitized insurance product spec.
    """
    product_name: CitedString = Field(description="Official name of the insurance product")
    line_of_business: CitedString = Field(description="Insurance vertical: Personal Auto, Homeowners, Term Life, etc.")
    state_or_jurisdiction: CitedString = Field(description="Filing state (e.g., Ohio, Texas, Illinois)")
    effective_date: Optional[CitedString] = Field(default=None, description="Contract effective date if stated")
    
    coverages: List[CoverageItem] = Field(default_factory=list, description="Extracted schedule of coverages")
    deductibles: List[DeductibleItem] = Field(default_factory=list, description="Extracted deductibles")
    rating_factors: List[RatingFactorItem] = Field(default_factory=list, description="Actuarial rating rules")
    underwriting_rules: List[UnderwritingRuleItem] = Field(default_factory=list, description="Underwriting eligibility criteria")
    exclusions: List[ExclusionItem] = Field(default_factory=list, description="Policy exclusions")
    endorsements: List[EndorsementItem] = Field(default_factory=list, description="Optional riders & endorsements")


class ProductExtractionResponse(BaseModel):
    """
    API Response wrapper containing the structured product extraction along with
    quality review flags, token usage, and latency metrics.
    """
    id: str = Field(description="Extraction ID")
    document_id: str = Field(description="Parent Document UUID")
    status: str = Field(description="'completed', 'needs_review', or 'failed'")
    model_name: str = Field(description="LLM provider and model used")
    prompt_tokens: int = Field(description="Input token count")
    completion_tokens: int = Field(description="Output token count")
    cost_usd: float = Field(description="Estimated run cost in USD")
    needs_review_count: int = Field(description="Count of citations with confidence < 0.75")
    data: StructuredProductExtraction = Field(description="Validated product data")
