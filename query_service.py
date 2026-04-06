"""Orchestration layer for query generation, validation, and execution."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict

from ai_query_generator import AIQueryGenerator, QueryGenerationError
from context_manager import ContextManager
from history_manager import QueryHistoryManager
from query_executor import QueryExecutionError, QueryExecutor
from result_formatter import ResultFormatter
from sql_explainer import SQLExplainer
from sql_validator import SQLValidationError, SQLValidator


LOGGER = logging.getLogger(__name__)


class QueryService:
    """High-level service that processes a natural language query end to end."""

    def __init__(
        self,
        query_generator: AIQueryGenerator,
        validator: SQLValidator,
        executor: QueryExecutor,
        formatter: ResultFormatter,
        history_manager: QueryHistoryManager,
    ) -> None:
        self.query_generator = query_generator
        self.validator = validator
        self.executor = executor
        self.formatter = formatter
        self.history_manager = history_manager
        self.explainer = SQLExplainer()
        self.context_manager = ContextManager()

    def process_query(self, user_query: str) -> Dict[str, Any]:
        """Generate, validate, execute, and format a query response with auto-correction."""
        started = time.perf_counter()
        cleaned_query = user_query.strip()
        if not cleaned_query:
            return self._error_response("Please enter a question.")

        # Resolve conversational context
        resolved_query = self.context_manager.resolve_query(cleaned_query)

        max_attempts = 2
        last_error = None
        
        for attempt in range(max_attempts):
            try:
                if attempt > 0:
                    # Generate SQL with error context for retry
                    generated = self.query_generator.generate_sql(
                        resolved_query, 
                        error_context=last_error
                    )
                else:
                    generated = self.query_generator.generate_sql(resolved_query)
                
                self.validator.validate(generated.sql)
                results = self.executor.execute(generated.sql)
                execution_time = time.perf_counter() - started
                self.history_manager.add_entry(cleaned_query, generated.sql)
                
                # Generate SQL explanation
                explanation = self.explainer.explain(generated.sql)
                
                # Update conversational context
                self.context_manager.update_context(cleaned_query, resolved_query, generated.sql, explanation)

                LOGGER.info("Query processed successfully for input: %s", cleaned_query)
                return {
                    "status": "success",
                    "message": "Query executed successfully." if not results.empty else "Query executed successfully, but no rows matched.",
                    "data": {
                        "user_query": cleaned_query,
                        "resolved_query": resolved_query,
                        "sql": generated.sql,
                        "explanation": explanation,
                        "prompt": generated.prompt,
                        "results": results,
                        "formatted_results": self.formatter.format(results),
                        "execution_time_seconds": execution_time,
                        "row_count": int(len(results.index)),
                        "attempts": attempt + 1,
                    },
                }
            except (QueryGenerationError, SQLValidationError, QueryExecutionError) as exc:
                last_error = str(exc)
                LOGGER.warning("Query attempt %d failed: %s", attempt + 1, exc)
                if attempt == max_attempts - 1:  # Last attempt
                    LOGGER.error("All query attempts failed for input: %s", cleaned_query)
                    return self._error_response(f"Query failed after {max_attempts} attempts. Last error: {last_error}")
            except Exception as exc:  # pragma: no cover
                LOGGER.exception("Unexpected failure while processing query")
                return self._error_response(f"Unexpected error: {exc}")

    def _error_response(self, message: str) -> Dict[str, Any]:
        """Return a consistent error payload."""
        return {"status": "error", "message": message, "data": None}
