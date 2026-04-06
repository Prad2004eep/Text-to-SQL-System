"""CLI entry point for the local Text-to-SQL system."""

from __future__ import annotations

import logging
from typing import Optional

from ai_query_generator import AIQueryGenerator
from config import AppConfig
from context_manager import ContextManager
from history_manager import QueryHistoryManager
from input_handler import InputHandler
from query_executor import QueryExecutor
from query_service import QueryService
from result_formatter import ResultFormatter
from schema_loader import initialize_database, load_schema_metadata
from sql_validator import SQLValidator


def run_cli() -> None:
    """Run the interactive CLI application."""
    config = AppConfig()
    
    # Initialize database and schema
    initialize_database(str(config.database_path))
    schema_metadata = load_schema_metadata(str(config.database_path))
    schema = schema_metadata["tables"]
    
    # Initialize all components
    input_handler = InputHandler()
    history_manager = QueryHistoryManager(str(config.database_path), max_items=config.max_history_items)
    query_generator = AIQueryGenerator(schema=schema, foreign_keys=schema_metadata["foreign_keys"], config=config)
    validator = SQLValidator(schema, max_joins=config.max_joins, max_query_length=config.max_query_length)
    executor = QueryExecutor(str(config.database_path))
    formatter = ResultFormatter()
    service = QueryService(query_generator, validator, executor, formatter, history_manager)
    service.context_manager = ContextManager()

    print("Local Text-to-SQL CLI")
    print("Available tables: Users, Orders, Products")
    print("Commands: 'history' to view recent queries, 'search <term>' to search history, 'help' for examples, 'clear' to clear context, 'exit' to quit.")

    while True:
        try:
            user_query = input_handler.get_user_query()
            command = input_handler.get_command(user_query)
            
            # Handle exit command
            if command == "exit":
                print("Exiting.")
                break
                
            # Handle clear command
            if command == "clear":
                service.context_manager = ContextManager()
                print("Conversation context cleared.")
                continue
                
            # Handle help command
            if command == "help":
                print("\nExample queries:")
                print("- Show all users")
                print("- Show all users above age 30")
                print("- List orders above 500")
                print("- Show all orders with user names")
                print("- List users and their total order amount")
                print("- Show products cheaper than 100")
                print("\nConversational examples:")
                print("- 'Show all users' followed by 'only above 30'")
                print("- 'Show orders' followed by 'above 500'")
                print("\nCommands:")
                print("- history: Show recent queries")
                print("- search <term>: Search query history")
                print("- clear: Clear conversation context")
                print("- help: Show this help message")
                print("- exit: Quit the program")
                continue
                
            # Handle search command
            if user_query.lower().startswith("search "):
                search_term = user_query[7:].strip()
                if not search_term:
                    print("Please provide a search term. Usage: search <term>")
                else:
                    search_results = history_manager.search_history(search_term)
                    if not search_results:
                        print(f"No queries found matching '{search_term}'.")
                    else:
                        print(f"\nSearch Results for '{search_term}':")
                        for i, item in enumerate(search_results, 1):
                            print(f"{i}. [{item.timestamp}] {item.user_query}")
                            print(f"   SQL: {item.sql}")
                continue
                
            # Handle history command
            if command == "history":
                history = history_manager.get_recent_entries()
                if not history:
                    print("No previous queries yet.")
                else:
                    print("\nRecent Query History:")
                    for i, item in enumerate(history, 1):
                        print(f"{i}. [{item.timestamp}] {item.user_query}")
                        print(f"   SQL: {item.sql}")
                continue
                
            # Process as regular query
            response = service.process_query(user_query)
            if response["status"] == "error":
                print(f"\nError: {response['message']}")
                continue

            data = response["data"]
            print(f"\nGenerated SQL:\n{data['sql']}")
            
            # Show retry information if applicable
            if data.get("attempts", 1) > 1:
                print(f"✅ Query succeeded after {data['attempts']} attempts")
                
            # Show resolved query if different from original
            if data.get("resolved_query") and data["resolved_query"] != data["user_query"]:
                print(f"\nContext: '{data['user_query']}' → '{data['resolved_query']}'")
                
            print(f"\nExplanation:\n{data['explanation']}")
            print(f"Execution Time: {data['execution_time_seconds']:.4f} seconds")
            print(f"Rows returned: {data['row_count']}")
            print("Results:")
            print(data["formatted_results"])
            
        except KeyboardInterrupt:
            print("\n\n🛑 Interrupted by user. Exiting gracefully...")
            break
        except Exception as e:
            print(f"\n\n❌ Unexpected error: {e}")
            break


if __name__ == "__main__":
    try:
        run_cli()
    except KeyboardInterrupt:
        print("\n\n🛑 Interrupted by user. Exiting gracefully...")
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
