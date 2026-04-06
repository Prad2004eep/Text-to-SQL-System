"""Input handling utilities for the Text-to-SQL CLI."""

from __future__ import annotations

from typing import Optional


class InputHandler:
    """Collect CLI input and interpret command shortcuts."""

    def get_user_query(self) -> str:
        """Read a natural language query from stdin."""
        return input("\nEnter a question about your data (or type 'exit'): ").strip()

    def get_command(self, query: str) -> Optional[str]:
        """Return a recognized CLI command if present."""
        normalized = query.strip().lower()
        if normalized in {"exit", "history", "help", "clear"}:
            return normalized
        return None
