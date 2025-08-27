# AI Database Agent

This project implements an AI database agent using the Google ADK. The agent can interact with a SQLite database to manage and analyze personal life tracking data, including expenses, habits, and workouts.

## Features

- **Database Interaction**: The agent can perform CRUD (Create, Read, Update, Delete) operations on the database.
- **Natural Language Interface**: Users can interact with the agent using natural language queries.
- **Data Analysis**: The agent can provide insights and summaries from the user's data.

## Project Structure

The project is organized as follows:

```
.
├── db-agent
│   ├── __init__.py
│   ├── .env
│   ├── .gitignore
│   ├── agent.py
│   ├── create-db.py
│   ├── life_tracker.db
│   ├── prompt.py
│   ├── server.log
│   └── server.py
├── .gitignore
├── main.py
├── .python-version
├── pyproject.toml
├── README.md
└── uv.lock
```

- **`db-agent/`**: This directory contains the core logic for the AI agent.
  - `agent.py`: Defines the AI agent using the Google ADK.
  - `server.py`: Implements the MCP server that exposes the database tools to the agent.
  - `create-db.py`: A script to create and populate the SQLite database with a predefined schema and dummy data.
  - `life_tracker.db`: The SQLite database file.
  - `prompt.py`: Contains the system prompt that instructs the agent on its role and capabilities.
- **`main.py`**: The entry point for running the agent.
- **`pyproject.toml`**: The project's dependencies.

## Getting Started

### Prerequisites

- Python 3.8 or higher
- `uv` package installer

### Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/your-username/database-agent.git
   cd database-agent
   ```

2. **Create a virtual environment and install dependencies:**

   ```bash
   uv venv
   source .venv/bin/activate
   uv pip install -r requirements.txt
   ```

3. **Install additional packages:**

   ```bash
   pip install google-adk mcp[cli]
   ```

4. **Create the database:**

   ```bash
   python db-agent/create-db.py
   ```

### Running the Agent

To run the agent and interact with it in the browser, navigate to the root directory of the project and run the following command:

```bash
adk web
```

This will start a web server, and you can open the provided URL in your browser to interact with the agent.
