from pathlib import Path
from typing import List

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/ directory (parent of app/core)
BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    PROJECT_NAME: str = "ShopSphere API"
    API_V1_STR: str = "/api"
    ENVIRONMENT: str = "development"

    # Database — PostgreSQL only. No SQLite fallback: the URL must be provided
    # via .env (copy .env.example) or the environment.
    DATABASE_URL: str

    # Security
    SECRET_KEY: str = "shopsphere-secret-key"

    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
    ]

    # Local file storage for uploaded product images (development-friendly).
    # No S3/cloud credentials are required.
    UPLOAD_DIR: Path = BACKEND_DIR / "uploads"
    MAX_IMAGE_SIZE_MB: int = 5

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v):
        if isinstance(v, str):
            return [i.strip() for i in v.split(",")]
        return v

    @model_validator(mode="after")
    def _reject_weak_secret_in_production(self):
        weak = {"shopsphere-secret-key", "change-me-to-a-long-random-string"}
        if self.ENVIRONMENT.lower() == "production" and self.SECRET_KEY in weak:
            raise ValueError(
                "SECRET_KEY must be set to a strong random value in production"
            )
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )


settings = Settings()
