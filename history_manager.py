"""Session query history support."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import sqlite3
from typing import List


@dataclass(frozen=True)
class QueryHistoryEntry:
    """Single query execution history record."""

    user_query: str
    sql: str
    timestamp: str


class QueryHistoryManager:
    """SQLite-backed query history with a configurable max size."""

    def __init__(self, db_path: str, max_items: int = 5) -> None:
        self.db_path = db_path
        self.max_items = max_items
        self._initialize_storage()

    def add_entry(self, user_query: str, sql: str) -> None:
        """Append a new history entry and trim to max size."""
        entry = QueryHistoryEntry(
            user_query=user_query.strip(),
            sql=sql.strip(),
            timestamp=datetime.now().isoformat(timespec="seconds"),
        )
        connection = sqlite3.connect(self.db_path)
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO QueryHistory (UserQuery, SQLText, Timestamp) VALUES (?, ?, ?)",
            (entry.user_query, entry.sql, entry.timestamp),
        )
        cursor.execute(
            """
            DELETE FROM QueryHistory
            WHERE HistoryId NOT IN (
                SELECT HistoryId
                FROM QueryHistory
                ORDER BY HistoryId DESC
                LIMIT ?
            )
            """,
            (self.max_items,),
        )
        connection.commit()
        connection.close()

    def search_history(self, search_term: str) -> List[QueryHistoryEntry]:
        """Search history entries by user query content."""
        connection = sqlite3.connect(self.db_path)
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT UserQuery, SQLText, Timestamp
            FROM QueryHistory
            WHERE UserQuery LIKE ?
            ORDER BY Timestamp DESC
            LIMIT ?
            """,
            (f"%{search_term}%", self.max_items),
        )
        rows = cursor.fetchall()
        connection.close()
        return [
            QueryHistoryEntry(
                user_query=row[0],
                sql=row[1],
                timestamp=row[2],
            )
            for row in rows
        ]

    def get_recent_entries(self) -> List[QueryHistoryEntry]:
        """Return recent entries in reverse chronological order."""
        connection = sqlite3.connect(self.db_path)
        cursor = connection.cursor()
        rows = cursor.execute(
            """
            SELECT UserQuery, SQLText, Timestamp
            FROM QueryHistory
            ORDER BY HistoryId DESC
            LIMIT ?
            """,
            (self.max_items,),
        ).fetchall()
        connection.close()
        return [
            QueryHistoryEntry(user_query=row[0], sql=row[1], timestamp=row[2])
            for row in rows
        ]

    def _initialize_storage(self) -> None:
        """Ensure the query history table exists."""
        connection = sqlite3.connect(self.db_path)
        cursor = connection.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS QueryHistory (
                HistoryId INTEGER PRIMARY KEY AUTOINCREMENT,
                UserQuery TEXT NOT NULL,
                SQLText TEXT NOT NULL,
                Timestamp TEXT NOT NULL
            )
            """
        )
        connection.commit()
        connection.close()
