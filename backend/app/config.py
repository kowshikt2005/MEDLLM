"""
Application configuration.

Uses pydantic-settings to read from environment variables or a .env file.
Every setting has a sensible default so the app works out-of-the-box
without any .env file for local development.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── App ──────────────────────────────────────────────
    app_name: str = "MedLLM"
    debug: bool = True

    # ── Database ─────────────────────────────────────────
    # SQLite file path. Relative to where uvicorn is started.
    database_url: str = "sqlite+aiosqlite:///./data/medllm.db"

    # ── Auth / JWT ───────────────────────────────────────
    # IMPORTANT: Change this in production! This is just for local dev.
    secret_key: str = "dev-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24 hours

    # ── Ollama (local LLM) ───────────────────────────────
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "mistral"  # Will become "medllm" after fine-tuning

    # ── Groq (reasoning mode — optional) ─────────────────
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    # ── Whisper (speech-to-text) ─────────────────────────
    whisper_model: str = "small"

    # ── RAG ──────────────────────────────────────────────
    chroma_persist_dir: str = "./data/chroma_db"
    embedding_model: str = "all-MiniLM-L6-v2"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",  # Ignore extra env vars that aren't defined here
    }


# Single global instance — import this everywhere
settings = Settings()
