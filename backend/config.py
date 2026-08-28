import os
import sys
from typing import List
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str = "Supply Chain Finance Core API"
    ENV: str = "development"
    DEBUG: bool = True

    # Security
    SECRET_KEY: str = "supply_chain_finance_super_secret_jwt_key_2026_safe"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Database
    # SQLite for local dev; override with postgresql:// URL in production env vars
    DATABASE_URL: str = "sqlite:///./supply_chain_finance.db"

    # CORS — comma-separated origins; defaults to wildcard for local dev
    ALLOWED_ORIGINS: str = "*"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @model_validator(mode="after")
    def validate_production_security(self):
        if self.ENV.lower() == "production":
            if "super_secret_jwt_key_2026_safe" in self.SECRET_KEY or len(self.SECRET_KEY) < 32:
                raise ValueError("CRITICAL SECURITY ERROR: Must configure a strong SECRET_KEY (min 32 chars) in production environment!")
        return self

    @property
    def cors_origins(self) -> List[str]:
        """Parse comma-separated ALLOWED_ORIGINS into a list."""
        if self.ALLOWED_ORIGINS.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

settings = Settings()
