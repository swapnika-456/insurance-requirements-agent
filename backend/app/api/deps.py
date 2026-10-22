"""
==============================================================================
File: backend/app/api/deps.py
Purpose: FastAPI dependency injection providers.
Architecture: Backend API Layer / Dependency Injection
==============================================================================

What is Dependency Injection in FastAPI?
Dependency Injection (DI) allows route handlers to declare their dependencies
(such as database sessions, service instances, or settings) as function parameters.
FastAPI automatically handles instantiation, parameter passing, and teardown.
This makes our code:
1. Loosely coupled (routes don't hardcode how services or DB connections are created).
2. Extremely easy to test (tests can override `get_db` with an in-memory SQLite fixture).
"""

from typing import Generator
from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, get_db
from app.services.ingestion import IngestionService


def get_ingestion_service() -> IngestionService:
    """
    Provides a singleton-style IngestionService instance for document parsing.
    
    Returns:
        IngestionService: Configured ingestion engine.
    """
    return IngestionService()
