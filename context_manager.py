"""Conversation context management for follow-up data questions."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Optional


LOGGER = logging.getLogger(__name__)


@dataclass
class QueryContext:
    """Remember the latest resolved query context for conversational follow-ups."""

    user_query: str
    resolved_query: str
    sql: str
    explanation: str


class ContextManager:
    """Maintain lightweight session memory and resolve follow-up prompts."""

    def __init__(self) -> None:
        self._last_context: Optional[QueryContext] = None

    def resolve_query(self, user_query: str) -> str:
        """Resolve short follow-up prompts against the previous context."""
        cleaned_query = user_query.strip()
        if not cleaned_query or not self._last_context:
            return cleaned_query
        if not self._is_follow_up(cleaned_query):
            return cleaned_query

        resolved = self._resolve_follow_up(cleaned_query, self._last_context)
        LOGGER.info("Resolved follow-up query '%s' to '%s'", cleaned_query, resolved)
        return resolved

    def update_context(self, user_query: str, resolved_query: str, sql: str, explanation: str) -> None:
        """Store the most recent successful interaction."""
        self._last_context = QueryContext(
            user_query=user_query.strip(),
            resolved_query=resolved_query.strip(),
            sql=sql.strip(),
            explanation=explanation.strip(),
        )

    def get_last_context(self) -> Optional[QueryContext]:
        """Return the latest stored context."""
        return self._last_context

    def _is_follow_up(self, user_query: str) -> bool:
        """Detect whether the current prompt likely depends on prior context."""
        normalized = user_query.strip().lower()
        standalone_terms = {"users", "user", "orders", "order", "products", "product", "show", "list", "find"}
        if any(term in normalized for term in standalone_terms):
            return False

        follow_up_prefixes = (
            "only",
            "and",
            "what about",
            "above",
            "below",
            "over",
            "under",
            "greater than",
            "less than",
            "older than",
            "younger than",
            "sort",
            "order by",
            "latest",
            "recent",
        )
        return len(normalized.split()) <= 8 or normalized.startswith(follow_up_prefixes)

    def _resolve_follow_up(self, user_query: str, context: QueryContext) -> str:
        """Map a short follow-up to a standalone query phrase."""
        normalized = user_query.strip().lower()
        last_sql_upper = context.sql.upper()

        if "FROM USERS" in last_sql_upper:
            return self._resolve_user_follow_up(normalized)
        if "FROM ORDERS" in last_sql_upper:
            return self._resolve_order_follow_up(normalized)
        if "FROM PRODUCTS" in last_sql_upper:
            return self._resolve_product_follow_up(normalized)
        return f"{context.resolved_query} {user_query}".strip()

    def _resolve_user_follow_up(self, follow_up: str) -> str:
        base = "Show all users"
        if self._contains_comparison(follow_up):
            return f"{base} {self._strip_leading_only(follow_up)}"
        if "latest" in follow_up or "recent" in follow_up:
            return f"{base} sorted by age desc"
        return f"{base} {self._strip_leading_only(follow_up)}"

    def _resolve_order_follow_up(self, follow_up: str) -> str:
        base = "Show all orders"
        if self._contains_comparison(follow_up) and "amount" not in follow_up:
            return f"{base} with amount {self._strip_leading_only(follow_up)}"
        return f"{base} {self._strip_leading_only(follow_up)}"

    def _resolve_product_follow_up(self, follow_up: str) -> str:
        base = "Show all products"
        if self._contains_comparison(follow_up) and "price" not in follow_up:
            return f"{base} with price {self._strip_leading_only(follow_up)}"
        return f"{base} {self._strip_leading_only(follow_up)}"

    def _contains_comparison(self, text: str) -> bool:
        return bool(re.search(r"\b(above|below|over|under|greater than|less than|older than|younger than)\b", text))

    def _strip_leading_only(self, text: str) -> str:
        return re.sub(r"^(only|and)\s+", "", text).strip()
