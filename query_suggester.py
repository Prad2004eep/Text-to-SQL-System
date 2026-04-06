"""Smart query suggestion engine based on context and patterns."""

from __future__ import annotations

from typing import List, Optional


class QuerySuggester:
    """Generate contextual query suggestions for follow-up questions."""

    def __init__(self) -> None:
        """Initialize the query suggester with base suggestions."""
        self.base_suggestions: List[str] = [
            "Show all users",
            "Show all orders", 
            "Show all products",
            "Show users above age 30",
            "List orders above 500",
            "Show products cheaper than 100",
            "Show all orders with user names",
            "List users and their total order amount",
        ]

    def get_suggestions(self, last_sql: str = "", user_query: str = "") -> List[str]:
        """Return relevant suggestions based on last query and context.
        
        Args:
            last_sql: The SQL from the previous query
            user_query: The user's original query
            
        Returns:
            List of suggested follow-up queries
        """
        if not last_sql:
            return self.base_suggestions[:5]

        last_sql_upper = last_sql.upper()
        
        # Table-specific suggestions
        if "FROM USERS" in last_sql_upper:
            return self._get_user_suggestions(last_sql_upper, user_query)
        elif "FROM ORDERS" in last_sql_upper:
            return self._get_order_suggestions(last_sql_upper, user_query)
        elif "FROM PRODUCTS" in last_sql_upper:
            return self._get_product_suggestions(last_sql_upper, user_query)
        elif "JOIN" in last_sql_upper:
            return self._get_join_suggestions(last_sql_upper, user_query)
        
        # Default suggestions
        return self.base_suggestions[:4]

    def _get_user_suggestions(self, last_sql: str, user_query: str) -> List[str]:
        """Suggestions for user-related queries.
        
        Args:
            last_sql: Upper-case SQL from previous query
            user_query: The user's original query
            
        Returns:
            List of user-focused suggestions
        """
        suggestions: List[str] = []
        
        if "WHERE" not in last_sql:
            suggestions.extend([
                "Show users above age 30",
                "Show users below age 25", 
                "Show users with specific email domain",
            ])
        else:
            suggestions.extend([
                "Count users by age group",
                "Sort users by name",
                "Show user details with orders",
            ])
        
        if "JOIN" not in last_sql:
            suggestions.append("Show users and their orders")
            
        return suggestions[:5]

    def _get_order_suggestions(self, last_sql: str, user_query: str) -> List[str]:
        """Suggestions for order-related queries.
        
        Args:
            last_sql: Upper-case SQL from previous query
            user_query: The user's original query
            
        Returns:
            List of order-focused suggestions
        """
        suggestions: List[str] = []
        
        if "WHERE" not in last_sql:
            suggestions.extend([
                "Show orders above 500",
                "Show recent orders",
                "Show orders by amount",
            ])
        else:
            suggestions.extend([
                "Count orders by user",
                "Show order totals",
                "Show orders with user details",
            ])
            
        if "JOIN" not in last_sql:
            suggestions.append("Show orders with user names")
            
        return suggestions[:5]

    def _get_product_suggestions(self, last_sql: str, user_query: str) -> List[str]:
        """Suggestions for product-related queries.
        
        Args:
            last_sql: Upper-case SQL from previous query
            user_query: The user's original query
            
        Returns:
            List of product-focused suggestions
        """
        suggestions: List[str] = []
        
        if "WHERE" not in last_sql:
            suggestions.extend([
                "Show products under 100",
                "Show most expensive products",
                "Show products by price",
            ])
        else:
            suggestions.extend([
                "Count products by price range",
                "Show product details",
                "Show products in orders",
            ])
            
        return suggestions[:5]

    def _get_join_suggestions(self, last_sql: str, user_query: str) -> List[str]:
        """Suggestions for join-related queries.
        
        Args:
            last_sql: Upper-case SQL from previous query
            user_query: The user's original query
            
        Returns:
            List of join-focused suggestions
        """
        suggestions: List[str] = [
            "Show total sales per user",
            "Show order count per user", 
            "Show average order amount",
            "Show users with no orders",
            "Show products never ordered",
        ]
        
        # Filter based on what's already been shown
        if "SUM(" in last_sql:
            suggestions = [s for s in suggestions if "total" not in s.lower()]
        if "COUNT(" in last_sql:
            suggestions = [s for s in suggestions if "count" not in s.lower()]
        if "AVG(" in last_sql:
            suggestions = [s for s in suggestions if "average" not in s.lower()]
            
        return suggestions[:5]
