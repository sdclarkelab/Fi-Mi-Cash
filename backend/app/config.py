from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Transaction Analyzer API"

    # Authentication
    SECRET_KEY: str = "your-secret-key-here"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

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

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()
