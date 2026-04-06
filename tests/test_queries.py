"""Regression tests for the Text-to-SQL system."""

from __future__ import annotations

from pathlib import Path

from ai_query_generator import AIQueryGenerator
from config import AppConfig
from history_manager import QueryHistoryManager
from query_executor import QueryExecutor
from query_service import QueryService
from result_formatter import ResultFormatter
from schema_loader import initialize_database, load_schema_metadata
from sql_validator import SQLValidationError, SQLValidator


def build_service(tmp_path: Path) -> QueryService:
    """Create a fully wired query service for tests."""
    db_path = tmp_path / "test_database.db"
    initialize_database(str(db_path))
    metadata = load_schema_metadata(str(db_path))
    config = AppConfig(
        database_path=db_path,
        use_groq=False,
        max_history_items=5,
        max_query_length=1200,
        max_joins=2,
    )
    generator = AIQueryGenerator(
        schema=metadata["tables"],
        foreign_keys=metadata["foreign_keys"],
        config=config,
    )
    validator = SQLValidator(metadata["tables"], max_joins=config.max_joins, max_query_length=config.max_query_length)
    executor = QueryExecutor(str(db_path))
    formatter = ResultFormatter()
    history = QueryHistoryManager(str(db_path), max_items=5)
    return QueryService(generator, validator, executor, formatter, history)


def test_valid_user_query(tmp_path: Path) -> None:
    """Simple user filters should succeed."""
    service = build_service(tmp_path)
    response = service.process_query("Show all users above age 30")
    assert response["status"] == "success"
    assert "WHERE Age > 30" in response["data"]["sql"]
    assert response["data"]["row_count"] > 0


def test_join_aggregate_query(tmp_path: Path) -> None:
    """Aggregate join queries should succeed."""
    service = build_service(tmp_path)
    response = service.process_query("List users and their total order amount")
    assert response["status"] == "success"
    assert "GROUP BY Users.Id, Users.Name" in response["data"]["sql"]
    assert "TotalOrderAmount" in response["data"]["results"].columns


def test_unsafe_sql_is_blocked(tmp_path: Path) -> None:
    """Validator should block non-SELECT SQL."""
    db_path = tmp_path / "test_database.db"
    initialize_database(str(db_path))
    metadata = load_schema_metadata(str(db_path))
    validator = SQLValidator(metadata["tables"])
    try:
        validator.validate("DROP TABLE Users;")
    except SQLValidationError as exc:
        assert "Only SELECT queries are allowed." in str(exc)
    else:
        raise AssertionError("DROP TABLE should have been blocked")


def test_unknown_column_is_blocked(tmp_path: Path) -> None:
    """Validator should reject hallucinated columns."""
    db_path = tmp_path / "test_database.db"
    initialize_database(str(db_path))
    metadata = load_schema_metadata(str(db_path))
    validator = SQLValidator(metadata["tables"])
    try:
        validator.validate("SELECT FakeColumn FROM Users;")
    except SQLValidationError as exc:
        assert "Unknown column referenced" in str(exc)
    else:
        raise AssertionError("Hallucinated column should have been blocked")
