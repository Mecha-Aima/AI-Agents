from pathlib import Path

from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters
from google.adk.tools import google_search

from .prompt import SYSTEM_PROMPT 

PATH_TO_SERVER = str((Path(__file__).parent / "server.py").resolve())

root_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="life_tracker_agent",
    instruction=SYSTEM_PROMPT,
    tools=[
        MCPToolset(
            connection_params=StdioServerParameters(
                command="python3",
                args=[PATH_TO_SERVER],
            )
        )
    ]
)
