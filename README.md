# Text-to-SQL System

A comprehensive local Python application that converts natural language questions into SQL with advanced features including auto-correction, visualization, export, and conversational context.

## 🚀 Enhanced Features

### Core Functionality
- **Natural Language → SQL**: Convert questions to SQL queries
- **SQL Explanation**: Human-readable explanations of generated SQL
- **Auto Query Correction**: Retry failed queries with improved prompts
- **Query Execution**: Safe SQLite execution with validation
- **Conversational Context**: Multi-step queries with context awareness
- **Smart Suggestions**: AI-powered follow-up query recommendations

### User Interface
- **CLI Interface**: Command-line interface with enhanced features
- **Streamlit UI**: Modern web interface with interactive features
- **Data Visualization**: Automatic charts (bar/line) for query results
- **Export Functionality**: Download results as CSV or Excel

### Performance & UX
- **Execution Metrics**: Performance timing and attempt tracking
- **Pretty Formatting**: Enhanced table display
- **Loading Indicators**: Visual feedback during processing
- **Error Handling**: Clear error messages and retry mechanisms

### Architecture
- **Modular Design**: Clean separation of concerns
- **Type Safety**: Full type hints throughout
- **Logging**: Comprehensive logging system
- **Testing**: Unit tests for core functionality

## 📋 Requirements

- Python 3.8+
- SQLite
- Dependencies listed in `requirements.txt`

## 🛠️ Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up environment variables (optional):
   ```bash
   cp .env.template .env
   # Edit .env with your Groq API key (optional - system works without it)
   # Keep your API key secure and never commit it to version control
   ```

## 🎯 Usage

### CLI Interface
```bash
python main.py
```

Available commands:
- `help`: Show examples and commands
- `history`: View recent queries
- `clear`: Clear conversation context
- `exit`: Quit the program

### Streamlit Web Interface
```bash
streamlit run ui.py
```

Features:
- Interactive query input
- Real-time results display
- Data visualization toggle
- Export buttons (CSV/Excel)
- Smart query suggestions
- Conversation context

## 🏗️ Project Structure

```text
d:/Text-to-SQL2/
│
├── Core Modules
│   ├── main.py                 # CLI entry point
│   ├── ui.py                   # Streamlit web interface
│   ├── query_service.py        # Orchestration layer
│   ├── ai_query_generator.py   # SQL generation with Groq
│   ├── sql_validator.py        # Query validation
│   ├── query_executor.py       # Database execution
│   └── result_formatter.py     # Output formatting
│
├── Enhanced Features
│   ├── sql_explainer.py        # SQL → Natural language
│   ├── context_manager.py      # Conversational context
│   ├── query_suggester.py      # Smart suggestions
│   ├── visualization.py        # Data visualization
│   └── export_handler.py       # CSV/Excel export
│
├── Supporting Modules
│   ├── config.py               # Configuration
│   ├── history_manager.py      # Query history
│   ├── schema_loader.py        # Database schema
│   └── input_handler.py        # CLI input handling
│
├── Data & Testing
│   ├── database.db             # SQLite database
│   ├── test_database.db        # Test database
│   └── tests/                   # Unit tests
│
└── Configuration
    ├── requirements.txt         # Python dependencies
    ├── .env.example            # Environment template
    └── README.md               # This file
```

## 🎨 Examples

### Basic Queries
- "Show all users"
- "Show users above age 30"
- "List orders above 500"
- "Show products cheaper than 100"

### Advanced Queries
- "Show all orders with user names"
- "List users and their total order amount"
- "Show recent orders sorted by date"

### Conversational Queries
1. "Show all users"
2. "Only above 30"
3. "Sort by name"

## 🔧 Configuration

Edit `config.py` to customize:
- Database path
- Logging level
- Maximum history items
- Query limits (joins, length)

## 🧪 Testing

Run tests:
```bash
python -m pytest tests/ -v
```

## 📊 Database Schema

The system includes a sample database with three tables:

- **Users**: Id, Name, Age, Email
- **Orders**: OrderId, UserId, Amount, Date  
- **Products**: ProductId, Name, Price

## 🔒 Security

- **SELECT-only queries**: No INSERT/UPDATE/DELETE allowed
- **SQL injection protection**: Input validation and sanitization
- **Schema validation**: Queries checked against known schema
- **Local execution**: No external API calls for data processing

## 🚀 Performance

- **Query caching**: Schema and result caching
- **Execution timing**: Performance metrics
- **Retry mechanism**: Auto-correction for failed queries
- **Optimized formatting**: Efficient table display

## 📝 Development

The system follows best practices:
- **Type hints**: Full type annotation coverage
- **Docstrings**: Comprehensive documentation
- **Logging**: Structured logging throughout
- **Modular design**: Clean separation of concerns
- **Error handling**: Graceful error recovery

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.
├── sql_validator.py
├── query_executor.py
├── result_formatter.py
├── ui.py
├── tests/
│   └── test_queries.py
├── requirements.txt
└── README.md
```

## Architecture Diagram

```text
User Query
   |
   v
input_handler.py / ui.py
   |
   v
query_service.py
   |--> schema_loader.py
   |--> ai_query_generator.py
   |--> sql_validator.py
   |--> query_executor.py
   |--> result_formatter.py
   |--> history_manager.py
   |
   v
Structured Response + Display
```

## Setup

1. Install dependencies:

```powershell
py -m pip install -r requirements.txt
```

2. Optional: set Groq variables for model-backed generation.

```powershell
$env:GROQ_API_KEY="your_new_groq_key"
$env:TEXT_TO_SQL_USE_GROQ="true"
$env:GROQ_MODEL="llama-3.3-70b-versatile"
$env:TEXT_TO_SQL_LOG_LEVEL="INFO"
```

You can also copy `.env.example` into a local `.env` workflow if you prefer shell-managed environment variables.

## Run The CLI

```powershell
py main.py
```

## Run The Streamlit UI

```powershell
streamlit run ui.py
```

## Run Tests

```powershell
pytest
```

## Example Queries

- `Show all users`
- `Show all users above age 30`
- `List orders above 500`
- `Show recent orders`
- `Show products cheaper than 100`
- `Show all orders with user names`
- `List users and their total order amount`

## Module Overview

- `config.py`: central runtime configuration and logging setup
- `schema_loader.py`: database creation, sample data seeding, schema loading, and foreign-key discovery
- `ai_query_generator.py`: Groq prompting, few-shot examples, schema-aware generation, local fallback rules, and SQL post-processing
- `sql_validator.py`: query safety checks, table/column validation, and complexity limits
- `query_executor.py`: SQLite execution plus repeated-query caching
- `result_formatter.py`: table formatting using pandas markdown output
- `history_manager.py`: recent query history with timestamps
- `query_service.py`: end-to-end orchestration and structured response creation
- `main.py`: CLI entry point
- `ui.py`: Streamlit UI with sidebar history and example prompts

## Notes

- Only `SELECT` queries are allowed.
- Unsafe operations such as `DELETE`, `DROP`, `UPDATE`, `INSERT`, `ALTER`, `TRUNCATE`, `CREATE`, and `REPLACE` are blocked.
- If `GROQ_API_KEY` is set, the app tries Groq first and falls back to local rules if the API is unavailable or returns unusable SQL.
- The Streamlit UI includes a sidebar history panel and example-query dropdown.
- Add screenshots after launching the UI locally if you want visual documentation in this README.
