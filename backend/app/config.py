"""
Centralized configuration.

Everything that varies between environments (dev / prod, which LLM
provider, where files live) is read from environment variables here,
so no other module ever reaches into os.environ directly.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite:///./app.db"

    # Auth
    jwt_secret_key: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # LLM (OpenRouter - OpenAI-compatible chat completions API)
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "google/gemini-2.5-flash"

    # Embeddings
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dim: int = 384

    # Storage
    upload_dir: str = "./storage/uploads"
    faiss_index_dir: str = "./storage/faiss_index"

    # Chunking
    chunk_size: int = 800
    chunk_overlap: int = 150

    # Email (SMTP - e.g. Gmail with an App Password)
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""  # falls back to smtp_username if left blank
    verification_code_expire_minutes: int = 10

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
