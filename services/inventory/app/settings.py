from pydantic_settings import BaseSettings
from typing import List, Optional
import os


class Settings(BaseSettings):
    APP_NAME: str = "inventory"
    ENV: str = "dev"
    LOG_LEVEL: str = "INFO"

    # JWT
    JWT_SECRET: str = "change-this-in-env"
    JWT_ISSUER: str = "waifu_solutions.partners"
    ACCESS_TOKEN_EXPIRE_SECONDS: int = 60 * 60 * 2  # 2h
    REFRESH_TOKEN_EXPIRE_SECONDS: int = 60 * 60 * 24 * 7  # 7d

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

    # File uploads (not used in inventory for now but
    # we might want to consider having similar to partners
    # service considering we need previews for the items)
    # Use a repo-local default to avoid permission issues on host OS
    #SKIN_DIR: str = "./data/skins"
    #MAX_SKIN_MB: int = 5
    #HAIR_DIR: str = "./data/hairs"
    #MAX_HAIR_MB: int = 5
    #EYE_DIR: str = "./data/eyes"
    #MAX_EYE_MB: int = 5
    #MOUTH_DIR: str = "./data/mouths"
    #MAX_MOUTH_MB: int = 5
    


    class Config:
        env_file = ".env"
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
