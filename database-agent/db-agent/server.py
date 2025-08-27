import asyncio 
import json 
import logging 
import os 
import sqlite3

import mcp.server.stdio
from dotenv import load_dotenv

from google.adk.tools.function_tool import FunctionTool
from google.adk.tools.mcp_tool.conversion_utils import adk_to_mcp_tool_type

from mcp import types as mcp_types 
from mcp.server.lowlevel import NotificationOptions, Server
from mcp.server.models import InitializationOptions

load_dotenv()

LOG_FILE= os.path.join(os.path.dirname(__file__), "server.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
    handlers=[logging.FileHandler(LOG_FILE, mode="w"),]
)

DATABASE_PATH = os.path.join(os.path.dirname(__file__), "life_tracker.db")


# UTILITY FUNCTION
def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row 
    return conn 


# MCP TOOLS
def list_db_tables(dummy_param: str) -> dict:
    """Lists all tables in the SQLite database.

    Args:
        dummy_param (str): This parameter is not used by the function
                           but helps ensure schema generation. A non-empty string is expected.
    Returns:
        dict: A dictionary with keys 'success' (bool), 'message' (str),
              and 'tables' (list[str]) containing the table names if successful.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        logging.info(f"Successfully listed all tables in the database: {tables}")

        return {
            "success": True,
            "message": "Successfully listed all tables in the database.",
            "tables": tables
        }
    except sqlite3.Error as e:
        logging.error(f"Error listing tables: {e}")
        return {"success": False, "message": f"Error listing tables: {e}", "tables": []} 
    except Exception as e:
        logging.error(f"An unexpected error occurred while listing tables: {e}")
        return {"success": False, "message": f"An unexpected error occurred while listing tables: {e}", "tables": []}  
    finally:
        conn.close()


def get_table_schema(table_name: str) -> dict:
    """Gets the schema (column names and types) of a specific table."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info('{table_name}');")
        schema_info = cursor.fetchall()
        logging.info(f"Successfully retrieved schema for table '{table_name}': {schema_info}")
        if not schema_info:
            return {
                "success": False,
                "message": f"Table '{table_name}' not found in the database.",
                "schema": {}
            }
        
        schema = [{"name": row["name"], "type": row["type"]} for row in schema_info]
        logging.info(f"Successfully retrieved schema for table '{table_name}': {schema}")
        return {
            "table_name": table_name,
            "columns": schema,
        }
    except sqlite3.Error as e:
        logging.error(f"Error retrieving schema for table '{table_name}': {e}")
        return {
            "success": False,
            "message": f"Error retrieving schema for table '{table_name}': {e}",
            "schema": {}
        }
    except Exception as e:
        logging.error(f"An unexpected error occurred while retrieving schema for table '{table_name}': {e}")
        return {
            "success": False,
            "message": f"An unexpected error occurred while retrieving schema for table '{table_name}': {e}",
            "schema": {}
        }
    finally:
        conn.close()


def query_db_table(table_name: str, columns: str, conditions: str) -> list[dict]:
    """Queries a table with an optional condition.

    Args:
        table_name: The name of the table to query.
        columns: Comma-separated list of columns to retrieve (e.g., "id, name"). Defaults to "*".
        condition: Optional SQL WHERE clause condition (e.g., "id = 1" or "frequency = daily").
    Returns:
        A list of dictionaries, where each dictionary represents a row.
    """ 
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = f"SELECT {columns} FROM {table_name}"
        if conditions:
            query += f" WHERE {conditions}"
        query += ";"

        cursor.execute(query)
        rows = [dict(row) for row in cursor.fetchall()]
        logging.info(f"Successfully queried table '{table_name}' with {len(rows)} rows")
        return rows

    except sqlite3.Error as e:
        return [{
            "success": False,
            "message": f"Error querying table '{table_name}': {e}",
            "rows": []
        }]
    except Exception as e:
        return [{
            "success": False,
            "message": f"An unexpected error occurred while querying table '{table_name}': {e}",
            "rows": []
        }]
    finally:
        conn.close()


