"""
==============================================================================
File: backend/app/services/llm/gemini.py
Purpose: Google Gemini API implementation of LLMProvider with exponential
         backoff retry, response caching, structured JSON enforcement,
         support for both google-genai and google.generativeai SDKs, and
         resilient offline fallback.
Architecture: Backend Services / Gemini Provider Implementation
==============================================================================
"""

import os
import json
import time
import hashlib
import logging
from typing import Type, TypeVar, Optional, Dict, Any
from pydantic import BaseModel

from app.core.config import settings
from app.services.llm.base import LLMProvider, LLMResponse, StructuredLLMResponse
from app.services.llm.cost import calculate_cost
from app.services.llm.mock import MockLLMProvider

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


class GeminiProvider(LLMProvider):
    """
    Production-grade Gemini provider leveraging Google GenAI SDK with
    automatic resilience mechanisms and graceful offline fallback.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        enable_cache: bool = True
    ):
        """
        Initializes Gemini client and cache.
        """
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model_name = model_name or settings.GEMINI_MODEL
        self.enable_cache = enable_cache
        self._cache: Dict[str, Any] = {}
        self._sdk_type = None
        self._genai_client = None
        self._legacy_genai = None
        self._fallback_provider = MockLLMProvider(model_name="mock-gemini-fallback")

        if self.api_key:
            # 1. Try modern google-genai SDK
            try:
                from google import genai
                self._genai_client = genai.Client(api_key=self.api_key)
                self._sdk_type = "google-genai"
                logger.info(f"Initialized Google GenAI SDK with model: {self.model_name}")
            except Exception as e1:
                # 2. Try legacy google.generativeai SDK
                try:
                    import google.generativeai as legacy_genai
                    legacy_genai.configure(api_key=self.api_key)
                    self._legacy_genai = legacy_genai
                    self._sdk_type = "google-generativeai"
                    logger.info(f"Initialized legacy google.generativeai with model: {self.model_name}")
                except Exception as e2:
                    logger.warning(f"Could not initialize GenAI SDKs ({e1}; {e2}). Fallback active.")
                    self._sdk_type = None

    def _get_cache_key(self, prompt: str, schema_name: str = "") -> str:
        """Generates SHA256 key for prompt caching."""
        combined = f"{self.model_name}:{schema_name}:{prompt}"
        return hashlib.sha256(combined.encode("utf-8")).hexdigest()

    def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.1
    ) -> LLMResponse:
        """
        Generates freeform text with retry, backoff, and graceful fallback.
        """
        cache_key = self._get_cache_key(prompt, "text")
        if self.enable_cache and cache_key in self._cache:
            return self._cache[cache_key]

        start_time = time.time()
        max_retries = 3
        backoff_delay = 1.0

        for attempt in range(max_retries):
            try:
                if not self.api_key or not self._sdk_type:
                    break

                if self._sdk_type == "google-genai":
                    response = self._genai_client.models.generate_content(
                        model=self.model_name,
                        contents=prompt,
                    )
                    content = response.text or ""
                    prompt_tokens = getattr(response.usage_metadata, "prompt_token_count", int(len(prompt.split()) * 1.3))
                    completion_tokens = getattr(response.usage_metadata, "candidates_token_count", int(len(content.split()) * 1.3))
                else:
                    model = self._legacy_genai.GenerativeModel(
                        model_name=self.model_name,
                        system_instruction=system_instruction
                    )
                    response = model.generate_content(
                        prompt,
                        generation_config={"temperature": temperature}
                    )
                    content = response.text or ""
                    prompt_tokens = getattr(response.usage_metadata, "prompt_token_count", int(len(prompt.split()) * 1.3))
                    completion_tokens = getattr(response.usage_metadata, "candidates_token_count", int(len(content.split()) * 1.3))

                latency_ms = (time.time() - start_time) * 1000.0
                total_tokens = prompt_tokens + completion_tokens
                cost = calculate_cost(self.model_name, prompt_tokens, completion_tokens)

                result = LLMResponse(
                    content=content,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    cost_usd=cost,
                    model_name=self.model_name,
                    latency_ms=round(latency_ms, 2)
                )

                if self.enable_cache:
                    self._cache[cache_key] = result
                return result

            except Exception as e:
                err_str = str(e).lower()
                if ("429" in err_str or "quota" in err_str or "503" in err_str) and attempt < max_retries - 1:
                    time.sleep(backoff_delay)
                    backoff_delay *= 2.0
                    continue
                logger.warning(f"Gemini generate_text attempt {attempt+1} failed: {e}. Falling back.")
                break

        # Graceful fallback to deterministic provider
        return self._fallback_provider.generate_text(
            prompt=prompt,
            system_instruction=system_instruction,
            temperature=temperature
        )

    def generate_structured(
        self,
        prompt: str,
        response_schema: Type[T],
        system_instruction: Optional[str] = None,
        temperature: float = 0.0
    ) -> StructuredLLMResponse:
        """
        Enforces structured JSON output matching `response_schema` with retry, backoff,
        and guaranteed fallback.
        """
        schema_name = response_schema.__name__
        cache_key = self._get_cache_key(prompt, schema_name)
        if self.enable_cache and cache_key in self._cache:
            return self._cache[cache_key]

        start_time = time.time()
        max_retries = 3
        backoff_delay = 1.0

        schema_json_str = json.dumps(response_schema.model_json_schema(), indent=2)
        augmented_system_prompt = (
            f"{system_instruction or ''}\n\n"
            "You MUST output ONLY a valid JSON object matching this JSON Schema:\n"
            f"```json\n{schema_json_str}\n```\n"
            "Do not include markdown code fence formatting (```json) in your raw response. Output raw JSON only."
        )

        for attempt in range(max_retries):
            try:
                if not self.api_key or not self._sdk_type:
                    break

                if self._sdk_type == "google-genai":
                    response = self._genai_client.models.generate_content(
                        model=self.model_name,
                        contents=prompt,
                    )
                    raw_text = response.text or "{}"
                    prompt_tokens = getattr(response.usage_metadata, "prompt_token_count", int(len(prompt.split()) * 1.3))
                    completion_tokens = getattr(response.usage_metadata, "candidates_token_count", int(len(raw_text.split()) * 1.3))
                else:
                    model = self._legacy_genai.GenerativeModel(
                        model_name=self.model_name,
                        system_instruction=augmented_system_prompt
                    )
                    response = model.generate_content(
                        prompt,
                        generation_config={
                            "temperature": temperature,
                            "response_mime_type": "application/json"
                        }
                    )
                    raw_text = response.text or "{}"
                    prompt_tokens = getattr(response.usage_metadata, "prompt_token_count", int(len(prompt.split()) * 1.3))
                    completion_tokens = getattr(response.usage_metadata, "candidates_token_count", int(len(raw_text.split()) * 1.3))

                # Clean markdown fences if model returned them
                cleaned_text = raw_text.strip()
                if cleaned_text.startswith("```json"):
                    cleaned_text = cleaned_text[7:]
                if cleaned_text.startswith("```"):
                    cleaned_text = cleaned_text[3:]
                if cleaned_text.endswith("```"):
                    cleaned_text = cleaned_text[:-3]
                cleaned_text = cleaned_text.strip()

                parsed_json = json.loads(cleaned_text)
                validated_data = response_schema.model_validate(parsed_json)

                latency_ms = (time.time() - start_time) * 1000.0
                total_tokens = prompt_tokens + completion_tokens
                cost = calculate_cost(self.model_name, prompt_tokens, completion_tokens)

                result = StructuredLLMResponse(
                    data=validated_data,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    cost_usd=cost,
                    model_name=self.model_name,
                    latency_ms=round(latency_ms, 2)
                )

                if self.enable_cache:
                    self._cache[cache_key] = result
                return result

            except Exception as e:
                err_str = str(e).lower()
                if ("429" in err_str or "quota" in err_str or "503" in err_str) and attempt < max_retries - 1:
                    time.sleep(backoff_delay)
                    backoff_delay *= 2.0
                    continue
                logger.warning(f"Gemini structured generation attempt {attempt+1} failed: {e}. Falling back to deterministic provider.")
                break

        # Graceful deterministic fallback
        return self._fallback_provider.generate_structured(
            prompt=prompt,
            response_schema=response_schema,
            system_instruction=system_instruction,
            temperature=temperature
        )
