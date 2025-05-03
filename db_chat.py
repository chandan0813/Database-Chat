import streamlit as st
import google.generativeai as genai
import pandas as pd
import sqlite3
import sqlalchemy
import pyodbc
import json
import os
import re
from typing import Dict, List, Tuple, Optional

# App configuration
st.set_page_config(
    page_title="Database Chat",
    page_icon="💬",
    layout="wide"
)

# Apply custom CSS
st.markdown("""
<style>
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        display: flex;
        flex-direction: row;
    }
    .chat-message.user {
        background-color: #02153b;
    }
    .chat-message.assistant {
        background-color: #02153b;
    }
    .chat-message .avatar {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        object-fit: cover;
        margin-right: 1rem;
    }
    .chat-message .message {
        flex-grow: 1;
    }
    .sql-code {
        padding: 10px;
        border-radius: 5px;
        background-color: #02153b;
        font-family: monospace;
        margin: 10px 0;
        border-left: 3px solid #4CAF50;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

if "connection_string" not in st.session_state:
    st.session_state.connection_string = ""

if "db_connected" not in st.session_state:
    st.session_state.db_connected = False

if "engine" not in st.session_state:
    st.session_state.engine = None

if "gemini_key" not in st.session_state:
    st.session_state.gemini_key = ""

if "gemini_configured" not in st.session_state:
    st.session_state.gemini_configured = False

if "schema_info" not in st.session_state:
    st.session_state.schema_info = ""

if "db_type" not in st.session_state:
    st.session_state.db_type = "mssql"  # Default to SQL Server

if "table_count" not in st.session_state:
    st.session_state.table_count = 0

if "table_names" not in st.session_state:
    st.session_state.table_names = []

# Utility functions
def init_gemini_api(api_key: str) -> bool:
    """Initialize the Gemini API with the provided key."""
    try:
        genai.configure(api_key=api_key)
        return True
    except Exception as e:
        st.error(f"Failed to configure Gemini API: {str(e)}")
        return False

def create_db_connection(connection_string: str) -> Tuple[bool, Optional[sqlalchemy.engine.base.Engine]]:
    """Create a database connection using the provided connection string."""
    try:
        engine = sqlalchemy.create_engine(connection_string)
        # Test connection
        with engine.connect() as conn:
            pass
        return True, engine
    except Exception as e:
        st.error(f"Failed to connect to database: {str(e)}")
        return False, None

def get_database_schema(engine: sqlalchemy.engine.base.Engine, db_type: str) -> str:
    """Fetch database schema information based on database type."""
    schema_info = []
    table_names = []
    
    try:
        with engine.connect() as conn:
            if db_type == "sqlite":
                # SQLite schema query
                tables_query = """
                SELECT name FROM sqlite_master
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
                """
                tables = pd.read_sql(tables_query, conn)
                
                # Store table count and names in session state
                st.session_state.table_count = len(tables)
                st.session_state.table_names = tables['name'].tolist()
                
                for table_name in tables['name']:
                    table_names.append(table_name)
                    # Get table schema
                    table_schema_query = f"PRAGMA table_info({table_name})"
                    table_schema = pd.read_sql(table_schema_query, conn)
                    
                    columns = []
                    for _, row in table_schema.iterrows():
                        column_name = row['name']
                        column_type = row['type']
                        columns.append(f"{column_name} ({column_type})")
                    
                    schema_info.append(f"Table: {table_name}")
                    schema_info.append("Columns: " + ", ".join(columns))
                    schema_info.append("")
                    
                    # Sample data (top 3 rows)
                    try:
                        sample_data_query = f"SELECT * FROM {table_name} LIMIT 3"
                        sample_data = pd.read_sql(sample_data_query, conn)
                        schema_info.append(f"Sample data: {sample_data.to_dict('records')}")
                        schema_info.append("")
                    except Exception as e:
                        schema_info.append(f"Could not fetch sample data for this table: {str(e)}")
                        schema_info.append("")
            
            elif db_type == "mssql":
                # SQL Server schema query
                tables_query = """
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_type = 'BASE TABLE'
                """
                tables = pd.read_sql(tables_query, conn)
                
                # Store table count and names in session state
                st.session_state.table_count = len(tables)
                st.session_state.table_names = tables['table_name'].tolist()
                
                for table_name in tables['table_name']:
                    table_names.append(table_name)
                    # Get table schema
                    table_schema_query = f"""
                    SELECT column_name, data_type, character_maximum_length
                    FROM information_schema.columns
                    WHERE table_name = '{table_name}'
                    """
                    table_schema = pd.read_sql(table_schema_query, conn)
                    
                    columns = []
                    for _, row in table_schema.iterrows():
                        column_name = row['column_name']
                        column_type = row['data_type']
                        if pd.notna(row['character_maximum_length']):
                            column_type += f"({row['character_maximum_length']})"
                        columns.append(f"{column_name} ({column_type})")
                    
                    schema_info.append(f"Table: {table_name}")
                    schema_info.append("Columns: " + ", ".join(columns))
                    schema_info.append("")
                    
                    # Sample data (top 3 rows)
                    try:
                        sample_data_query = f"SELECT TOP 3 * FROM {table_name}"
                        sample_data = pd.read_sql(sample_data_query, conn)
                        schema_info.append(f"Sample data: {sample_data.to_dict('records')}")
                        schema_info.append("")
                    except Exception as e:
                        schema_info.append(f"Could not fetch sample data for this table: {str(e)}")
                        schema_info.append("")
            
            else:
                schema_info.append(f"Schema fetching not implemented for database type: {db_type}")
    
    except Exception as e:
        schema_info.append(f"Error fetching schema: {str(e)}")
    
    # Add summary at the beginning
    summary = [
        f"Database Summary:",
        f"Total Tables: {st.session_state.table_count}",
        f"Table Names: {', '.join(st.session_state.table_names)}",
        "",
        "Detailed Schema:",
        ""
    ]
    
    return "\n".join(summary + schema_info)

def execute_sql_query(engine: sqlalchemy.engine.base.Engine, query: str, db_type: str) -> Tuple[pd.DataFrame, Optional[str]]:
    """Execute SQL query and return results as DataFrame."""
    try:
        # Adapt query syntax for different database types
        if db_type == "mssql":
            # Check if the query includes LIMIT and replace with TOP for SQL Server
            if re.search(r'\bLIMIT\s+\d+\b', query, re.IGNORECASE):
                # Extract the LIMIT value
                limit_match = re.search(r'\bLIMIT\s+(\d+)\b', query, re.IGNORECASE)
                if limit_match:
                    limit_value = limit_match.group(1)
                    # Replace LIMIT with TOP
                    query = re.sub(r'\bSELECT\b', f'SELECT TOP {limit_value}', query, flags=re.IGNORECASE)
                    # Remove the LIMIT clause
                    query = re.sub(r'\bLIMIT\s+\d+\b', '', query, flags=re.IGNORECASE)
        
        with engine.connect() as conn:
            df = pd.read_sql(query, conn)
            return df, None
    except Exception as e:
        return pd.DataFrame(), str(e)

def query_gemini(prompt: str, schema_info: str = None) -> Dict:
    """Query Gemini API with a prompt and optional schema information."""  
    try:
        # Build content for the model
        content = []
        
        # System prompt
        system_prompt = """You are a helpful AI assistant that translates natural language questions into SQL queries and interprets query results.
        Your task is to:
        1. Understand the user's natural language question about their database
        2. Generate a correct SQL query based on the database schema provided
        3. When results are provided, interpret them to answer the original question in natural language
        
        If the user asks about the number of tables or wants to see table names, directly use the summary information at the beginning of the schema without generating a SQL query.
        
        If you need schema information, respond with: {"request_schema": true, "message": "I need the database schema to answer this question."}
        
        If you're ready to generate a SQL query, respond with: {"sql_query": "YOUR SQL QUERY HERE", "explanation": "Brief explanation of what the query does"}
        
        If you can answer directly from the schema summary, respond with: {"direct_answer": "Your answer here", "explanation": "How you got this information from the schema"}
        
        If you're interpreting results, respond with: {"interpretation": "Your natural language interpretation of the results", "details": "Additional details or insights from the data"}
        
        Always ensure your SQL queries are safe and properly formatted for the database being used. Use only the schema information provided.
        """
        
        # Add system message
        content = [{"role": "user", "parts": [{"text": system_prompt}]}]
        
        # Add user question
        content.append({"role": "user", "parts": [{"text": prompt}]})
        
        # Add schema info if provided
        if schema_info:
            content.append({"role": "user", "parts": [{"text": f"Here is the database schema information:\n{schema_info}"}]})
        
        # Initialize the model
        model = genai.GenerativeModel("gemini-1.5-flash")
        
        # Generate content
        response = model.generate_content(content)
        response_text = response.text.strip()
        
        # Try to parse as JSON
        try:
            # Clean up the response in case it has markdown code blocks
            if response_text.startswith("```json") and response_text.endswith("```"):
                response_text = response_text[7:-3].strip()
            elif response_text.startswith("{") and response_text.endswith("}"):
                # Already looks like JSON
                pass
            else:
                # Try to extract JSON from text
                json_match = re.search(r'{.*}', response_text, re.DOTALL)
                if json_match:
                    response_text = json_match.group(0)
            
            return json.loads(response_text)
        except json.JSONDecodeError:
            # If not valid JSON, return as regular message
            return {"message": response_text}
            
    except Exception as e:
        return {"message": f"Error calling Gemini API: {str(e)}"}

def process_results(question: str, query: str, results: pd.DataFrame) -> str:
    """Process query results and get interpretation from Gemini."""
    # Convert results to a readable format
    if results.empty:
        results_str = "The query returned no results."
    else:
        results_str = results.to_string()
    
    # Ask Gemini to interpret the results
    interpretation_prompt = f"""
    Original question: {question}
    
    SQL query: {query}
    
    Query results:
    {results_str}
    
    Please interpret these results to answer the original question in natural language.
    """
    
    interpretation_response = query_gemini(interpretation_prompt)
    
    if "interpretation" in interpretation_response:
        return interpretation_response["interpretation"]
    elif "direct_answer" in interpretation_response:
        return interpretation_response["direct_answer"]
    else:
        # Fallback if structured response not received
        return interpretation_response.get("message", f"Results: {results_str}")

def handle_table_count_question(question: str) -> bool:
    """Check if the question is about table count or names and handle it directly."""
    question_lower = question.lower()
    table_count_patterns = [
        "how many tables", 
        "number of tables", 
        "table count",
        "count of tables",
        "list of tables",
        "what tables",
        "which tables",
        "table names"
    ]
    
    return any(pattern in question_lower for pattern in table_count_patterns)

def display_chat_message(role: str, content: str, sql: str = None):
    """Display a chat message with appropriate styling."""
    avatar = "👤" if role == "user" else "🤖"
    bg_color = "user" if role == "user" else "assistant"
    
    with st.container():
        st.markdown(f"""
        <div class="chat-message {bg_color}">
            <div class="avatar">{avatar}</div>
            <div class="message">{content}</div>
        </div>
        """, unsafe_allow_html=True)
        
        if sql:
            st.markdown(f"""
            <div class="sql-code">
                <strong>SQL Query:</strong><br>
                {sql}
            </div>
            """, unsafe_allow_html=True)

# Main app UI
st.title("Database Chat 💬")
st.subheader("Chat with your database using natural language")

# Sidebar for configuration
with st.sidebar:
    st.header("Configuration")
    
    # Gemini API Key input
    gemini_key = st.text_input("Gemini API Key", 
                               value=st.session_state.gemini_key,
                               type="password")
    
    if gemini_key and gemini_key != st.session_state.gemini_key:
        st.session_state.gemini_key = gemini_key
        st.session_state.gemini_configured = init_gemini_api(gemini_key)
        if st.session_state.gemini_configured:
            st.success("✅ Gemini API configured successfully!")
    
    # Database type selection
    st.subheader("Database Configuration")
    db_type = st.selectbox(
        "Database Type",
        options=["mssql", "sqlite"],
        index=0 if st.session_state.db_type == "mssql" else 1
    )
    
    if db_type != st.session_state.db_type:
        st.session_state.db_type = db_type
    
    # Connection string help text
    if db_type == "mssql":
        st.info("""
        SQL Server connection string format:
        ```
        mssql+pyodbc://username:password@server_name/database_name?driver=ODBC+Driver+17+for+SQL+Server
        ```
        Or with Windows Authentication:
        ```
        mssql+pyodbc://server_name/database_name?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes
        ```
        """)
    else:
        st.info("""
        SQLite connection string format:
        ```
        sqlite:///path/to/your/database.db
        ```
        """)
    
    # Database connection string
    connection_string = st.text_input(
        "Connection String", 
        value=st.session_state.connection_string,
        placeholder="Enter database connection string"
    )
    
    if st.button("Connect to Database") and connection_string:
        st.session_state.connection_string = connection_string
        st.session_state.db_connected, st.session_state.engine = create_db_connection(connection_string)
        
        if st.session_state.db_connected:
            st.success("✅ Connected to database successfully!")
            st.session_state.schema_info = get_database_schema(st.session_state.engine, st.session_state.db_type)
        else:
            st.error("❌ Failed to connect to database")
    
    if st.session_state.db_connected:
        st.info("Connected to database ✓")
        
        # Display table count and names directly in sidebar
        st.success(f"Total Tables: {st.session_state.table_count}")
        with st.expander("Table Names"):
            for table in st.session_state.table_names:
                st.write(f"- {table}")
        
        if st.button("View Schema"):
            with st.expander("Database Schema", expanded=True):
                st.text(st.session_state.schema_info)
    
    st.divider()
    st.caption("Database Chat v1.0")
    st.caption("A natural language database client")

# Display chat history
for message in st.session_state.messages:
    display_chat_message(
        role=message["role"],
        content=message["content"],
        sql=message.get("sql", None)
    )

# Input for user question
user_input = st.chat_input("Ask a question about your database...", 
                          disabled=not (st.session_state.db_connected and st.session_state.gemini_configured))

# Process user input
if user_input:
    # Add user message to chat
    st.session_state.messages.append({"role": "user", "content": user_input})
    display_chat_message("user", user_input)
    
    # Check if both API and DB are configured
    if not st.session_state.gemini_configured:
        st.error("Please configure Gemini API first")
    elif not st.session_state.db_connected:
        st.error("Please connect to a database first")
    else:
        with st.spinner("Thinking..."):
            # Check if it's a question about table count or names
            if handle_table_count_question(user_input):
                # Handle directly without querying Gemini
                table_names_str = ", ".join(st.session_state.table_names)
                response = f"There are {st.session_state.table_count} tables in the database: {table_names_str}"
                
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": response
                })
                display_chat_message("assistant", response)
            else:
                # First, ask Gemini to process the question
                gemini_response = query_gemini(user_input)
                
                # Check if Gemini needs schema information
                if gemini_response.get("request_schema", False):
                    # Provide schema info and ask again
                    schema_message = gemini_response.get("message", "Requesting database schema...")
                    st.info(schema_message)
                    
                    # Send the question with schema info
                    gemini_response = query_gemini(user_input, st.session_state.schema_info)
                
                # Check if we can answer directly from schema
                if "direct_answer" in gemini_response:
                    direct_answer = gemini_response["direct_answer"]
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": direct_answer
                    })
                    display_chat_message("assistant", direct_answer)
                
                # Check if we got a SQL query
                elif "sql_query" in gemini_response:
                    sql_query = gemini_response["sql_query"]
                    explanation = gemini_response.get("explanation", "")
                    
                    # Execute the SQL query
                    with st.spinner("Executing SQL query..."):
                        results, error = execute_sql_query(st.session_state.engine, sql_query, st.session_state.db_type)
                    
                    if error:
                        # If there's an error, send it back to Gemini
                        error_prompt = f"The SQL query failed with error: {error}. Please correct the query based on the schema:\n{st.session_state.schema_info}"
                        gemini_response = query_gemini(error_prompt)
                        
                        if "sql_query" in gemini_response:
                            # Try the corrected query
                            sql_query = gemini_response["sql_query"]
                            results, error = execute_sql_query(st.session_state.engine, sql_query, st.session_state.db_type)
                            
                            if error:
                                # If still error, report to user
                                assistant_response = f"I couldn't execute the query due to an error: {error}"
                                st.session_state.messages.append({
                                    "role": "assistant", 
                                    "content": assistant_response,
                                    "sql": sql_query
                                })
                                display_chat_message("assistant", assistant_response, sql_query)
                            else:
                                # Process successful results
                                result_interpretation = process_results(user_input, sql_query, results)
                                st.session_state.messages.append({
                                    "role": "assistant", 
                                    "content": result_interpretation,
                                    "sql": sql_query
                                })
                                display_chat_message("assistant", result_interpretation, sql_query)
                        else:
                            # Unable to correct query
                            assistant_response = f"I couldn't generate a working SQL query for your question. The error was: {error}"
                            st.session_state.messages.append({
                                "role": "assistant", 
                                "content": assistant_response
                            })
                            display_chat_message("assistant", assistant_response)
                    else:
                        # Process successful results
                        result_interpretation = process_results(user_input, sql_query, results)
                        st.session_state.messages.append({
                            "role": "assistant", 
                            "content": result_interpretation,
                            "sql": sql_query
                        })
                        display_chat_message("assistant", result_interpretation, sql_query)
                else:
                    # Handle general message
                    assistant_response = gemini_response.get("message", "I couldn't understand how to query the database for that question.")
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": assistant_response
                    })
                    display_chat_message("assistant", assistant_response)

# Display data preview if available
if st.session_state.db_connected and len(st.session_state.messages) > 0:
    last_message = st.session_state.messages[-1]
    if last_message["role"] == "assistant" and "sql" in last_message:
        with st.expander("View Raw Data"):
            with st.session_state.engine.connect() as conn:
                try:
                    df = pd.read_sql(last_message["sql"], conn)
                    st.dataframe(df)
                    
                    if not df.empty:
                        if st.button("Show Data Visualization Options"):
                            cols = df.columns.tolist()
                            
                            # Simple visualization options based on data types
                            numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
                            if len(numeric_cols) >= 1:
                                st.subheader("Quick Charts")
                                
                                # Bar chart for one numeric column
                                if len(df) < 30 and len(numeric_cols) >= 1:  # Reasonable number of rows
                                    selected_col = st.selectbox("Select column to visualize", numeric_cols)
                                    st.bar_chart(df.set_index(df.columns[0])[selected_col] if len(df.columns) > 1 else df[selected_col])
                except Exception as e:
                    st.error(f"Error displaying data: {str(e)}")
