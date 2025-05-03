# Database Chat 💬

A Streamlit-based natural language interface to chat with your database. This app allows you to connect to SQL Server (MSSQL) or SQLite databases, ask questions in plain English, and get SQL queries generated and executed automatically using Google's Gemini API. The results are interpreted and displayed in a conversational chat format.

---

## 📸 Preview

![Database Chat - Google Chrome 03-05-2025 20_14_18](https://github.com/user-attachments/assets/a6752b50-ac00-483a-a8c4-39b17faf03ce)

---
## Features

- Connect to MSSQL or SQLite databases using connection strings.
- Use natural language queries to interact with your database.
- Automatic translation of natural language questions into SQL queries via Gemini API.
- Schema introspection to provide context-aware query generation.
- Display SQL queries alongside natural language answers.
- View raw query results and simple data visualizations.
- Chat history with user and assistant messages.
- Custom styled chat interface with avatars and SQL code blocks.

---

## Installation

1. Clone this repository or download the source code.

2. Install Python 3.8+ and create a virtual environment (recommended):

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install required dependencies:

```bash
pip install streamlit google-generativeai pandas sqlalchemy pyodbc
```

> Note: Additional drivers may be required for database connections, such as ODBC Driver 17 for SQL Server.

---

## Configuration

### Gemini API Key

You need a valid Gemini API key to use the natural language to SQL translation features. Obtain your API key from Google Cloud or the Gemini API provider.

### Database Connection

The app supports two database types:

- **MSSQL (SQL Server)**
- **SQLite**

You must provide a valid connection string for your database.

#### MSSQL Connection String Examples

- Using SQL Server Authentication:

```
mssql+pyodbc://username:password@server_name/database_name?driver=ODBC+Driver+17+for+SQL+Server
```

- Using Windows Authentication:

```
mssql+pyodbc://server_name/database_name?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes
```

#### SQLite Connection String Example

```
sqlite:///path/to/your/database.db
```

---

## Usage

1. Run the Streamlit app:

```bash
streamlit run db_chat.py
```

2. In the sidebar:

- Enter your Gemini API key.
- Select your database type (MSSQL or SQLite).
- Enter your database connection string.
- Click **Connect to Database**.

3. Once connected, you can:

- See the total number of tables and their names.
- View the database schema.
- Ask natural language questions about your database in the chat input.
- View generated SQL queries and their results.
- Explore raw data and simple visualizations.

---

## How It Works

- The app connects to your database using SQLAlchemy.
- It fetches schema information (tables, columns, sample data).
- When you ask a question, it sends the prompt to the Gemini API.
- Gemini generates a SQL query or direct answer based on the schema.
- The app executes the SQL query and fetches results.
- Results are sent back to Gemini for interpretation.
- The chat interface displays the conversation, SQL queries, and results.

---

## Supported Databases

- **SQLite**: Uses SQLite system tables and PRAGMA commands to fetch schema.
- **MSSQL (SQL Server)**: Uses `information_schema` views to fetch schema.

---

## Troubleshooting

- Ensure your database connection string is correct and accessible.
- Make sure the required ODBC drivers are installed for MSSQL.
- Verify your Gemini API key is valid and has necessary permissions.
- If SQL queries fail, the app attempts to correct them via Gemini.
- Check Streamlit logs for detailed error messages.

---

## License

This project is provided as-is under the MIT License.

---

## Version

v1.0

---

## Acknowledgments

- Built with [Streamlit](https://streamlit.io/)
- Uses Google's [Gemini API](https://developers.generativeai.google/)
- Powered by [SQLAlchemy](https://www.sqlalchemy.org/) and [Pandas](https://pandas.pydata.org/)

---

Enjoy chatting with your database! 💬
