from typing import Dict, List, Optional
from langchain_core.tools import BaseTool 
from pydantic import BaseModel
from langchain_core.tools import tool

@tool
class Done(BaseModel):
    """E-mail has been sent."""
    done: bool

@tool
class Question(BaseModel):
      """Question to ask user."""
      content: str

def get_tools(tool_names: Optional[List[str]] = None) -> List[BaseTool]:
    try:
        from gmail_assistant.tools.gmail_tools import (
            fetch_emails_tool,
            send_email_tool,
            check_calendar_tool,
            schedule_meeting_tool
        )

        all_tools = {
            "fetch_emails_tool": fetch_emails_tool,
            "send_email_tool": send_email_tool,
            "check_calendar_tool": check_calendar_tool,
            "schedule_meeting_tool": schedule_meeting_tool,
            "Question": Question,
            "Done": Done
        }

    except ImportError:
        raise ImportError("❌ Failed to import tools.")
    
    if tool_names is None:
        return list(all_tools.values())
    
    return [all_tools[name] for name in tool_names if name in all_tools]


def get_tools_by_name(tools: Optional[List[BaseTool]] = None) -> Dict[str, BaseTool]:
    if tools is None:
        tools = get_tools()

    return {tool.name: tool for tool in tools}
