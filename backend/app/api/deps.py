"""
==============================================================================
File: backend/app/api/deps.py
Purpose: FastAPI dependency injection providers for database sessions,
         LLM providers, and business services.
Architecture: Backend API Layer / Dependency Injection
==============================================================================
"""

from typing import Generator
from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal, get_db
from app.services.ingestion import IngestionService
from app.services.llm.base import LLMProvider
from app.services.llm.gemini import GeminiProvider
from app.services.llm.mock import MockLLMProvider
from app.services.extraction import ExtractionService


def get_ingestion_service() -> IngestionService:
    """Provides a singleton-style IngestionService instance."""
    return IngestionService()


def get_llm_provider() -> LLMProvider:
    """
    Provides the active LLM Provider.
    If GEMINI_API_KEY is configured in .env, instantiates GeminiProvider.
    Otherwise, falls back to MockLLMProvider for offline reliability.
    """
    if settings.GEMINI_API_KEY and settings.GEMINI_API_KEY != "your_gemini_api_key_here":
        return GeminiProvider(
            api_key=settings.GEMINI_API_KEY,
            model_name=settings.GEMINI_MODEL
        )
    return MockLLMProvider(model_name="mock-gemini-provider")


def get_extraction_service(
    llm: LLMProvider = Depends(get_llm_provider)
) -> ExtractionService:
    """Provides ExtractionService wired to the configured LLM provider."""
    return ExtractionService(llm_provider=llm)
