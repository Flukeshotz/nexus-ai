"""
Core application settings loaded from environment variables.
Uses pydantic-settings for type-safe configuration management.
"""

import os
import json
from pydantic_settings import BaseSettings
from typing import List

_db_path = os.getenv("DATABASE_PATH", "./nexus.db")

class Settings(BaseSettings):
    # ── Database ──────────────────────────────────────────────
    DATABASE_URL: str = f"sqlite+aiosqlite:///{_db_path}"
    DATABASE_URL_SYNC: str = f"sqlite:///{_db_path}"

    # ── JWT Authentication ────────────────────────────────────
    JWT_SECRET_KEY: str = "change-me-to-a-secure-random-string"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── CORS ──────────────────────────────────────────────────
    CORS_ORIGINS: str = '["*"]'

    @property
    def cors_origins_list(self) -> List[str]:
        return json.loads(self.CORS_ORIGINS)

    # ── AI Integration ────────────────────────────────────────
    GEMINI_API_KEY: str = "AIzaSyBxD8PgAOE4H93TCBu2Qld56AMtSBuJhck"
    GROQ_API_KEY: str = ""
    GROQ_MODEL_REASONING: str = "llama-3.3-70b-versatile"
    GROQ_MODEL_FAST: str = "llama-3.1-8b-instant"

    # ── Server ────────────────────────────────────────────────
    APP_ENV: str = "development"
    DEBUG: bool = True

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
