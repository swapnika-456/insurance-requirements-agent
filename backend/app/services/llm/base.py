"""
==============================================================================
File: backend/app/services/llm/base.py
Purpose: Abstract Base Class defining the LLM Provider interface.
Architecture: Backend Services / Pluggable LLM Abstraction Layer
==============================================================================

Why Provider Abstraction?
Insurance carriers maintain strict regulatory compliance and data sovereignty rules.
Some carriers mandate Azure OpenAI (HIPAA/SOC2 BAA), others AWS Bedrock, and others
run open-source models (Llama 3) via vLLM within private on-prem data centers.
By isolating model invocation behind this `LLMProvider` interface, our extraction,
requirements, and traceability services depend ONLY on this abstract contract.
Swapping LLMs requires changing ONE configuration line without altering business logic.
"""

from abc import ABC, abstractmethod
from typing import Type, TypeVar, Optional, Dict, Any
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMResponse(BaseModel):
    """
    Standardized result returned by all LLM providers, including usage telemetry.
    """
    content: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    model_name: str
    latency_ms: float = 0.0


class StructuredLLMResponse(BaseModel):
    """
    Standardized typed result returned when enforcing a Pydantic schema output.
    """
    data: Any
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    model_name: str
    latency_ms: float = 0.0


class LLMProvider(ABC):
    """
    Abstract interface that all LLM backends (Gemini, OpenAI, Bedrock, Mock) must implement.
    """

    @abstractmethod
    def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.1
    ) -> LLMResponse:
        """
        Generates freeform text from a prompt.

        Args:
            prompt: User/task prompt.
            system_instruction: High-priority system steering instructions.
            temperature: Sampling temperature (default 0.1 for high determinism).

        Returns:
            LLMResponse: Text output and token telemetry.
        """
        pass

    @abstractmethod
    def generate_structured(
        self,
        prompt: str,
        response_schema: Type[T],
        system_instruction: Optional[str] = None,
        temperature: float = 0.0
    ) -> StructuredLLMResponse:
        """
        Enforces guaranteed Pydantic schema structured JSON output from the LLM.

        Args:
            prompt: Extraction prompt including context chunks.
            response_schema: Pydantic model class to validate against.
            system_instruction: System guidelines.
            temperature: Default 0.0 for deterministic schema adherence.

        Returns:
            StructuredLLMResponse: Parsed Pydantic instance and token telemetry.
        """
        pass
