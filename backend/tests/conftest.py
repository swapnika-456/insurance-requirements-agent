"""
==============================================================================
File: backend/tests/conftest.py
Purpose: Pytest configuration, fixtures, in-memory SQLite isolation,
         and TestClient setup for backend testing.
Architecture: Test Infrastructure / Pytest Fixtures
==============================================================================

Why Use In-Memory SQLite Fixtures for Tests?
1. Speed: In-memory tests run in milliseconds without disk I/O.
2. Isolation: Each test function receives a clean, empty database table schema.
   No test can pollute or depend on the leftover state of another test.
3. Safety: Tests will never overwrite or delete the developer's actual database.
"""

import os
import sys
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure backend folder is in PYTHONPATH so 'app' imports resolve cleanly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import Base, get_db
from app.main import app

# Create in-memory SQLite engine using StaticPool so all threads share the same in-memory DB
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def db_session():
    """
    Creates fresh database tables for each test and drops them on cleanup.
    Yields an isolated SQLAlchemy session.
    """
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db_session):
    """
    TestClient fixture that overrides FastAPI's `get_db` dependency
    with the isolated in-memory test database session.
    """
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="session")
def sample_pdf_paths():
    """
    Returns verified paths to the 3 generated synthetic insurance product PDFs.
    """
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "samples"))
    return {
        "auto": os.path.join(base_dir, "sample_auto_policy.pdf"),
        "home": os.path.join(base_dir, "sample_homeowners_policy.pdf"),
        "life": os.path.join(base_dir, "sample_term_life_spec.pdf"),
    }
