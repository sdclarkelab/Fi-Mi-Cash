from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Transaction Analyzer API"

    # Authentication — shared secret required on every API request (X-API-Key header)
    API_KEY: str

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # External APIs
    OPENAI_API_KEY: str

    # Gmail API
    GMAIL_CREDENTIALS_PATH: str
    GMAIL_TOKEN_PATH: str = "token.json"
    GMAIL_SCOPES: List[str] = ["https://www.googleapis.com/auth/gmail.readonly"]

    # Caching
    CACHE_TTL: int = 86400  # 24 hours
    CACHE_MAX_SIZE: int = 1000

    # Logging
    LOG_LEVEL: str = "INFO"

    # Sync Configuration
    MAX_SYNC_DAYS: int = 90  # Maximum days to sync in one operation
    SYNC_WINDOW_DAYS: int = 30  # Preferred sync window size
    MIN_SYNC_OVERLAP_HOURS: int = 1  # Minimum overlap to avoid re-sync
    
    # Card Types
    MASTERCARD_TYPE: str = "MASTERCARD PLATINUM USD"
    VISA_TYPE: str = "NCB VISA PLATINUM"

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()
