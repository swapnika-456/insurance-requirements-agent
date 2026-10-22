"""
==============================================================================
File: backend/app/schemas/citation.py
Purpose: Pydantic v2 schemas for Source Citations, Evidence Quotes,
         and Confidence Scoring.
Architecture: Backend Data Transfer Layer / Citation Grounding
==============================================================================

Why are Strict Citations Required in Insurance AI?
Underwriting guidelines and policy forms are legally binding. In core insurance
system implementations, if an AI generates a coverage limit or deductible without
an attributable clause, it cannot be audited by compliance officers or regulators.
Every extracted fact MUST cite:
1. `page_number`: The exact page in the filed policy PDF.
2. `clause_reference`: The statutory section or sub-clause code (e.g. 'Clause 2.1').
3. `exact_quote`: Verbatim substring from the document proving the extraction.
4. `confidence_score`: 0.0 to 1.0. If < 0.75, it is flagged as `needs_review`.
"""

from typing import Optional
from pydantic import BaseModel, Field, model_validator


class Citation(BaseModel):
    """
    Cryptographic-style traceability link anchoring an extracted value back to
    its exact location in the source PDF policy form.
    """
    page_number: int = Field(
        ...,
        ge=1,
        description="1-indexed source PDF page number where evidence appears"
    )
    clause_reference: Optional[str] = Field(
        default=None,
        description="Section or clause header (e.g., 'Clause 2.1: Bodily Injury')"
    )
    exact_quote: str = Field(
        ...,
        min_length=3,
        description="Verbatim text snippet quoted directly from the source chunk"
    )
    confidence_score: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="AI confidence score between 0.0 (uncertain) and 1.0 (fully verified)"
    )
    needs_review: bool = Field(
        default=False,
        description="Automatically flagged True if confidence_score is below 0.75"
    )

    @model_validator(mode="after")
    def evaluate_review_flag(self) -> "Citation":
        """Flags any extraction with confidence < 0.75 as requiring human review."""
        if self.confidence_score < 0.75:
            self.needs_review = True
        return self
