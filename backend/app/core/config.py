"""
==============================================================================
File: backend/app/core/config.py
Purpose: Application configuration management using Pydantic Settings.
         Loads environment variables from .env with validation and fallbacks.
Architecture: Backend Core Infrastructure / Configuration Layer
==============================================================================

Why Pydantic Settings?
In modern Python microservices, configuration settings should be strictly typed.
Pydantic Settings reads from environment variables, converts types (e.g., str to list),
and errors early at startup if required configuration (like secrets or paths) is missing.
"""

import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """
    Central settings definition for the Insurance Requirements Agent backend.
    
    Attributes:
        GEMINI_API_KEY: Google GenAI API key for LLM and embeddings.
        GEMINI_MODEL: Gemini model name (default: gemini-2.5-flash).
        ENVIRONMENT: Application stage (development, staging, production).
        BACKEND_HOST: Server binding address.
        BACKEND_PORT: Server port.
        DATABASE_URL: SQLite database connection string.
        CHROMA_PERSIST_DIRECTORY: Persistent folder for ChromaDB vector embeddings.
        UPLOAD_DIRECTORY: Local folder where ingested PDF files are stored.
        CORS_ORIGINS: Comma-separated list of allowed web/client origins.
    """
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    GEMINI_API_KEY: str = Field(default="", description="Gemini API Key")
    GEMINI_MODEL: str = Field(default="gemini-2.5-flash", description="Gemini model identifier")
    
    ENVIRONMENT: str = Field(default="development", description="Runtime environment")
    BACKEND_HOST: str = Field(default="0.0.0.0", description="FastAPI host")
    BACKEND_PORT: int = Field(default=8000, description="FastAPI port")
    
    DATABASE_URL: str = Field(
        default="sqlite:///./data/app.db",
        description="SQLAlchemy database connection URL"
    )
    CHROMA_PERSIST_DIRECTORY: str = Field(
        default="./data/chroma",
        description="Directory for ChromaDB vector store"
    )
    UPLOAD_DIRECTORY: str = Field(
        default="./data/uploads",
        description="Directory for storing uploaded PDF policies"
    )
    
    CORS_ORIGINS: str = Field(
        default="http://localhost:3000,http://localhost:8080,http://localhost:8000,http://localhost:5000,http://127.0.0.1:8000",
        description="Comma-delimited CORS allowed origins"
    )

    @property
    def cors_origins_list(self) -> List[str]:
        """Parses the comma-delimited CORS_ORIGINS string into a clean list of strings."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


# Singleton instance cached across the application
settings = Settings()

# Ensure local runtime directories exist on module import
os.makedirs(settings.UPLOAD_DIRECTORY, exist_ok=True)
os.makedirs(settings.CHROMA_PERSIST_DIRECTORY, exist_ok=True)
os.makedirs(os.path.dirname(settings.DATABASE_URL.replace("sqlite:///", "")) or "./data", exist_ok=True)
