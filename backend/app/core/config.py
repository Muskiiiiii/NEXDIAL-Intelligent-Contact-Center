import os
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    PROJECT_NAME: str = "NEXDIAL - Intelligent Contact Center"
    ENVIRONMENT: str = "SIMULATION"
    API_V1_STR: str = "/api/v1"

    # Database URL - defaults to SQLite for local development/testing; can be overridden by env for PostgreSQL
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./nexdial.db")
    SYNC_DATABASE_URL: str = os.getenv("SYNC_DATABASE_URL", "sqlite:///./nexdial.db")

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5173", "*"]

    # Pacing and Safety defaults
    DEFAULT_SAFETY_BUFFER_RATIO: float = 0.15  # 15% safety buffer
    MAX_DIAL_RATIO_PREDICTIVE: float = 3.0    # At most 3x dials per agent in aggressive mode
    DEFAULT_DIAL_RATIO: float = 1.0           # 1:1 for progressive
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = 5
    CIRCUIT_BREAKER_RECOVERY_TIME: float = 10.0 # seconds

    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()
