"""Centralized config. Read env vars only here."""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    llm_model: str
    llm_base_url: str | None  # set for OpenAI-compatible providers (Groq, Ollama, etc.)
    embedding_model: str
    chroma_path: str
    top_k: int
    log_level: str


def get_settings() -> Settings:
    base_url = os.environ.get("LLM_BASE_URL", "").strip() or None
    return Settings(
        openai_api_key=os.environ.get("OPENAI_API_KEY", ""),
        llm_model=os.environ.get("LLM_MODEL", "gpt-4o-mini"),
        llm_base_url=base_url,
        embedding_model=os.environ.get(
            "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
        ),
        chroma_path=os.environ.get("CHROMA_PATH", "./data/chroma"),
        top_k=int(os.environ.get("TOP_K", "5")),
        log_level=os.environ.get("LOG_LEVEL", "INFO"),
    )
