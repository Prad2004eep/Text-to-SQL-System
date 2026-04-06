"""Convert SQL queries into plain-English explanations."""

from __future__ import annotations

import re


class SQLExplainer:
    """Rule-based SQL explainer for local, deterministic summaries."""

    def explain(self, sql: str) -> str:
        """Return a concise human-readable explanation for a SQL query."""
        normalized = " ".join(sql.strip().rstrip(";").split())
        upper_sql = normalized.upper()

        if " JOIN " in upper_sql and "SUM(" in upper_sql:
            return "This query joins related tables and calculates an aggregated total for each grouped record."
        if " JOIN " in upper_sql:
            return "This query combines data from related tables and returns the selected matching records."

        table_match = re.search(r"\bFROM\s+([A-Za-z_][A-Za-z0-9_]*)", normalized, flags=re.IGNORECASE)
        table_name = table_match.group(1) if table_match else "the database"
        base = f"This query retrieves data from {table_name}."

        where_match = re.search(r"\bWHERE\s+(.+?)(?:\bGROUP BY\b|\bORDER BY\b|\bLIMIT\b|$)", normalized, flags=re.IGNORECASE)
        if where_match:
            base = (
                f"This query retrieves data from {table_name} where "
                f"{self._humanize_conditions(where_match.group(1))}."
            )

        if "GROUP BY" in upper_sql:
            base += " It groups the results before returning them."
        if "ORDER BY" in upper_sql:
            base += " It sorts the results."
        if "LIMIT" in upper_sql:
            limit_match = re.search(r"\bLIMIT\s+(\d+)", normalized, flags=re.IGNORECASE)
            if limit_match:
                base += f" It returns only the first {limit_match.group(1)} row(s)."
        return base

    def _humanize_conditions(self, conditions: str) -> str:
        """Translate common SQL predicates into plain language."""
        humanized = conditions
        replacements = (
            (r"\bAND\b", "and"),
            (r"\bOR\b", "or"),
            (r">=", "is greater than or equal to"),
            (r"<=", "is less than or equal to"),
            (r"!=", "is not equal to"),
            (r">", "is greater than"),
            (r"<", "is less than"),
            (r"=", "is equal to"),
        )
        for pattern, replacement in replacements:
            humanized = re.sub(pattern, f" {replacement} ", humanized, flags=re.IGNORECASE)
        return " ".join(humanized.replace("_", " ").split())