def insert_data_into_table(table_name: str, data: dict) -> dict:
    """Inserts a new row of data into the specified table.

    Args:
        table_name (str): The name of the table to insert data into.
        data (dict): A dictionary where keys are column names and values are the
                     corresponding values for the new row.

    Returns:
        dict: A dictionary with keys 'success' (bool) and 'message' (str).
              If successful, 'message' includes the ID of the newly inserted row.
    """
    if not data:
        return {"success": False, "message": "No data provided to insert."}
    
    conn = get_db_connection()
    cursor = conn.cursor()
    columns = ", ".join(data.keys())
    placeholders = ", ".join("?" * len(data))
    values = tuple(data.values())

    query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"

    try:
        cursor.execute(query, values)
        conn.commit()
        row_id = cursor.lastrowid
        return {
            "success": True,
            "message": f"Successfully inserted data into table '{table_name}', ROW_ID: {row_id}",
            "row_id": row_id,
        }
    except sqlite3.Error as e:
        conn.rollback()
        logging.error(f"Error inserting data into table '{table_name}': {e}")
        return {
            "success": False,
            "message": f"Error inserting data into table '{table_name}': {e}",
        }
    except Exception as e:
        logging.error(f"An unexpected error occurred while inserting data into table '{table_name}': {e}")
        return {
            "success": False,
            "message": f"An unexpected error occurred while inserting data into table '{table_name}': {e}",
        }
    finally:
        conn.close()


def delete_data_from_table(table_name: str, condition: str) -> dict:
    """Deletes rows from a table based on a given SQL WHERE clause condition.

    Args:
        table_name (str): The name of the table to delete data from.
        condition (str): The SQL WHERE clause condition to specify which rows to delete.
                         This condition MUST NOT be empty to prevent accidental mass deletion.

    Returns:
        dict: A dictionary with keys 'success' (bool) and 'message' (str).
              If successful, 'message' includes the count of deleted rows.
    """
    if not condition or not condition.strip():
        return {
            "success": False,
            "message": "No condition provided for deletion. Please provide a valid WHERE clause condition."
        }
    
    conn = get_db_connection()
    cursor = conn.cursor()

    query = f"DELETE FROM {table_name} WHERE {condition}"

    try:
        cursor.execute(query)
        rows_deleted = cursor.rowcount
        conn.commit()
        logging.info(f"Successfully deleted {rows_deleted} rows from table '{table_name}'")
        return {
            "success": True,
            "message": f"Successfully deleted {rows_deleted} rows from table '{table_name}'",
            "rows_deleted": rows_deleted
        }
    except sqlite3.Error as e:
        conn.rollback()
        logging.error(f"Error deleting data from table '{table_name}': {e}")
        return {
            "success": False,
            "message": f"Error deleting data from table '{table_name}': {e}",
            "rows_deleted": 0
        }
    except Exception as e:
        conn.rollback()
        logging.error(f"An unexpected error occurred while deleting data from table '{table_name}': {e}")
        return {
            "success": False,
            "message": f"An unexpected error occurred while deleting data from table '{table_name}': {e}",
            "rows_deleted": 0
        }
    finally:
        conn.close()


def update_data_in_table(table_name: str, data: dict, condition: str) -> dict:
    """Updates rows in a table based on a given SQL WHERE clause condition.

    Args:
        table_name (str): The name of the table to update data in.
        data (dict): A dictionary where keys are column names and values are the
                     corresponding new values for the update.
        condition (str): The SQL WHERE clause condition to specify which rows to update.
                         This condition MUST NOT be empty to prevent accidental mass updates.

    Returns:
        dict: A dictionary with keys 'success' (bool) and 'message' (str).
              If successful, 'message' includes the count of updated rows.
    """
    if not data:
        return {"success": False, "message": "No data provided to update."}
    
    if not condition or not condition.strip():
        return {
            "success": False,
            "message": "No condition provided for update. Please provide a valid WHERE clause condition."
        }
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Build the SET clause for the UPDATE statement
    set_clause = ", ".join([f"{column} = ?" for column in data.keys()])
    values = tuple(data.values())
    
    query = f"UPDATE {table_name} SET {set_clause} WHERE {condition}"

    try:
        cursor.execute(query, values)
        rows_updated = cursor.rowcount
        conn.commit()
        logging.info(f"Successfully updated {rows_updated} rows in table '{table_name}'")
        return {
            "success": True,
            "message": f"Successfully updated {rows_updated} rows in table '{table_name}'",
            "rows_updated": rows_updated
        }
    except sqlite3.Error as e:
        conn.rollback()
        logging.error(f"Error updating data in table '{table_name}': {e}")
        return {
            "success": False,
            "message": f"Error updating data in table '{table_name}': {e}",
            "rows_updated": 0
        }
    except Exception as e:
        conn.rollback()
        logging.error(f"An unexpected error occurred while updating data in table '{table_name}': {e}")
        return {
            "success": False,
            "message": f"An unexpected error occurred while updating data in table '{table_name}': {e}",
            "rows_updated": 0
        }
    finally:
        conn.close()


