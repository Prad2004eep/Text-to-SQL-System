"""Streamlit UI for the local Text-to-SQL system."""

from __future__ import annotations

import streamlit as st

from ai_query_generator import AIQueryGenerator
from config import AppConfig, configure_logging
from export_handler import ExportHandler
from history_manager import QueryHistoryManager
from query_executor import QueryExecutor
from query_service import QueryService
from query_suggester import QuerySuggester
from result_formatter import ResultFormatter
from schema_loader import format_schema_for_prompt, initialize_database, load_schema_metadata
from sql_validator import SQLValidator
from visualization import VisualizationBuilder


def main() -> None:
    """Run the Streamlit UI."""
    st.set_page_config(page_title="Local Text-to-SQL", page_icon=":card_index_dividers:", layout="wide")

    config = AppConfig()
    configure_logging(config.log_level)
    initialize_database(str(config.database_path))
    schema_metadata = load_schema_metadata(str(config.database_path))
    schema = schema_metadata["tables"]

    query_generator = AIQueryGenerator(schema=schema, foreign_keys=schema_metadata["foreign_keys"], config=config)
    validator = SQLValidator(schema, max_joins=config.max_joins, max_query_length=config.max_query_length)
    executor = QueryExecutor(str(config.database_path))
    formatter = ResultFormatter()
    viz_builder = VisualizationBuilder()
    export_handler = ExportHandler()
    suggester = QuerySuggester()

    if "history_manager" not in st.session_state:
        st.session_state.history_manager = QueryHistoryManager(
            str(config.database_path),
            max_items=config.max_history_items,
        )
    
    # Initialize context manager in session state
    if "context_manager" not in st.session_state:
        from context_manager import ContextManager
        st.session_state.context_manager = ContextManager()

    service = QueryService(query_generator, validator, executor, formatter, st.session_state.history_manager)
    # Inject context manager into service
    service.context_manager = st.session_state.context_manager

    st.title("Text-to-SQL Local AI System")
    st.caption("Fully local natural language to SQLite query execution")

    example_queries = [
        "Show all users",
        "Show all users above age 30",
        "List orders above 500",
        "Show all orders with user names",
        "List users and their total order amount",
        "Show products cheaper than 100",
    ]

    with st.sidebar:
        st.header("History")
        for item in st.session_state.history_manager.get_recent_entries():
            st.caption(item.timestamp)
            st.write(item.user_query)
            st.code(item.sql, language="sql")

        st.divider()
        selected_example = st.selectbox("Example Queries", [""] + example_queries)

    with st.expander("Database Schema", expanded=False):
        st.code(format_schema_for_prompt(schema), language="sql")

    default_query = selected_example if selected_example else ""
    
    # Check for suggested query from previous interaction
    if "suggested_query" in st.session_state:
        default_query = st.session_state.suggested_query
        auto_execute = st.session_state.get("auto_execute", False)
        del st.session_state.suggested_query
        if "auto_execute" in st.session_state:
            del st.session_state.auto_execute
    else:
        default_query = selected_example if selected_example else ""
        auto_execute = False

    user_query = st.text_input(
        "Ask a question about the data",
        value=default_query,
        placeholder="Show all users above age 30",
    )

    if st.button("Run Query", type="primary") or auto_execute:
        with st.spinner("🔄 Generating and executing SQL..."):
            response = service.process_query(user_query)

        if response["status"] == "error":
            st.error(response["message"])
            return

        data = response["data"]
        
        # Show retry information if applicable
        if data.get("attempts", 1) > 1:
            st.info(f"✅ Query succeeded after {data['attempts']} attempts")
        else:
            st.success(response["message"])
            
        st.subheader("Generated SQL")
        st.code(data["sql"], language="sql")
        st.subheader("Explanation")
        st.info(data["explanation"])
        
        # Show resolved query if different from original
        if data.get("resolved_query") and data["resolved_query"] != data["user_query"]:
            st.caption(f"Original: '{data['user_query']}' → Resolved: '{data['resolved_query']}'")
        
        st.caption(f"Execution time: {data['execution_time_seconds']:.4f} seconds")

        st.subheader("Results")
        if data["results"].empty:
            st.info("Query executed successfully, but no rows matched.")
        else:
            # Enhanced dataframe display
            st.dataframe(
                data["results"], 
                use_container_width=True,
                hide_index=True,
                height=min(400, len(data["results"]) * 40 + 50)
            )
            
            # Export functionality
            col1, col2 = st.columns(2)
            with col1:
                csv_data = export_handler.to_csv_bytes(data["results"])
                st.download_button(
                    label="Download CSV",
                    data=csv_data,
                    file_name="query_results.csv",
                    mime="text/csv",
                )
            with col2:
                excel_data = export_handler.to_excel_bytes(data["results"])
                st.download_button(
                    label="Download Excel",
                    data=excel_data,
                    file_name="query_results.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            
            # Visualization section
            viz_result = viz_builder.build(data["results"])
            if viz_result:
                show_viz = st.checkbox("Show Visualization", value=True)
                if show_viz:
                    st.subheader("Data Visualization")
                    st.plotly_chart(viz_result.figure, use_container_width=True)
                    st.caption(f"Chart type: {viz_result.chart_type} | X-axis: {viz_result.x_column} | Y-axis: {viz_result.y_column}")

        with st.expander("Formatted Output", expanded=False):
            st.text(data["formatted_results"])

        # Smart suggestions section
        suggestions = suggester.get_suggestions(data["sql"], data["user_query"])
        if suggestions:
            st.subheader("Suggested Follow-up Queries")
            cols = st.columns(min(len(suggestions), 3))
            for i, suggestion in enumerate(suggestions[:6]):  # Show max 6 suggestions
                with cols[i % 3]:
                    if st.button(suggestion, key=f"suggestion_{i}"):
                        # Set the suggested query and mark for auto-execution
                        st.session_state.suggested_query = suggestion
                        st.session_state.auto_execute = True
                        st.rerun()


if __name__ == "__main__":
    main()
