# AI Micro‑SaaS Agents

A collection of small, focused AI agents I’m building for micro‑SaaS use cases. Projects are scoped, practical, and designed to be easy to run and adapt.

## 🧩 Agents in this repo

- Database Agent (`database-agent`): AI that manages a personal SQLite life‑tracker (expenses, habits, workouts). Uses Google ADK + an MCP server for database tools. See the agent’s README for setup and running with `adk web`.
- Dev Research Agent (`dev-research-agent`): Streamlit app that researches and compares developer tools using LangGraph + Firecrawl. Includes robust rate‑limit handling. See README for `uv sync` and `run_app.py`.
- Gmail Assistant (`email-agent`): LangGraph‑based ambient agent that triages email, drafts replies, checks calendar, and schedules meetings using Gmail/Calendar APIs. Local dev via `langgraph dev` and ingestion script.
- Social Media Manager (`social-media-manager`): Content manager that maintains user profile, content calendar, and content guidelines with memory. Built with LangGraph + OpenAI. Run the CLI in `main.py`.

## 📁 Repository structure

```
AI Agents/
├── database-agent/
├── dev-research-agent/
├── email-agent/
├── social-media-manager/
├── pyproject.toml
├── README.md
└── uv.lock
```

Each agent has its own `README.md` (or docs) with prerequisites and commands. Follow those per‑agent instructions for environment setup and running.

## 🛠️ Tech used across agents

- LangGraph and LangChain for agent workflows and tools
- Google ADK for agent scaffolding (where applicable)
- Python (with `uv` in some projects)
- Firecrawl (research/scraping) and Google APIs (Gmail/Calendar) where needed
- OpenAI models for reasoning and extraction

## 🚀 Getting started

1) Pick an agent directory from above
2) Read its README for environment variables and commands
3) Run with the provided entry point (e.g., `adk web`, `langgraph dev`, `run_app.py`, or `python main.py`)

## 🤝 Contributing

Suggestions and improvements are welcome:

- Open issues for bugs or ideas
- Propose enhancements to existing agents or new micro‑SaaS agents

## 📄 Licensing

Licenses and third‑party terms vary by subproject. Please review each agent’s files and respect upstream dependencies.

---

Built for practical, composable agent workflows.