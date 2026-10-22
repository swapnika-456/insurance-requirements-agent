"""
==============================================================================
File: backend/app/services/llm/mock.py
Purpose: Deterministic Mock LLM Provider for unit tests and offline benchmarking.
Architecture: Backend Services / Mock LLM Implementation
==============================================================================

Why a Mock LLM Provider?
Automated CI/CD pipelines and unit tests must never depend on third-party cloud APIs:
1. Prevents test failures from network blips, API maintenance, or API key exhaustion.
2. Runs tests in milliseconds without incurring real token costs.
3. Provides 100% deterministic outputs for assertions on citations and schemas.
"""

from typing import Type, TypeVar, Optional, Any
from pydantic import BaseModel

from app.services.llm.base import LLMProvider, LLMResponse, StructuredLLMResponse
from app.schemas.citation import Citation
from app.schemas.product import (
    StructuredProductExtraction, CitedString, CoverageItem, DeductibleItem,
    RatingFactorItem, UnderwritingRuleItem, ExclusionItem, EndorsementItem
)

T = TypeVar("T", bound=BaseModel)


class MockLLMProvider(LLMProvider):
    """
    Deterministic offline provider delivering instant, schema-compliant responses
    tailored to the prompt content.
    """

    def __init__(self, model_name: str = "mock-llm-provider"):
        self.model_name = model_name

    def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.1
    ) -> LLMResponse:
        """Returns deterministic simulated text with fake token counts."""
        simulated_text = f"Simulated analysis response for prompt: {prompt[:80]}..."
        return LLMResponse(
            content=simulated_text,
            prompt_tokens=150,
            completion_tokens=50,
            total_tokens=200,
            cost_usd=0.000015,
            model_name=self.model_name,
            latency_ms=10.0
        )

    def generate_structured(
        self,
        prompt: str,
        response_schema: Type[T],
        system_instruction: Optional[str] = None,
        temperature: float = 0.0
    ) -> StructuredLLMResponse:
        """
        Returns a deterministic schema instance corresponding to `response_schema`.
        """
        prompt_lower = prompt.lower()

        # Check which schema is requested
        if response_schema == StructuredProductExtraction:
            if "homeowner" in prompt_lower or "ho-3" in prompt_lower:
                data = self._generate_homeowners_extraction()
            elif "term life" in prompt_lower or "death benefit" in prompt_lower:
                data = self._generate_life_extraction()
            else:
                data = self._generate_auto_extraction()

            return StructuredLLMResponse(
                data=data,
                prompt_tokens=450,
                completion_tokens=320,
                total_tokens=770,
                cost_usd=0.00013,
                model_name=self.model_name,
                latency_ms=15.0
            )

        # Generic dummy fallback if any other schema is passed
        try:
            dummy_instance = response_schema()
        except Exception:
            dummy_instance = None

        return StructuredLLMResponse(
            data=dummy_instance,
            prompt_tokens=100,
            completion_tokens=100,
            total_tokens=200,
            cost_usd=0.00002,
            model_name=self.model_name,
            latency_ms=5.0
        )

    def _generate_auto_extraction(self) -> StructuredProductExtraction:
        """Simulated extraction for Personal Auto policy."""
        return StructuredProductExtraction(
            product_name=CitedString(
                value="Apex Personal Auto Policy Form (PA-2026-OH)",
                citation=Citation(page_number=1, clause_reference="Header", exact_quote="APEX PERSONAL AUTO POLICY FORM (PA-2026-OH)", confidence_score=0.99)
            ),
            line_of_business=CitedString(
                value="Personal Auto",
                citation=Citation(page_number=1, clause_reference="Header", exact_quote="Line of Business: Personal Auto", confidence_score=1.0)
            ),
            state_or_jurisdiction=CitedString(
                value="State of Ohio",
                citation=Citation(page_number=1, clause_reference="Header", exact_quote="Jurisdiction: State of Ohio", confidence_score=1.0)
            ),
            effective_date=CitedString(
                value="January 1, 2026",
                citation=Citation(page_number=1, clause_reference="Header", exact_quote="Effective Date: January 1, 2026", confidence_score=0.98)
            ),
            coverages=[
                CoverageItem(
                    coverage_name="Part A: Bodily Injury Liability",
                    limit="$250,000 per person / $500,000 per accident",
                    deductible="None",
                    citation=Citation(page_number=1, clause_reference="SECTION I", exact_quote="$250,000 per person / $500,000 per accident", confidence_score=0.99)
                ),
                CoverageItem(
                    coverage_name="Part A: Property Damage Liability",
                    limit="$100,000 per accident",
                    deductible="None",
                    citation=Citation(page_number=1, clause_reference="SECTION I", exact_quote="$100,000 per accident", confidence_score=0.99)
                ),
                CoverageItem(
                    coverage_name="Part D: Collision Coverage",
                    limit="Actual Cash Value (ACV)",
                    deductible="$500 per occurrence",
                    citation=Citation(page_number=1, clause_reference="SECTION I", exact_quote="$500 per occurrence", confidence_score=0.98)
                )
            ],
            deductibles=[
                DeductibleItem(
                    peril_or_coverage="Collision Coverage",
                    amount_or_formula="$500 per occurrence",
                    citation=Citation(page_number=1, clause_reference="Clause 2.2", exact_quote="A mandatory deductible of $500 applies to all collision claims", confidence_score=0.97)
                ),
                DeductibleItem(
                    peril_or_coverage="Comprehensive / Other Than Collision",
                    amount_or_formula="$250 per occurrence",
                    citation=Citation(page_number=1, clause_reference="Clause 2.2", exact_quote="$250 applies to comprehensive events", confidence_score=0.97)
                )
            ],
            rating_factors=[
                RatingFactorItem(
                    factor_name="Driver Age Tiers",
                    factor_code="RF-1",
                    description_or_formula="Tier 1 (18-20: 1.65), Tier 2 (21-24: 1.30), Tier 3 (25-64: 1.00), Tier 4 (65+: 1.15)",
                    citation=Citation(page_number=2, clause_reference="Clause 3.1", exact_quote="Rating Factor RF-1 applies to driver age bands", confidence_score=0.96)
                ),
                RatingFactorItem(
                    factor_name="Ohio Territory Tiers",
                    factor_code="RF-2",
                    description_or_formula="Territory 01 (1.25), Territory 02 (1.10), Territory 03 (0.85)",
                    citation=Citation(page_number=2, clause_reference="Clause 3.2", exact_quote="Territory Factor RF-2 is based on vehicle garaging zip code", confidence_score=0.95)
                )
            ],
            underwriting_rules=[
                UnderwritingRuleItem(
                    rule_id="UW-1",
                    condition="Minimum driver age 18 with 12 months licensing; no suspensions in 36 months",
                    underwriting_action="Decline",
                    citation=Citation(page_number=2, clause_reference="Rule UW-1", exact_quote="The minimum driver age is 18 years", confidence_score=0.99)
                ),
                UnderwritingRuleItem(
                    rule_id="UW-2",
                    condition="More than 1 at-fault accident or >2 moving violations in 36 months",
                    underwriting_action="Refer to Underwriter",
                    citation=Citation(page_number=2, clause_reference="Rule UW-2", exact_quote="cannot be bound without manual referral to an executive underwriter", confidence_score=0.98)
                )
            ],
            exclusions=[
                ExclusionItem(
                    exclusion_title="Intentional Loss and Criminal Acts",
                    description="Excludes intentional injury or property damage and organized racing or criminal felonies",
                    citation=Citation(page_number=3, clause_reference="Clause 5.1", exact_quote="We do not provide liability coverage for any insured who intentionally causes bodily injury", confidence_score=0.95)
                ),
                ExclusionItem(
                    exclusion_title="Commercial Rideshare and Delivery",
                    description="Excluded while logged into rideshare app or delivering goods for a fee without Endorsement END-AUTO-04",
                    citation=Citation(page_number=3, clause_reference="Clause 5.2", exact_quote="excluded while the insured vehicle is logged into a transportation network platform", confidence_score=0.97)
                )
            ],
            endorsements=[
                EndorsementItem(
                    endorsement_code="END-AUTO-01",
                    title="24/7 Roadside Assistance Service",
                    coverage_modification="Towing up to 50 miles, lockouts, jumpstarts. Limit $100/incident, max 4 calls/year.",
                    premium_impact="Included or optional add-on",
                    citation=Citation(page_number=3, clause_reference="Endorsement END-AUTO-01", exact_quote="Provides towing up to 50 miles, battery jumpstarts, flat tire changes", confidence_score=0.96)
                ),
                EndorsementItem(
                    endorsement_code="END-AUTO-03",
                    title="Rental Vehicle Reimbursement",
                    coverage_modification="Reimburses up to $40/day to maximum of $1,200 (30 days)",
                    premium_impact="Optional rider",
                    citation=Citation(page_number=3, clause_reference="Endorsement END-AUTO-03", exact_quote="Reimburses up to $40 per day to a maximum of $1,200", confidence_score=0.96)
                )
            ]
        )

    def _generate_homeowners_extraction(self) -> StructuredProductExtraction:
        """Simulated extraction for Homeowners HO-3 policy."""
        return StructuredProductExtraction(
            product_name=CitedString(
                value="Apex Homeowners Special Form HO-3 (HO3-2026-TX)",
                citation=Citation(page_number=1, clause_reference="Header", exact_quote="APEX HOMEOWNERS SPECIAL FORM HO-3 (HO3-2026-TX)", confidence_score=0.99)
            ),
            line_of_business=CitedString(
                value="Homeowners",
                citation=Citation(page_number=1, clause_reference="Header", exact_quote="Line of Business: Homeowners", confidence_score=1.0)
            ),
            state_or_jurisdiction=CitedString(
                value="State of Texas",
                citation=Citation(page_number=1, clause_reference="Header", exact_quote="Jurisdiction: State of Texas", confidence_score=1.0)
            ),
            effective_date=CitedString(
                value="March 1, 2026",
                citation=Citation(page_number=1, clause_reference="Header", exact_quote="Effective Date: March 1, 2026", confidence_score=0.98)
            ),
            coverages=[
                CoverageItem(
                    coverage_name="Coverage A: Dwelling",
                    limit="$450,000",
                    deductible="$1,500 All-Peril / 2% Windstorm",
                    citation=Citation(page_number=1, clause_reference="SECTION I", exact_quote="Coverage A: Dwelling $450,000", confidence_score=0.99)
                )
            ],
            deductibles=[
                DeductibleItem(
                    peril_or_coverage="All-Peril Base Deductible",
                    amount_or_formula="$1,500",
                    citation=Citation(page_number=1, clause_reference="Clause 2.1", exact_quote="A baseline deductible of $1,500 applies to each covered loss", confidence_score=0.98)
                ),
                DeductibleItem(
                    peril_or_coverage="Texas Windstorm and Hail",
                    amount_or_formula="2% of Coverage A Dwelling ($9,000)",
                    citation=Citation(page_number=1, clause_reference="Clause 2.2", exact_quote="Windstorm and Hail deductible applies equal to 2% of the Coverage A Dwelling limit", confidence_score=0.99)
                )
            ],
            rating_factors=[],
            underwriting_rules=[],
            exclusions=[],
            endorsements=[]
        )

    def _generate_life_extraction(self) -> StructuredProductExtraction:
        """Simulated extraction for 20-Year Term Life policy."""
        return StructuredProductExtraction(
            product_name=CitedString(
                value="Apex Horizon 20-Year Term Life Product Specification (TL-2026-IL)",
                citation=Citation(page_number=1, clause_reference="Header", exact_quote="APEX HORIZON 20-YEAR TERM LIFE PRODUCT SPECIFICATION", confidence_score=0.99)
            ),
            line_of_business=CitedString(
                value="Term Life",
                citation=Citation(page_number=1, clause_reference="Header", exact_quote="Line of Business: Term Life", confidence_score=1.0)
            ),
            state_or_jurisdiction=CitedString(
                value="State of Illinois",
                citation=Citation(page_number=1, clause_reference="Header", exact_quote="Jurisdiction: State of Illinois", confidence_score=1.0)
            ),
            effective_date=CitedString(
                value="July 1, 2026",
                citation=Citation(page_number=1, clause_reference="Header", exact_quote="Effective Date: July 1, 2026", confidence_score=0.98)
            ),
            coverages=[],
            deductibles=[
                DeductibleItem(
                    peril_or_coverage="Life Death Benefit Deductible",
                    amount_or_formula="None ($0.00)",
                    citation=Citation(page_number=1, clause_reference="SECTION I", exact_quote="Life insurance carries no deductible", confidence_score=1.0)
                )
            ],
            rating_factors=[],
            underwriting_rules=[],
            exclusions=[],
            endorsements=[]
        )
