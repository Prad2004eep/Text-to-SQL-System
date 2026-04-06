"""Natural-language to SQL generation with Groq and local fallbacks."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Dict, List, Optional

from groq import Groq

from config import AppConfig
from schema_loader import ForeignKeyReference


class QueryGenerationError(Exception):
    """Raised when a natural language query cannot be converted to SQL."""


@dataclass
class GeneratedQuery:
    """Generated SQL and the prompt used to create it."""

    sql: str
    prompt: str


class AIQueryGenerator:
    """Text-to-SQL generator with Groq support and local schema-aware fallback."""

    def __init__(
        self,
        schema: Dict[str, List[str]],
        foreign_keys: Optional[Dict[str, List[ForeignKeyReference]]] = None,
        config: Optional[AppConfig] = None,
    ) -> None:
        self.config = config or AppConfig()
        self.schema = schema
        self.foreign_keys = foreign_keys or {}
        self.logger = logging.getLogger(__name__)
        self.groq_client = self._build_groq_client()

    def generate_sql(self, user_query: str, error_context: Optional[str] = None) -> GeneratedQuery:
        """Generate SQL for a natural-language request with optional error context for retry."""
        normalized = self._normalize(user_query)
        
        # Handle empty/invalid input early
        if not normalized or len(normalized) < 2:
            raise QueryGenerationError(
                "Please enter a valid question about the data. "
                "Try asking about users, orders, or products."
            )
        
        prompt = self._build_prompt(user_query, error_context)

        sql = self._generate_with_groq(prompt)
        if not sql:
            sql = (
                self._generate_join_query(normalized)
                or self._generate_users_query(normalized)
                or self._generate_orders_query(normalized)
                or self._generate_products_query(normalized)
                or self._generate_generic_listing(normalized)
                or self._generate_fallback_query(normalized)
            )

        if not sql:
            raise QueryGenerationError(
                "Unable to map the request to a safe SELECT query. "
                "Try mentioning a table such as users, orders, or products and a simple filter. "
                "Examples: 'Show all users', 'List orders above 500', 'Show products cheaper than 100'"
            )

        return GeneratedQuery(sql=self._post_process_sql(sql), prompt=prompt)

    def _build_prompt(self, user_query: str, error_context: Optional[str] = None) -> str:
        """Build a schema-aware prompt with few-shot examples and optional error context."""
        schema_description = "\n".join(
            f"{table}({', '.join(columns)})" for table, columns in self.schema.items()
        )
        examples = (
            'Question: "Show all users"\n'
            "SQL: SELECT Id, Name, Age, Email FROM Users;\n\n"
            'Question: "Show all users above age 30"\n'
            "SQL: SELECT Id, Name, Age, Email FROM Users WHERE Age > 30;\n\n"
            'Question: "List orders above 500"\n'
            "SQL: SELECT OrderId, UserId, Amount, Date FROM Orders WHERE Amount > 500;\n\n"
            'Question: "Show recent orders"\n'
            "SQL: SELECT OrderId, UserId, Amount, Date FROM Orders ORDER BY Date DESC;\n\n"
            'Question: "Show products cheaper than 100"\n'
            "SQL: SELECT ProductId, Name, Price FROM Products WHERE Price < 100;\n\n"
            'Question: "Show all orders with user names"\n'
            "SQL: SELECT Orders.OrderId, Users.Name, Orders.Amount, Orders.Date FROM Orders "
            "JOIN Users ON Orders.UserId = Users.Id;\n\n"
            'Question: "List users and their total order amount"\n'
            "SQL: SELECT Users.Id, Users.Name, SUM(Orders.Amount) AS TotalOrderAmount FROM Users "
            "JOIN Orders ON Orders.UserId = Users.Id GROUP BY Users.Id, Users.Name;\n\n"
            'Question: "Show the cheapest products"\n'
            "SQL: SELECT ProductId, Name, Price FROM Products ORDER BY Price ASC LIMIT 1;"
        )
        
        error_instruction = ""
        if error_context:
            error_instruction = f"\n\nIMPORTANT: The previous SQL query failed with this error: {error_context}\nPlease fix the SQL query to resolve this error.\n"
        
        return (
            "Convert the following natural language query into SQL.\n"
            f"Database Schema:\n{schema_description}\n\n"
            "Only generate SELECT queries.\n"
            "Return only SQL with no explanation and no markdown fences.\n"
            "Use only tables and columns from the provided schema.\n\n"
            f"Examples:\n{examples}\n\n"
            f'Question: "{user_query}"\nSQL:'
        )

    def _build_groq_client(self) -> Optional[Groq]:
        """Create the Groq client when enabled and configured."""
        if not self.config.use_groq or not self.config.groq_api_key:
            return None
        return Groq(api_key=self.config.groq_api_key)

    def _generate_with_groq(self, prompt: str) -> Optional[str]:
        """Generate SQL through Groq and return cleaned SQL text."""
        if not self.groq_client:
            return None

        try:
            completion = self.groq_client.chat.completions.create(
                model=self.config.groq_model,
                temperature=0,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You convert natural language into safe SQLite SELECT queries. "
                            "Only return SQL. Never return explanations or markdown."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
            )
        except Exception as exc:
            self.logger.error("Groq generation failed: %s", exc)
            return None

        content = completion.choices[0].message.content or ""
        return self._extract_sql_from_response(content)

    def _extract_sql_from_response(self, content: str) -> Optional[str]:
        """Extract a SQL statement from a model response."""
        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```[a-zA-Z]*\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned).strip()

        # More restrictive SQL extraction - only allow safe patterns
        select_match = re.search(r"(SELECT\b[^;]*(?:;|$))", cleaned, flags=re.IGNORECASE | re.DOTALL)
        if select_match:
            sql = " ".join(select_match.group(1).split())
            # Additional safety check
            if any(dangerous in sql.upper() for dangerous in ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER"]):
                return None
            return sql if sql.endswith(";") else f"{sql};"

        return None

    def _normalize(self, text: str) -> str:
        """Normalize user text for rule matching."""
        return " ".join(text.lower().strip().split())

    def _extract_number(self, text: str) -> Optional[float]:
        """Extract the first numeric value from text."""
        match = re.search(r"(-?\d+(?:\.\d+)?)", text)
        return float(match.group(1)) if match else None

    def _extract_limit(self, text: str) -> Optional[int]:
        """Extract a requested LIMIT value from text."""
        match = re.search(r"\b(?:top|first|limit)\s+(\d+)\b", text)
        return int(match.group(1)) if match else None

    def _post_process_sql(self, sql: str) -> str:
        """Normalize SQL formatting and ensure a trailing semicolon."""
        cleaned = re.sub(r"\s+", " ", sql.strip().rstrip(";"))
        replacements = {
            "select": "SELECT",
            "from": "FROM",
            "where": "WHERE",
            "join": "JOIN",
            "on": "ON",
            "group by": "GROUP BY",
            "order by": "ORDER BY",
            "limit": "LIMIT",
            "as": "AS",
        }
        normalized = cleaned
        for source, target in replacements.items():
            normalized = re.sub(rf"\b{source}\b", target, normalized, flags=re.IGNORECASE)
        return f"{normalized};"

    def _generate_users_query(self, text: str) -> Optional[str]:
        """Generate user-centric queries using local rules."""
        if "user" not in text and "users" not in text and "customer" not in text:
            return None

        conditions: List[str] = []
        order_by = ""
        limit = self._extract_limit(text)

        if any(phrase in text for phrase in ["above age", "older than", "age above", "age greater than"]):
            value = self._extract_number(text)
            if value is not None:
                conditions.append(f"Age > {int(value)}")
        elif any(phrase in text for phrase in ["below age", "younger than", "age below", "age less than", "below", "less than"]):
            value = self._extract_number(text)
            if value is not None:
                conditions.append(f"Age < {int(value)}")
        elif "age" in text and any(word in text for word in ["=", "equal to", "exactly"]):
            value = self._extract_number(text)
            if value is not None:
                conditions.append(f"Age = {int(value)}")

        if "oldest" in text:
            order_by = " ORDER BY Age DESC"
            if limit is None:
                limit = 1
        elif "youngest" in text:
            order_by = " ORDER BY Age ASC"
            if limit is None:
                limit = 1
        elif "sort" in text or "order by age" in text:
            direction = "DESC" if "desc" in text or "highest" in text else "ASC"
            order_by = f" ORDER BY Age {direction}"

        sql = "SELECT Id, Name, Age, Email FROM Users"
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += order_by
        if limit is not None:
            sql += f" LIMIT {limit}"
        return sql + ";"

    def _generate_orders_query(self, text: str) -> Optional[str]:
        """Generate order-centric queries using local rules."""
        if "order" not in text and "orders" not in text:
            return None

        conditions: List[str] = []
        order_by = ""
        limit = self._extract_limit(text)

        if (any(phrase in text for phrase in ["above", "greater than", "more than", "over"]) and "amount" in text) or "orders above" in text:
            value = self._extract_number(text)
            if value is not None:
                conditions.append(f"Amount > {value}")
        elif (any(phrase in text for phrase in ["below", "less than", "under"]) and "amount" in text) or "orders below" in text:
            value = self._extract_number(text)
            if value is not None:
                conditions.append(f"Amount < {value}")

        date_match = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", text)
        if date_match:
            operator = ">=" if any(word in text for word in ["after", "since", "from"]) else "<="
            if any(word in text for word in ["before", "until"]):
                operator = "<="
            conditions.append(f"Date {operator} '{date_match.group(1)}'")

        if "highest" in text or "largest" in text:
            order_by = " ORDER BY Amount DESC"
            if limit is None and any(word in text for word in ["order", "orders", "show", "list"]):
                limit = 1
        elif "lowest" in text or "smallest" in text:
            order_by = " ORDER BY Amount ASC"
            if limit is None:
                limit = 1
        elif "recent" in text or "latest" in text:
            order_by = " ORDER BY Date DESC"
            if limit is None and any(word in text for word in ["latest order", "most recent order"]):
                limit = 1

        sql = "SELECT OrderId, UserId, Amount, Date FROM Orders"
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += order_by
        if limit is not None:
            sql += f" LIMIT {limit}"
        return sql + ";"

    def _generate_products_query(self, text: str) -> Optional[str]:
        """Generate product-centric queries using local rules."""
        if "product" not in text and "products" not in text:
            return None

        conditions: List[str] = []
        order_by = ""
        limit = self._extract_limit(text)

        if any(phrase in text for phrase in ["cheaper than", "below", "less than", "under"]):
            value = self._extract_number(text)
            if value is not None:
                conditions.append(f"Price < {value}")
        elif any(phrase in text for phrase in ["costlier than", "more than", "above", "over", "expensive than"]):
            value = self._extract_number(text)
            if value is not None:
                conditions.append(f"Price > {value}")

        if "highest" in text or "most expensive" in text:
            order_by = " ORDER BY Price DESC"
            if limit is None:
                limit = 1
        elif "lowest" in text or "cheapest" in text:
            order_by = " ORDER BY Price ASC"
            if limit is None:
                limit = 1

        sql = "SELECT ProductId, Name, Price FROM Products"
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += order_by
        if limit is not None:
            sql += f" LIMIT {limit}"
        return sql + ";"

    def _generate_join_query(self, text: str) -> Optional[str]:
        """Generate join and aggregate queries using discovered foreign keys."""
        join_triggers = [
            "with user names",
            "with users",
            "user names",
            "customer names",
            "join",
            "their total order amount",
            "total order amount",
        ]
        if not any(trigger in text for trigger in join_triggers):
            return None

        join_clause = self._build_join_clause("Orders", "Users")
        if not join_clause:
            return None

        if ("total order amount" in text or "sum of orders" in text) and ("user" in text or "users" in text):
            return (
                "SELECT Users.Id, Users.Name, SUM(Orders.Amount) AS TotalOrderAmount "
                f"FROM {join_clause} "
                "GROUP BY Users.Id, Users.Name "
                "ORDER BY TotalOrderAmount DESC;"
            )

        if "order" in text or "orders" in text:
            sql = (
                "SELECT Orders.OrderId, Users.Name, Orders.Amount, Orders.Date "
                f"FROM {join_clause}"
            )
            value = self._extract_number(text)
            if value is not None and any(word in text for word in ["above", "over", "greater than", "more than"]):
                sql += f" WHERE Orders.Amount > {value}"
            elif value is not None and any(word in text for word in ["below", "under", "less than"]):
                sql += f" WHERE Orders.Amount < {value}"
            if "latest" in text or "recent" in text:
                sql += " ORDER BY Orders.Date DESC"
            return sql + ";"

        return None

    def _build_join_clause(self, left_table: str, right_table: str) -> Optional[str]:
        """Build a join clause from discovered foreign key metadata."""
        for foreign_key in self.foreign_keys.get(left_table, []):
            if foreign_key["reference_table"].lower() == right_table.lower():
                return (
                    f"{left_table} JOIN {right_table} ON "
                    f"{left_table}.{foreign_key['from_column']} = "
                    f"{right_table}.{foreign_key['reference_column']}"
                )
        for foreign_key in self.foreign_keys.get(right_table, []):
            if foreign_key["reference_table"].lower() == left_table.lower():
                return (
                    f"{right_table} JOIN {left_table} ON "
                    f"{right_table}.{foreign_key['from_column']} = "
                    f"{left_table}.{foreign_key['reference_column']}"
                )
        return None

    def _generate_generic_listing(self, text: str) -> Optional[str]:
        """Generate simple listing queries."""
        normalized = text.lower().strip()
        
        # User queries
        if normalized in {"show all users", "list users", "show users", "users", "all users", "get users", "display users", "show me users", "show me the users"}:
            return "SELECT Id, Name, Age, Email FROM Users;"
        
        # Order queries  
        if normalized in {"show all orders", "list orders", "show orders", "orders", "all orders", "get orders", "display orders", "show me orders", "show me the orders"}:
            return "SELECT OrderId, UserId, Amount, Date FROM Orders;"
        
        # Product queries
        if normalized in {"show all products", "list products", "show products", "products", "all products", "get products", "display products", "show me products", "show me the products"}:
            return "SELECT ProductId, Name, Price FROM Products;"
            
        # Handle generic "show all" by defaulting to users
        if normalized in {"show all", "list all", "show everything", "list everything", "all", "everything"}:
            return "SELECT Id, Name, Age, Email FROM Users;"
            
        return None

    def _generate_fallback_query(self, text: str) -> Optional[str]:
        """Generate fallback queries for common patterns."""
        normalized = text.lower().strip()
        
        # Handle numeric context queries (e.g., "only 50", "above 30", "below 100")
        number = self._extract_number(text)
        if number is not None:
            # Handle standalone numeric queries (default to users)
            if not any(table in normalized for table in ["user", "order", "product"]):
                if any(word in normalized for word in ["only", "limit", "top", "first"]):
                    return f"SELECT Id, Name, Age, Email FROM Users LIMIT {int(number)};"
                elif any(word in normalized for word in ["above", "greater", "over", "more than"]):
                    return f"SELECT Id, Name, Age, Email FROM Users WHERE Age > {int(number)};"
                elif any(word in normalized for word in ["below", "less", "under"]):
                    return f"SELECT Id, Name, Age, Email FROM Users WHERE Age < {int(number)};"
            
            # If user mentions any table name, show that table with filter
            if "user" in normalized:
                if any(word in normalized for word in ["only", "limit", "top", "first"]):
                    return f"SELECT Id, Name, Age, Email FROM Users LIMIT {int(number)};"
                elif any(word in normalized for word in ["above", "greater", "over", "more than"]):
                    return f"SELECT Id, Name, Age, Email FROM Users WHERE Age > {int(number)};"
                elif any(word in normalized for word in ["below", "less", "under"]):
                    return f"SELECT Id, Name, Age, Email FROM Users WHERE Age < {int(number)};"
            elif "order" in normalized:
                if any(word in normalized for word in ["only", "limit", "top", "first"]):
                    return f"SELECT OrderId, UserId, Amount, Date FROM Orders LIMIT {int(number)};"
                elif any(word in normalized for word in ["above", "greater", "over", "more than"]):
                    return f"SELECT OrderId, UserId, Amount, Date FROM Orders WHERE Amount > {number};"
                elif any(word in normalized for word in ["below", "less", "under"]):
                    return f"SELECT OrderId, UserId, Amount, Date FROM Orders WHERE Amount < {number};"
            elif "product" in normalized:
                if any(word in normalized for word in ["only", "limit", "top", "first"]):
                    return f"SELECT ProductId, Name, Price FROM Products LIMIT {int(number)};"
                elif any(word in normalized for word in ["above", "greater", "over", "more than"]):
                    return f"SELECT ProductId, Name, Price FROM Products WHERE Price > {number};"
                elif any(word in normalized for word in ["below", "less", "under", "cheaper"]):
                    return f"SELECT ProductId, Name, Price FROM Products WHERE Price < {number};"
        
        # If user mentions any table name, show that table
        if "user" in normalized:
            return "SELECT Id, Name, Age, Email FROM Users;"
        elif "order" in normalized:
            return "SELECT OrderId, UserId, Amount, Date FROM Orders;"
        elif "product" in normalized:
            return "SELECT ProductId, Name, Price FROM Products;"
        
        # If user asks to "show" or "list" anything, default to users
        if any(word in normalized for word in ["show", "list", "get", "display", "find"]):
            return "SELECT Id, Name, Age, Email FROM Users;"
            
        return None
