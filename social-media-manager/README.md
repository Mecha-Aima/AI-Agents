# Social Media Manager Agent

An AI-powered content management assistant built with LangGraph that helps users plan, organize, and track social media content across multiple platforms. The agent maintains persistent memory of user preferences, content calendars, and creation guidelines.

## 🚀 Features

- **Smart Content Planning**: AI-powered brainstorming and content organization
- **Persistent Memory**: Remembers user profiles, content preferences, and guidelines across sessions
- **Content Calendar Management**: Track content ideas, deadlines, and publishing status
- **Adaptive Guidelines**: Learns from user interactions to improve content suggestions
- **Multi-Platform Support**: Organize content for different social media platforms

## 🏗️ Architecture

The agent uses a **LangGraph workflow** with three main memory types:

- **User Profile**: Personal preferences, target audience, and platform choices
- **Content Calendar**: Planned content with titles, deadlines, and status tracking
- **Content Guidelines**: Evolving best practices learned from user feedback

### Workflow Components

```
START → content_manager → route_message → [update_profile | update_content_calendar | update_guidelines] → content_manager → END
```

- **Content Manager**: Main reasoning node that processes user input and decides what to update
- **Memory Updates**: Specialized nodes for updating different memory types
- **Persistent Storage**: In-memory store with checkpointing for conversation continuity

## 🛠️ Technology Stack

- **LangGraph**: Workflow orchestration and state management
- **LangChain**: LLM integration and tool binding
- **OpenAI GPT-4**: Reasoning and content generation
- **Pydantic**: Data validation and schemas
- **Python 3.13+**: Runtime environment

## 📋 Prerequisites

- Python 3.13 or higher
- OpenAI API key
- Virtual environment (recommended)

## 🔧 Installation

1. **Clone and navigate to the project:**
   ```bash
   cd social-media-manager
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install langgraph langchain-openai python-dotenv
   ```

4. **Set up environment variables:**
   ```bash
   # Create .env file
   echo "OPENAI_API_KEY=your_api_key_here" > .env
   ```

## 🚀 Usage

### Quick Start

Run the interactive CLI:

```bash
python main.py
```

The agent will prompt for your name and start a conversation session.

### Available Commands

- **`exit`**: End the current session
- **`new`**: Start a new conversation thread (preserves memory)

### Example Interactions

```
👤 You: I want to create content about AI tools for developers
🤖 Agent: I'll help you plan content about AI tools for developers. Let me add this to your content calendar and update your profile if needed.

👤 You: My target audience is junior developers learning AI
🤖 Agent: Great! I've updated your profile to reflect that your target audience is junior developers learning AI. This will help me suggest more relevant content ideas.

👤 You: I prefer posting on LinkedIn and Twitter
🤖 Agent: Noted! I've updated your preferred platforms to LinkedIn and Twitter. This will help me tailor content suggestions for these platforms.
```

## 📊 Data Models

### User Profile
- **Name**: User's full name
- **Location**: Geographical location
- **Target Audience**: Intended content audience
- **Preferred Platforms**: List of social media platforms

### Content Calendar Entry
- **Title**: Content piece title/subject
- **Platform**: Target publishing platform
- **Deadline**: Scheduled publishing date/time
- **Status**: Progress stage (idea → draft → review → posted)
- **Tags**: Keywords and categories
- **Idea**: Brief concept summary

## 🔍 How It Works

1. **Input Processing**: User messages are analyzed by the content manager
2. **Memory Retrieval**: Relevant profile, calendar, and guideline data is fetched
3. **Decision Making**: AI determines what memory should be updated
4. **Memory Update**: Appropriate memory type is updated using specialized tools
5. **Response Generation**: User receives confirmation and relevant information

### Memory Update Types

- **`user`**: Updates personal profile information
- **`content_calendar`**: Adds or modifies content calendar entries
- **`guidelines`**: Updates content creation best practices

## 🧪 Development

### Project Structure

```
social-media-manager/
├── main.py              # CLI entry point
├── workflow.py          # LangGraph workflow definition
├── prompts.py           # System prompts and instructions
├── schemas/             # Pydantic data models
│   └── schemas.py
├── tools/               # Memory update tools
│   ├── __init__.py
│   ├── extractor.py     # Data extraction utilities
│   └── update_tools.py  # Memory update functions
└── langgraph.json       # Deployment configuration
```

### Adding New Features

1. **New Memory Type**: Add schema in `schemas/schemas.py`
2. **Update Function**: Create new function in `tools/update_tools.py`
3. **Workflow Integration**: Add node and edges in `workflow.py`
4. **Routing Logic**: Update `route_message` function

## 🚀 Deployment

### Local Development

```bash
langgraph dev
```

### Production

The `langgraph.json` configuration supports deployment to LangGraph Cloud or other hosting platforms.


---

**Built with LangGraph for practical, composable agent workflows.**
