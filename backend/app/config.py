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
    ollama_model: str = "mistral:latest"
    ollama_baseline_identifier: str = "6577803aa9a0"

    # ── Groq (reasoning mode — optional) ─────────────────
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    # Temperature for medical answers (low = more factual)
    llm_temperature: float = 0.1
    reasoning_plan_timeout_seconds: int = 25
    reasoning_research_timeout_seconds: int = 120
    reasoning_synthesis_timeout_seconds: int = 120
    reasoning_local_fallback_timeout_seconds: int = 45
    reasoning_progress_heartbeat_seconds: int = 8
    reasoning_verbose_output: bool = True

    # ── Whisper (speech-to-text) ─────────────────────────
    whisper_model: str = "small"

    # ── RAG ──────────────────────────────────────────────
    chroma_persist_dir: str = "./data/chroma_db"
    # Use a higher-quality embedding model for medical retrieval
    # NOTE: re-ingest your knowledge base after changing embeddings
    embedding_model: str = "BAAI/bge-large-en-v1.5"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",  # Ignore extra env vars that aren't defined here
    }


# Single global instance — import this everywhere
settings = Settings()
