# Dev Tools Research Assistant

A Streamlit application that helps developers research and compare development tools using LangGraph and Firecrawl.

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- `uv` package manager
- Firecrawl API key

### Setup
1. **Install dependencies:**
   ```bash
   cd dev-research-agent
   uv sync
   ```

2. **Set up environment variables:**
   ```bash
   # Create .env file in the project root
   echo "FIRECRAWL_API_KEY=your_api_key_here" > .env
   ```

3. **Run the app:**
   ```bash
   # Option 1: Use the launcher script
   python run_app.py
   
   # Option 2: Direct Streamlit command
   STREAMLIT_SERVER_PYTHON_PATH="../.venv/bin/python" streamlit run app.py
   
   # Option 3: Use uv virtual environment directly
   ../.venv/bin/python -m streamlit run app.py
   ```

## 🔧 Recent Fixes

### Rate Limiting & Error Handling
- **Fixed IndexError**: Added proper checks for empty search results
- **Rate Limiting**: Implemented exponential backoff retry mechanism
- **Error Recovery**: Graceful handling of API failures and network issues
- **User Feedback**: Better status updates and error messages

### Key Improvements
1. **Robust Error Handling**: The app now handles rate limiting (429 errors) gracefully
2. **Retry Logic**: Automatic retries with exponential backoff for failed requests
3. **Empty Result Handling**: Proper handling when no search results are found
4. **Progress Updates**: Real-time status updates during research process
5. **Graceful Degradation**: App continues working even if some tools can't be researched

## 🛠️ Architecture

- **LangGraph**: State machine for orchestrating the research workflow
- **Firecrawl**: Web scraping and search capabilities
- **Streamlit**: User interface
- **OpenAI GPT-4**: LLM for analysis and recommendations

## 📝 Usage

1. Enter a development tool or technology you want to research
2. The app will:
   - Search for relevant articles and tools
   - Extract tool names from the content
   - Research each tool's details (pricing, features, etc.)
   - Provide recommendations and comparisons

## ⚠️ Rate Limiting

The app includes built-in rate limiting protection:
- 1-second delays between requests
- Exponential backoff retry mechanism
- Graceful handling of 429 errors
- User-friendly error messages

## 🔍 Troubleshooting

### Common Issues
1. **ModuleNotFoundError**: Ensure you're using the correct Python interpreter from `.venv`
2. **Rate Limiting**: Wait a few minutes and try again
3. **No Results**: Try rephrasing your query or wait for rate limits to reset

### Environment Issues
If you encounter environment problems:
```bash
# Recreate the virtual environment
uv sync --reinstall
```

## 📊 Features

- **Multi-step Research**: Extracts tools → Researches details → Provides analysis
- **Real-time Updates**: Progress indicators and status messages
- **Comprehensive Analysis**: Pricing, features, tech stack, integrations
- **Error Recovery**: Continues working even with partial failures
- **Rate Limit Protection**: Built-in retry logic and delays 