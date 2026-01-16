"""
Configuration settings for NovellaForge
"""
from typing import List, Optional, Union
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator, ValidationError
import os
import secrets


class Settings(BaseSettings):
    """Application settings"""

    # Project Info
    PROJECT_NAME: str = "NovellaForge API"
    VERSION: str = "1.0.0"
    APP_ENV: str = Field(default="development", env="APP_ENV")
    DEBUG: bool = Field(default=True, env="DEBUG")

    # API Settings
    API_V1_PREFIX: str = "/api/v1"
    SECRET_KEY: str = Field(default="", env="SECRET_KEY")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    @field_validator('SECRET_KEY')
    @classmethod
    def validate_secret_key(cls, v: str, info) -> str:
        """Validate SECRET_KEY is strong enough"""
        # Get environment info
        data = info.data if info.data else {}
        is_dev = data.get('APP_ENV') == 'development' or data.get('DEBUG') is True

        # If empty, handle based on environment
        if not v or v == "":
            if is_dev:
                # Generate a random key for development
                print("⚠️  WARNING: No SECRET_KEY provided. Generating random key for development.")
                return secrets.token_urlsafe(32)
            raise ValueError(
                "SECRET_KEY must be set in production. "
                "Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
            )

        # Check if it's the default weak key
        weak_keys = [
            "dev-secret-key-change-in-production",
            "your-secret-key-change-in-production",
            "change-me",
            "secret",
        ]
        if v.lower() in weak_keys:
            if not is_dev:
                raise ValueError(
                    "Cannot use default/weak SECRET_KEY in production. "
                    "Generate a strong key with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
                )
            # In dev, warn but allow
            print(f"⚠️  WARNING: Using weak SECRET_KEY '{v}'. Generating secure key for development.")
            return secrets.token_urlsafe(32)

        # Validate minimum length
        if len(v) < 32:
            if not is_dev:
                raise ValueError("SECRET_KEY must be at least 32 characters long in production")
            print(f"⚠️  WARNING: SECRET_KEY is too short ({len(v)} chars). Should be at least 32.")

        return v

    # CORS
    CORS_ORIGINS: Union[str, List[str]] = Field(
        default="http://localhost:3020,http://localhost:3000,http://localhost"
    )

    @field_validator('CORS_ORIGINS', mode='before')
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string or list"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        elif isinstance(v, list):
            return v
        return ["http://localhost:3000", "http://localhost"]

    ALLOWED_HOSTS: Union[str, List[str]] = Field(
        default="localhost,127.0.0.1"
    )

    @field_validator('ALLOWED_HOSTS', mode='before')
    @classmethod
    def parse_allowed_hosts(cls, v):
        """Parse allowed hosts from string or list"""
        if isinstance(v, str):
            return [host.strip() for host in v.split(",") if host.strip()]
        elif isinstance(v, list):
            return v
        return ["localhost", "127.0.0.1"]

    # Database
    DATABASE_URL: str = Field(..., env="DATABASE_URL")

    # Redis
    REDIS_URL: str = Field(..., env="REDIS_URL")

    # Qdrant Vector Database
    QDRANT_URL: str = Field(..., env="QDRANT_URL")
    QDRANT_API_KEY: Optional[str] = Field(default=None, env="QDRANT_API_KEY")
    QDRANT_COLLECTION_NAME: str = "novellaforge_documents"

    # Neo4j Knowledge Graph
    NEO4J_URI: Optional[str] = Field(default=None, env="NEO4J_URI")
    NEO4J_USER: Optional[str] = Field(default=None, env="NEO4J_USER")
    NEO4J_PASSWORD: Optional[str] = Field(default=None, env="NEO4J_PASSWORD")
    NEO4J_DATABASE: Optional[str] = Field(default=None, env="NEO4J_DATABASE")

    # ChromaDB
    CHROMA_HOST: Optional[str] = Field(default=None, env="CHROMA_HOST")
    CHROMA_PORT: Optional[int] = Field(default=None, env="CHROMA_PORT")
    CHROMA_PERSIST_DIR: str = Field(default="./chromadb", env="CHROMA_PERSIST_DIR")
    CHROMA_COLLECTION_PREFIX: str = Field(default="novellaforge", env="CHROMA_COLLECTION_PREFIX")

    # DeepSeek API
    DEEPSEEK_API_KEY: str = Field(..., env="DEEPSEEK_API_KEY")
    DEEPSEEK_API_BASE: str = "https://api.deepseek.com/v1"
    DEEPSEEK_MODEL: str = "deepseek-chat"
    DEEPSEEK_REASONING_MODEL: str = "deepseek-reasoner"
    DEEPSEEK_TIMEOUT: float = Field(default=300.0, env="DEEPSEEK_TIMEOUT")
    CHAT_MAX_TOKENS: int = Field(default=4096, env="CHAT_MAX_TOKENS")
    CHAPTER_MIN_WORDS: int = Field(default=1200, env="CHAPTER_MIN_WORDS")
    CHAPTER_MAX_WORDS: int = Field(default=2000, env="CHAPTER_MAX_WORDS")

    # Embeddings
    EMBEDDING_MODEL: str = "BAAI/bge-m3"
    EMBEDDING_DIMENSION: int = 1024

    # File Upload
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10 MB
    ALLOWED_EXTENSIONS: List[str] = [".txt", ".docx", ".pdf", ".md"]
    UPLOAD_DIR: str = "./uploads"

    # Celery
    CELERY_BROKER_URL: str = Field(default="", env="REDIS_URL")
    CELERY_RESULT_BACKEND: str = Field(default="", env="REDIS_URL")

    # RAG Settings
    RAG_CHUNK_SIZE: int = 512
    RAG_CHUNK_OVERLAP: int = 50
    RAG_TOP_K: int = 5

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    # Logging
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")

    class Config:
        env_file = ".env"
        case_sensitive = True


# Create settings instance
settings = Settings()
