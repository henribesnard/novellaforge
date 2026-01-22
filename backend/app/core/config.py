"""
Configuration settings for NovellaForge
"""
from typing import List, Optional, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AliasChoices, Field, field_validator
import secrets


class Settings(BaseSettings):
    """Application settings"""

    # Project Info
    PROJECT_NAME: str = "NovellaForge API"
    VERSION: str = "1.0.0"
    APP_ENV: str = Field(default="development")
    DEBUG: bool = Field(default=True)

    # API Settings
    API_V1_PREFIX: str = "/api/v1"
    SECRET_KEY: str = Field(default="")
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
    DATABASE_URL: str = Field(...)

    # Redis
    REDIS_URL: str = Field(...)

    # Qdrant Vector Database
    QDRANT_URL: str = Field(...)
    QDRANT_API_KEY: Optional[str] = Field(default=None)
    QDRANT_COLLECTION_NAME: str = "novellaforge_documents"

    # Neo4j Knowledge Graph
    NEO4J_URI: Optional[str] = Field(default=None)
    NEO4J_USER: Optional[str] = Field(default=None)
    NEO4J_PASSWORD: Optional[str] = Field(default=None)
    NEO4J_DATABASE: Optional[str] = Field(default=None)

    # ChromaDB
    CHROMA_HOST: Optional[str] = Field(default=None)
    CHROMA_PORT: Optional[int] = Field(default=None)
    CHROMA_PERSIST_DIR: str = Field(default="./chromadb")
    CHROMA_COLLECTION_PREFIX: str = Field(default="novellaforge")

    # DeepSeek API
    DEEPSEEK_API_KEY: str = Field(...)
    DEEPSEEK_API_BASE: str = "https://api.deepseek.com/v1"
    DEEPSEEK_MODEL: str = "deepseek-chat"
    DEEPSEEK_REASONING_MODEL: str = "deepseek-reasoner"
    DEEPSEEK_TIMEOUT: float = Field(default=300.0)
    CHAT_MAX_TOKENS: int = Field(default=4096)
    CHAPTER_MIN_WORDS: int = Field(default=1200)
    CHAPTER_MAX_WORDS: int = Field(default=2000)
    MAX_REVISIONS: int = Field(default=2)
    QUALITY_GATE_COHERENCE_THRESHOLD: float = Field(default=6.0)
    QUALITY_GATE_SCORE_THRESHOLD: float = Field(default=7.5)
    PLAN_REASONING_ENABLED: bool = Field(default=True)
    PLAN_REASONING_FIRST_CHAPTERS: int = Field(default=3)
    PLAN_REASONING_INTERVAL: int = Field(default=10)
    PLAN_REASONING_KEYWORDS: str = Field(default="critical,twist,finale")
    WRITE_PARALLEL_BEATS: bool = Field(default=True)
    WRITE_DISTRIBUTED_BEATS: bool = Field(default=False)  # Use Celery for true parallelism
    WRITE_PARTIAL_REVISION: bool = Field(default=True)
    WRITE_PREVIOUS_BEATS_MAX_CHARS: int = Field(default=1500)
    WRITE_EARLY_STOP_RATIO: float = Field(default=1.05)
    WRITE_MIN_BEAT_WORDS: int = Field(default=120)
    WRITE_TOKENS_PER_WORD: float = Field(default=1.5)
    WRITE_MAX_TOKENS: int = Field(default=1800)
    MEMORY_CONTEXT_MAX_CHARS: int = Field(default=4000)
    RAG_CONTEXT_MAX_CHARS: int = Field(default=4000)
    STYLE_CONTEXT_MAX_CHARS: int = Field(default=2000)
    STORY_BIBLE_MAX_CHARS: int = Field(default=2500)
    VALIDATION_MAX_CHARS: int = Field(default=12000)
    VALIDATION_ALLOW_FALLBACK: bool = Field(default=False)
    CRITIC_MAX_CHARS: int = Field(default=6000)

    # Embeddings
    EMBEDDING_MODEL: str = "BAAI/bge-m3"
    EMBEDDING_DIMENSION: int = 1024

    # File Upload
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10 MB
    ALLOWED_EXTENSIONS: List[str] = [".txt", ".docx", ".pdf", ".md"]
    UPLOAD_DIR: str = "./uploads"

    # Celery
    CELERY_BROKER_URL: str = Field(
        default="",
        validation_alias=AliasChoices("CELERY_BROKER_URL", "REDIS_URL"),
    )
    CELERY_RESULT_BACKEND: str = Field(
        default="",
        validation_alias=AliasChoices("CELERY_RESULT_BACKEND", "REDIS_URL"),
    )

    # RAG Settings
    RAG_CHUNK_SIZE: int = 512
    RAG_CHUNK_OVERLAP: int = 50
    RAG_TOP_K: int = 5

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    # Logging
    LOG_LEVEL: str = Field(default="INFO")

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )


# Create settings instance
settings = Settings()  # type: ignore[call-arg]
