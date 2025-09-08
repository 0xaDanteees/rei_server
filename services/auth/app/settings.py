from pydantic_settings import BaseSettings
from typing import List, Optional
import os


class Settings(BaseSettings):
    APP_NAME: str = "auth"
    ENV: str = "dev"
    LOG_LEVEL: str = "INFO"

    # JWT
    JWT_SECRET: str = "change-this-in-env"
    JWT_ISSUER: str = "waifu_solutions.auth"
    ACCESS_TOKEN_EXPIRE_SECONDS: int = 60 * 60 * 2  # 2h
    REFRESH_TOKEN_EXPIRE_SECONDS: int = 60 * 60 * 24 * 7  # 7d

    # Database (prefer POSTGRES_DSN, else compose from DB_* env vars)
    POSTGRES_DSN: Optional[str] = None
    DB_USER: str = os.getenv("DB_USER")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD")
    DB_HOST: str = os.getenv("DB_HOST")
    DB_PORT: int = os.getenv("DB_PORT")
    DB_NAME: str = os.getenv("DB_NAME")

    # CORS
    CORS_ORIGINS: List[str] = ["*"]

    # File uploads (avatars)
    # Use a repo-local default to avoid permission issues on host OS
    AVATAR_DIR: str = "./data/avatars"
    MAX_AVATAR_MB: int = 5

    class Config:
        env_file = ".env"
        case_sensitive = True


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