logging.info(
    "Creating MCP Server instance for SQLite Database..."
)
# MCP Server instance
app = Server("life-tracker-db-mcp-server")

# Wrap as ADK function tools
DB_TOOLS = {
    "list_db_tables": FunctionTool(func=list_db_tables),
    "get_table_schema": FunctionTool(func=get_table_schema),
    "query_db_table": FunctionTool(func=query_db_table),
    "insert_data_into_table": FunctionTool(func=insert_data_into_table),
    "delete_data_from_table": FunctionTool(func=delete_data_from_table),
    "update_data_in_table": FunctionTool(func=update_data_in_table),
}


@app.list_tools()
async def list_mcp_tools() -> list[mcp_types.Tool]:
    """MCP handler to list tools this server exposes."""
    logging.info("MCP Server: Received list_tools request")
    mcp_tools_list = []

    for tool_name, tool_instance in DB_TOOLS.items():
        if not tool_instance.name:
            tool_instance.name = tool_name

        mcp_tool_schema = adk_to_mcp_tool_type(tool_instance)
        logging.info(
            f"MCP Server: Exposing tool: {mcp_tool_schema.name} InputSchema: {mcp_tool_schema.inputSchema}"
        )
        mcp_tools_list.append(mcp_tool_schema)
    return mcp_tools_list


@app.call_tool()
async def call_mcp_tool(tool_name: str, arguments: dict) -> list[mcp_types.TextContent]:
    """MCP handler to execute a tool call requested by an MCP client."""
    logging.info(f"MCP Server: Received call_tool request for '{tool_name}' with arguments: {arguments}")

    if tool_name in DB_TOOLS:
        tool_instance = DB_TOOLS[tool_name]
        try:
            # Call the function directly since these are synchronous functions
            func = tool_instance.func
            tool_response = func(**arguments)
            logging.info(f"MCP Server: Tool '{tool_name}' executed. Response: {tool_response}")
            response_text = json.dumps(tool_response, indent=2)

            return [mcp_types.TextContent(type="text", text=response_text)]
        
        except Exception as e:
            logging.error(f"MCP Server: Error executing tool '{tool_name}': {e}", exc_info=True)
            error_payload = {
                "success": False,
                "message": f"Failed to execute tool '{tool_name}': {str(e)}",
            }
            error_text = json.dumps(error_payload, indent=2)
            return [mcp_types.TextContent(type="text", text=error_text)]
    else:
        logging.warning(
            f"MCP Server: Tool {tool_name} not found in this server"
        )
        error_payload = {
            "success": False,
            "message": f"Tool '{tool_name}' not implemented by this server.",
        }
        error_text = json.dumps(error_payload)
        return [mcp_types.TextContent(type="text", text=error_text)]


# SERVER RUNNER
async def run_mcp_server():
    """Runs the MCP server, listening for connections over standard input/output."""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        logging.info(
            "MCP Stdio Server: Starting handshake with client..."
        )
        await app.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name=app.name,
                server_version="0.1.0",
                capabilities=app.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )
        logging.info("MCP Stdio Server: Run loop finished or client disconnected.")


if __name__ == "__main__":
    logging.info(
        "Launching SQLite DB MCP Server via stdio..."
    )
    try:
        asyncio.run(run_mcp_server())
    except KeyboardInterrupt:
        logging.info(
            "\nMCP Server (stdio) stopped by user."
        )
    except Exception as e:
        logging.critical("MCP Server: Unexpected error occurred", exc_info=True)
    finally:
        logging.info("MCP Server (stdio) shutting down...")

    
    
         
