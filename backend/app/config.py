from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://recruit:recruit_secret@localhost:5432/recruitment"
    DATABASE_URL_SYNC: str = "postgresql+psycopg2://recruit:recruit_secret@localhost:5432/recruitment"
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION: str = "candidates"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:3b"
    EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"
    RERANKER_MODEL: str = "BAAI/bge-reranker-v2-m3"
    EMBEDDING_DIM: int = 384
    PDF_STORAGE_PATH: str = "./storage/pdfs"
    SECRET_KEY: str = "recruit-beta-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    DEMO_USERNAME: str = "demo"
    DEMO_PASSWORD: str = "demo123"
    RERANK_TOP_N: int = 20
    SEARCH_RETURN_TOP: int = 20

    model_config = {"env_file": "../.env", "extra": "ignore"}


settings = Settings()

BACKEND_ROOT = Path(__file__).resolve().parent.parent
PDF_STORAGE = BACKEND_ROOT / settings.PDF_STORAGE_PATH
PDF_STORAGE.mkdir(parents=True, exist_ok=True)
