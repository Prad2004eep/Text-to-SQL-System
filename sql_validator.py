"""SQL validation helpers for safe local execution."""

from __future__ import annotations

import logging
import re
from typing import Dict, List, Set

import sqlparse
from sqlparse.sql import Identifier, IdentifierList
from sqlparse.tokens import DML, Keyword, Wildcard


class SQLValidationError(Exception):
    """Raised when SQL fails security or schema validation."""


class SQLValidator:
    """Validate that a query is a safe SELECT over known schema objects."""

    FORBIDDEN_KEYWORDS = {"DELETE", "DROP", "UPDATE", "INSERT", "ALTER", "TRUNCATE", "CREATE", "REPLACE"}

    def __init__(self, schema: Dict[str, List[str]], max_joins: int = 2, max_query_length: int = 1200) -> None:
        self.schema = schema
        self.tables_lower = {table.lower(): table for table in schema}
        self.max_joins = max_joins
        self.max_query_length = max_query_length
        self.logger = logging.getLogger(__name__)

    def validate(self, sql: str) -> None:
        """Validate query safety, schema correctness, and basic complexity."""
        self._validate_query_complexity(sql)
        parsed = sqlparse.parse(sql)
        if not parsed:
            raise SQLValidationError("No SQL query was generated.")

        statement = parsed[0]
        if statement.get_type() != "SELECT":
            raise SQLValidationError("Only SELECT queries are allowed.")

        upper_sql = sql.upper()
        for keyword in self.FORBIDDEN_KEYWORDS:
            if re.search(rf"\b{keyword}\b", upper_sql):
                raise SQLValidationError(f"Unsafe query blocked: {keyword} statements are not allowed.")

        tables = self._extract_tables(statement)
        if not tables:
            raise SQLValidationError("No valid table reference found in the query.")

        canonical_tables: List[str] = []
        for table in tables:
            if table.lower() not in self.tables_lower:
                raise SQLValidationError(f"Unknown table referenced: {table}")
            canonical_tables.append(self.tables_lower[table.lower()])

        aliases = self._extract_aliases(statement)
        columns = self._extract_columns(statement)
        self._validate_columns(columns, canonical_tables, aliases)
        self.logger.info("SQL validation succeeded")

    def _validate_query_complexity(self, sql: str) -> None:
        """Reject queries that are too long or too complex for this local app."""
        if len(sql) > self.max_query_length:
            raise SQLValidationError("Query is too long and was blocked.")
        if sql.count(";") > 1:
            raise SQLValidationError("Multiple SQL statements are not allowed.")
        if re.search(r"\bUNION\b|\bINTERSECT\b|\bEXCEPT\b", sql, flags=re.IGNORECASE):
            raise SQLValidationError("Set operations are not allowed.")
        if len(re.findall(r"\bJOIN\b", sql, flags=re.IGNORECASE)) > self.max_joins:
            raise SQLValidationError("Query has too many joins.")
        if len(re.findall(r"\bSELECT\b", sql, flags=re.IGNORECASE)) > 1:
            raise SQLValidationError("Nested queries are not allowed.")

    def _extract_tables(self, statement) -> List[str]:
        """Extract referenced table names from a parsed statement."""
        tables: List[str] = []
        from_seen = False

        for token in statement.tokens:
            if token.is_whitespace:
                continue
            if token.ttype is Keyword and token.value.upper() == "FROM":
                from_seen = True
                continue
            if not from_seen:
                continue
            if isinstance(token, IdentifierList):
                for identifier in token.get_identifiers():
                    tables.append(identifier.get_real_name() or identifier.get_name())
            elif isinstance(token, Identifier):
                tables.append(token.get_real_name() or token.get_name())
            elif token.ttype is Keyword and "JOIN" in token.value.upper():
                continue
            elif token.ttype is Keyword:
                break

        tables.extend(re.findall(r"\bJOIN\s+([A-Za-z_][A-Za-z0-9_]*)", str(statement), flags=re.IGNORECASE))

        unique_tables: List[str] = []
        for table in tables:
            if table and table not in unique_tables:
                unique_tables.append(table)
        return unique_tables

    def _extract_aliases(self, statement) -> Dict[str, str]:
        """Extract table aliases from a parsed statement."""
        aliases: Dict[str, str] = {}
        for token in statement.tokens:
            if isinstance(token, Identifier):
                real_name = token.get_real_name()
                alias = token.get_alias()
                if real_name and alias:
                    aliases[alias.lower()] = real_name

        join_aliases = re.findall(
            r"\b(?:FROM|JOIN)\s+([A-Za-z_][A-Za-z0-9_]*)(?:\s+AS)?\s+([A-Za-z_][A-Za-z0-9_]*)",
            str(statement),
            flags=re.IGNORECASE,
        )
        for table, alias in join_aliases:
            if alias.upper() not in {"ON", "WHERE", "ORDER", "LIMIT", "GROUP"}:
                aliases[alias.lower()] = table
        return aliases

    def _extract_columns(self, statement) -> Set[str]:
        """Extract column references from SELECT, WHERE, GROUP BY, and ORDER BY."""
        columns: Set[str] = set()
        select_seen = False

        for token in statement.tokens:
            if token.is_whitespace:
                continue
            if token.ttype is DML and token.value.upper() == "SELECT":
                select_seen = True
                continue
            if not select_seen:
                continue
            if token.ttype is Keyword and token.value.upper() == "FROM":
                break
            if isinstance(token, IdentifierList):
                for identifier in token.get_identifiers():
                    columns.add(identifier.value.strip())
            elif isinstance(token, Identifier):
                columns.add(token.value.strip())
            elif token.ttype is Wildcard:
                columns.add("*")

        where_columns = re.findall(
            r"\b([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)?)\b\s*(?:=|<|>|<=|>=|!=|LIKE)",
            str(statement),
            flags=re.IGNORECASE,
        )
        columns.update(where_columns)

        grouped_columns = re.findall(
            r"\b(?:GROUP BY|ORDER BY)\s+([A-Za-z_][A-Za-z0-9_\. ,]*)",
            str(statement),
            flags=re.IGNORECASE,
        )
        for grouped_column in grouped_columns:
            for part in grouped_column.split(","):
                cleaned_part = part.strip().split()[0]
                if cleaned_part:
                    columns.add(cleaned_part)

        return columns

    def _validate_columns(self, columns: Set[str], tables: List[str], aliases: Dict[str, str]) -> None:
        """Validate all referenced columns against the live schema."""
        valid_columns = {table: {column.lower() for column in self.schema[table]} for table in tables}
        all_columns = {column for columns_set in valid_columns.values() for column in columns_set}

        for raw_column in columns:
            if raw_column == "*":
                continue

            cleaned = raw_column.strip()
            if "(" in cleaned and ")" in cleaned:
                continue

            cleaned = re.sub(r"\s+AS\s+[A-Za-z_][A-Za-z0-9_]*$", "", cleaned, flags=re.IGNORECASE)
            cleaned = cleaned.strip('"')

            if "." in cleaned:
                prefix, column_name = cleaned.split(".", 1)
                table_name = aliases.get(prefix.lower(), prefix)
                canonical_table = self.tables_lower.get(table_name.lower())
                if not canonical_table:
                    raise SQLValidationError(f"Unknown table or alias used in column reference: {prefix}")
                if column_name.lower() not in {column.lower() for column in self.schema[canonical_table]}:
                    raise SQLValidationError(f"Unknown column referenced: {column_name} on table {canonical_table}")
            else:
                if cleaned.lower() not in all_columns:
                    raise SQLValidationError(f"Unknown column referenced: {cleaned}")
