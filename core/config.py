"""
core/config.py
--------------
Central configuration loader for Buildway AI Core.
Reads environment variables from .env (via python-dotenv).
Never hardcode real keys here — use .env.example as reference.
"""

import os
from dataclasses import dataclass

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv not installed; fall back to os.environ only
    pass


@dataclass(frozen=True)
class AppConfig:
    """Immutable config snapshot loaded at startup."""

    # Supabase
    supabase_url: str
    supabase_service_key: str

    # Qdrant
    qdrant_url: str
    qdrant_api_key: str

    # LLM providers (tenant-supplied keys override these at call time)
    openai_api_key: str
    anthropic_api_key: str


def load_config() -> AppConfig:
    """
    Load configuration from environment variables.
    Missing required vars will raise ValueError at startup — fail fast.
    """

    def _require(key: str) -> str:
        value = os.getenv(key, "")
        if not value:
            raise ValueError(
                f"Missing required environment variable: {key}. "
                f"Check .env.example for the full list."
            )
        return value

    def _optional(key: str, default: str = "") -> str:
        return os.getenv(key, default)

    return AppConfig(
        supabase_url=_require("SUPABASE_URL"),
        supabase_service_key=_require("SUPABASE_SERVICE_KEY"),
        qdrant_url=_optional("QDRANT_URL", "http://localhost:6333"),
        qdrant_api_key=_optional("QDRANT_API_KEY", ""),
        openai_api_key=_optional("OPENAI_API_KEY", ""),
        anthropic_api_key=_optional("ANTHROPIC_API_KEY", ""),
    )


def load_config_safe() -> AppConfig:
    """
    Like load_config() but tolerates missing vars (for local dev / testing).
    Returns an AppConfig with empty strings for missing values.
    """
    return AppConfig(
        supabase_url=os.getenv("SUPABASE_URL", ""),
        supabase_service_key=os.getenv("SUPABASE_SERVICE_KEY", ""),
        qdrant_url=os.getenv("QDRANT_URL", "http://localhost:6333"),
        qdrant_api_key=os.getenv("QDRANT_API_KEY", ""),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
    )
