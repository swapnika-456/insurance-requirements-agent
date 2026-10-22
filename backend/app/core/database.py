"""
==============================================================================
File: backend/app/core/database.py
Purpose: SQLAlchemy database engine, session factory, and declarative base.
Architecture: Backend Core Infrastructure / Data Persistence Layer
==============================================================================

What is an ORM (Object-Relational Mapping)?
An ORM lets us interact with SQL tables using native Python objects and classes
rather than writing raw SQL strings (`SELECT * FROM ...`). This guarantees type
safety, prevents SQL injection attacks, and allows easy migration between
databases (e.g., from SQLite in development to PostgreSQL in production).
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

# For SQLite, check_same_thread=False is required to allow FastAPI's multithreaded
# async request handlers to share connections safely.
connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

# Engine manages database connection pooling and dialect translation
engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False  # Set to True if verbose SQL logging is needed for debugging
)

# SessionLocal is a factory that spawns new database sessions per API request
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Declarative base class from which all database models inherit
Base = declarative_base()


def get_db():
    """
    FastAPI dependency that yields a SQLAlchemy database session per request
    and guarantees that the session is closed cleanly when the request completes,
    preventing connection leaks.

    Yields:
        Session: Active SQLAlchemy session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
