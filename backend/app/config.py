"""
Central app configuration. Everything secret/environment-specific lives here,
loaded from environment variables (see .env.example). Nothing in this codebase
should ever hardcode an API key.
"""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Required secrets
    GROQ_API_KEY: str = ""
    PINECONE_API_KEY: str = ""

    # Optional secrets
    GITHUB_TOKEN: str = ""

    # Models
    GROQ_CHAT_MODEL: str = "openai/gpt-oss-120b"
    GROQ_FAST_MODEL: str = "openai/gpt-oss-20b"

    # Pinecone
    PINECONE_INDEX_NAME: str = "codebase-chat"
    PINECONE_CLOUD: str = "aws"
    PINECONE_REGION: str = "us-east-1"
    PINECONE_EMBED_MODEL: str = "llama-text-embed-v2"
    PINECONE_RERANK_MODEL: str = "bge-reranker-v2-m3"

    # App
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"
    DATA_DIR: str = "./data"
    MAX_FILES_PER_REPO: int = 1200
    MAX_FILE_SIZE_BYTES: int = 300_000

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def data_dir_path(self) -> Path:
        p = Path(self.DATA_DIR)
        p.mkdir(parents=True, exist_ok=True)
        return p


@lru_cache
def get_settings() -> Settings:
    return Settings()


def require_groq_key() -> str:
    key = get_settings().GROQ_API_KEY
    if not key:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Add it to backend/.env (see .env.example)."
        )
    return key


def require_pinecone_key() -> str:
    key = get_settings().PINECONE_API_KEY
    if not key:
        raise RuntimeError(
            "PINECONE_API_KEY is not set. Add it to backend/.env (see .env.example)."
        )
    return key
