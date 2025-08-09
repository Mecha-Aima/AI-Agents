## Gmail Assistant (Ambient Agents)

An email-focused agent built as a learning exercise from LangChain’s Ambient Agents course. This agent uses LangGraph to orchestrate tools for Gmail and Google Calendar, and can be deployed locally with the LangGraph CLI.

### What it does
- triage incoming emails and route to actions
- draft and send replies
- check calendar availability for dates
- schedule meetings on Google Calendar
- mark messages as read once workflows complete

### Tech
- LangGraph for graph orchestration and local deployment
- LangChain for tool integration and LLM bindings
- Google APIs (Gmail, Calendar)


## Project Structure

```
email-agent/
  langgraph.json                 # Local deployment config and graph entry points
  pyproject.toml                 # Project metadata and dependencies
  src/
    gmail_assistant/
      graph.py                   # Main graph definition (exported as `gmail_assistant`)
      cron.py                    # Additional graph entry (mapped as `cron`)
      prompts.py                 # System/user prompts used by the agent
      schemas.py                 # Pydantic schemas for graph state and inputs
      utils.py                   # Helpers for parsing/formatting Gmail messages
      tools/
        gmail_tools.py           # Gmail + Calendar tools (fetch, send, schedule, etc.)
        setup_gmail.py           # OAuth flow to create `.secrets/token.json`
        run_ingest.py            # Pull emails and send to the local LangGraph server
        setup_cron.py            # Optional cron/script setup
        .secrets/                # Place `secrets.json` and generated `token.json` here
```

Entry points are declared in `langgraph.json`:

```json
{
  "graphs": {
    "gmail_assistant": "./src/gmail_assistant/graph.py:gmail_assistant",
    "cron": "./src/gmail_assistant/cron.py:graph"
  },
  "python_version": "3.11",
  "env": ".env",
  "dependencies": ["."]
}
```


## Setup

### Prereqs
- Python 3.11+ (the project targets 3.11; a 3.13 local setup also works)
- A Google Cloud project with Gmail and Calendar APIs enabled
- An OpenAI API key for the LLM

### Install

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -U pip
pip install -e .

# Optional: explicitly install the CLI if needed
# pip install -U langgraph-cli
```

Create a `.env` file in the project root with at least:

```bash
OPENAI_API_KEY=your_openai_api_key
```


## Graph
The `src/gmail_assistant/graph.py` graph is configured to use Gmail tools.

You simply need to run the setup below to obtain the credentials needed to run the graph with your own email.

### Setup Credentials

#### 1) Set up Google Cloud Project and Enable Required APIs

Enable Gmail and Calendar APIs:
1. Go to the Google APIs Library and enable the Gmail API:
   https://developers.google.com/workspace/gmail/api/quickstart/python#enable_the_api
2. Go to the Google APIs Library and enable the Google Calendar API:
   https://developers.google.com/workspace/calendar/api/quickstart/python#enable_the_api

Create OAuth Credentials:
1. Authorize credentials for a desktop application:
   https://developers.google.com/workspace/gmail/api/quickstart/python#authorize_credentials_for_a_desktop_application
2. Go to Credentials → Create Credentials → OAuth Client ID
3. Set Application Type to "Desktop app"
4. Click "Create"
5. Save the downloaded JSON file (you'll need this in the next step)

#### 2) Set Up Authentication Files

Move your downloaded client secret JSON file to the `.secrets` directory:

```bash
# Create a secrets directory
mkdir -p src/gmail_assistant/tools/.secrets

# Move your downloaded client secret to the secrets directory
mv /path/to/downloaded/client_secret.json src/gmail_assistant/tools/.secrets/secrets.json
```

Run the Gmail setup script to perform the OAuth flow and create `token.json`:

```bash
python src/gmail_assistant/tools/setup_gmail.py
```

Notes:
- A browser window will open for you to authenticate with your Google account.
- This creates `src/gmail_assistant/tools/.secrets/token.json` used for Gmail/Calendar access.


## Use With A Local Deployment

### 1) Run the LangGraph server locally

```bash
langgraph dev
```

### 2) Run the Gmail ingestion script

In another terminal, run:

```bash
python src/gmail_assistant/tools/run_ingest.py \
  --email youremail@example.com \
  --minutes-since 1000 \
  --graph-name gmail_assistant
```

What this does:
- Uses the local deployment URL (`http://127.0.0.1:2024`) by default.
- Fetches emails from the past N minutes and forwards each to the `gmail_assistant` graph via the LangGraph SDK.

Tips:
- Add `--early` to process just one email for testing.
- Add `--include-read` if you want to process read emails as well.


## Agent Inbox (Optional)

After ingestion, you can access interrupted threads in Agent Inbox:

- Deployment URL: `http://127.0.0.1:2024`
- Assistant/Graph ID: `gmail_assistant`
- Name: `Graph Name`
- App URL: https://dev.agentinbox.ai/


## Notes on Tools

- `fetch_emails_tool`, `send_email_tool`, `check_calendar_tool`, `schedule_meeting_tool` are defined in `src/gmail_assistant/tools/gmail_tools.py`.
- Meeting scheduling adds attendees to the event; to also send email invites, the Calendar insert should be called with `sendUpdates="all"` (not as part of the event body).
- `run_ingest.py` includes detailed debug logs to help trace LangGraph run creation and Gmail queries.


## Troubleshooting

- 422 Unprocessable Content from the LangGraph server typically means:
  - The `--graph-name` was missing or incorrect.
  - The input payload shape doesn’t match the graph’s expected schema.
  - Use the debug logs printed by `run_ingest.py` to see the exact payload.

- Calendar timezone errors (naive vs aware datetimes) have been addressed by making working hours UTC-aware and normalizing event times.


## Learn More

- This project is based on the LangChain Ambient Agents course material and adapts patterns from the “agents-from-scratch” examples.
- Original Gmail tool reference and README: [langchain-ai/agents-from-scratch – email tools](https://github.com/langchain-ai/agents-from-scratch/tree/main/src/email_assistant/tools/gmail)


