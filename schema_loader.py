"""Database creation and schema inspection helpers."""

from __future__ import annotations

import logging
import sqlite3
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, TypedDict


DATABASE_PATH = Path("database.db")
LOGGER = logging.getLogger(__name__)


class ForeignKeyReference(TypedDict):
    """Foreign key relationship metadata."""

    from_column: str
    reference_table: str
    reference_column: str


class SchemaMetadata(TypedDict):
    """Structured schema metadata for prompting and validation."""

    tables: Dict[str, List[str]]
    foreign_keys: Dict[str, List[ForeignKeyReference]]


def initialize_database(db_path: str = str(DATABASE_PATH)) -> None:
    """Create the SQLite database and seed sample data when empty."""
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS Users (
            Id INTEGER PRIMARY KEY,
            Name TEXT NOT NULL,
            Age INTEGER NOT NULL,
            Email TEXT NOT NULL
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS Orders (
            OrderId INTEGER PRIMARY KEY,
            UserId INTEGER NOT NULL,
            Amount REAL NOT NULL,
            Date TEXT NOT NULL,
            FOREIGN KEY (UserId) REFERENCES Users (Id)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS Products (
            ProductId INTEGER PRIMARY KEY,
            Name TEXT NOT NULL,
            Price REAL NOT NULL
        )
        """
    )
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

    users_count = cursor.execute("SELECT COUNT(*) FROM Users").fetchone()[0]
    orders_count = cursor.execute("SELECT COUNT(*) FROM Orders").fetchone()[0]
    products_count = cursor.execute("SELECT COUNT(*) FROM Products").fetchone()[0]

    if users_count == 0:
        cursor.executemany(
            "INSERT INTO Users (Id, Name, Age, Email) VALUES (?, ?, ?, ?)",
            [
                (1, "Alice Johnson", 28, "alice@example.com"),
                (2, "Bob Smith", 35, "bob@example.com"),
                (3, "Carol Davis", 41, "carol@example.com"),
                (4, "David Wilson", 22, "david@example.com"),
                (5, "Eva Brown", 31, "eva@example.com"),
                (6, "Frank Miller", 45, "frank@example.com"),
                (7, "Grace Lee", 27, "grace@example.com"),
                (8, "Henry Clark", 38, "henry@example.com"),
                (9, "Ivy Turner", 29, "ivy@example.com"),
                (10, "Jack White", 33, "jack@example.com"),
            ],
        )

    if orders_count == 0:
        cursor.executemany(
            "INSERT INTO Orders (OrderId, UserId, Amount, Date) VALUES (?, ?, ?, ?)",
            [
                (1, 1, 120.50, "2024-01-05"),
                (2, 2, 540.00, "2024-01-11"),
                (3, 3, 90.25, "2024-01-20"),
                (4, 4, 710.90, "2024-02-03"),
                (5, 5, 320.40, "2024-02-12"),
                (6, 6, 860.00, "2024-03-01"),
                (7, 7, 45.99, "2024-03-15"),
                (8, 8, 580.75, "2024-04-08"),
                (9, 9, 250.00, "2024-04-18"),
                (10, 10, 999.99, "2024-05-10"),
            ],
        )

    if products_count == 0:
        cursor.executemany(
            "INSERT INTO Products (ProductId, Name, Price) VALUES (?, ?, ?)",
            [
                (1, "Laptop", 999.99),
                (2, "Mouse", 25.50),
                (3, "Keyboard", 75.00),
                (4, "Monitor", 180.00),
                (5, "Desk Lamp", 45.00),
                (6, "Headphones", 89.99),
                (7, "USB Cable", 9.99),
                (8, "Webcam", 55.00),
                (9, "External SSD", 149.99),
                (10, "Office Chair", 210.00),
            ],
        )

    connection.commit()
    connection.close()
    LOGGER.info("Database initialized at %s", db_path)


@lru_cache(maxsize=4)
def load_schema_metadata(db_path: str = str(DATABASE_PATH)) -> SchemaMetadata:
    """Load tables, columns, and foreign keys from SQLite."""
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()

    tables = cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()

    schema: Dict[str, List[str]] = {}
    foreign_keys: Dict[str, List[ForeignKeyReference]] = {}
    for (table_name,) in tables:
        columns = cursor.execute(f"PRAGMA table_info({table_name})").fetchall()
        schema[table_name] = [column[1] for column in columns]
        foreign_keys[table_name] = [
            {
                "from_column": fk[3],
                "reference_table": fk[2],
                "reference_column": fk[4],
            }
            for fk in cursor.execute(f"PRAGMA foreign_key_list({table_name})").fetchall()
        ]

    connection.close()
    LOGGER.info("Loaded schema metadata for %d tables", len(schema))
    return {"tables": schema, "foreign_keys": foreign_keys}


def load_schema(db_path: str = str(DATABASE_PATH)) -> Dict[str, List[str]]:
    """Load only table and column information."""
    return load_schema_metadata(db_path)["tables"]


def format_schema_for_prompt(schema: Dict[str, List[str]]) -> str:
    """Format schema into a prompt-friendly string."""
    return "\n".join(f"{table}({', '.join(columns)})" for table, columns in schema.items())
