"""Central configuration for the Text-to-SQL system."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


def _parse_bool(value: str | None, default: bool) -> bool:
    """Convert an environment string into a boolean value."""
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class AppConfig:
    """Application-wide runtime settings."""

    database_path: Path = Path("database.db")
    use_groq: bool = _parse_bool(os.getenv("TEXT_TO_SQL_USE_GROQ"), False)
    groq_model: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    log_level: str = os.getenv("TEXT_TO_SQL_LOG_LEVEL", "INFO").upper()
    max_history_items: int = int(os.getenv("TEXT_TO_SQL_MAX_HISTORY", "5"))
    max_query_length: int = int(os.getenv("TEXT_TO_SQL_MAX_QUERY_LENGTH", "1200"))
    max_joins: int = int(os.getenv("TEXT_TO_SQL_MAX_JOINS", "2"))
    max_retry_attempts: int = int(os.getenv("TEXT_TO_SQL_MAX_RETRY_ATTEMPTS", "2"))


def configure_logging(level: str) -> None:
    """Initialize application logging once."""
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
