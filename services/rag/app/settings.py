from pydantic_settings import BaseSettings
from typing import List, Optional
import os
from pathlib import Path


class Settings(BaseSettings):
    APP_NAME: str = "rag"
    ENV: str = "dev"
    LOG_LEVEL: str = "INFO"

    # JWT
    JWT_SECRET: str = "change-this-in-env"
    JWT_ISSUER: Optional[str] = None  # issuer check optional across services

    # Database (prefer POSTGRES_DSN, else compose from DB_* env vars)
    POSTGRES_DSN: Optional[str] = None
    # Optional so vercel doesnt break
    DB_USER: Optional[str] = os.getenv("DB_USER")
    DB_PASSWORD: Optional[str] = os.getenv("DB_PASSWORD")
    DB_HOST: Optional[str] = os.getenv("DB_HOST")
    DB_PORT: Optional[int] = int(os.getenv("DB_PORT")) if os.getenv("DB_PORT") else None
    DB_NAME: Optional[str] = os.getenv("DB_NAME")

    # CORS
    CORS_ORIGINS: List[str] = ["*"]

    # LLM provider configuration
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai")  # "openai" or "azure"

    # OpenAI
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # Azure OpenAI
    AZURE_OPENAI_API_KEY: Optional[str] = os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("AZURE_OPENAI_KEY")
    AZURE_OPENAI_ENDPOINT: Optional[str] = os.getenv("AZURE_OPENAI_ENDPOINT") or os.getenv("AZURE_GPT_ENDPOINT")
    AZURE_OPENAI_API_VERSION: str = os.getenv("AZURE_OPENAI_API_VERSION", "2024-06-01")
    AZURE_OPENAI_DEPLOYMENT: Optional[str] = os.getenv("AZURE_OPENAI_DEPLOYMENT") or os.getenv("AZURE_DEPLOYMENT_LLM")

    # Token/memory policy
    TOKEN_MEMORY_THRESHOLD: int = int(os.getenv("TOKEN_MEMORY_THRESHOLD", 4000))
    MAX_CONTEXT_TOKENS: int = int(os.getenv("MAX_CONTEXT_TOKENS", 12000))

    class Config:
        # Load .env from repo root (reicam_server/.env)
        # Path: services/rag/app/settings.py -> parents[3] = reicam_server
        env_file = str(Path(__file__).resolve().parents[3] / ".env")
        case_sensitive = True
        extra = "ignore"  # Ignore extra fields from shared .env


settings = Settings()

# Build DSN if not explicitly provided AND all components exist
if not settings.POSTGRES_DSN:
    if all([settings.DB_USER, settings.DB_PASSWORD, settings.DB_HOST, settings.DB_PORT, settings.DB_NAME]):
        settings.POSTGRES_DSN = (
            f"postgresql+asyncpg://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
        )
    else:
        # leave as None to allow stateless mode (no DB on Vercel)
        settings.POSTGRES_DSN = None
