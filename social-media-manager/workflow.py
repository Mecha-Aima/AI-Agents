from langgraph.graph import MessagesState, START, END, StateGraph
from langchain_core.runnables import RunnableConfig
from langgraph.store.base import BaseStore
from langchain_core.messages import SystemMessage
from langgraph.store.memory import InMemoryStore
from langgraph.checkpoint.memory import MemorySaver
from typing import Literal

from tools import *
from prompts import MODEL_SYSTEM_MESSAGE
from schemas import *

def content_manager(state: MessagesState, config: RunnableConfig, store: BaseStore):
    user_id = config['configurable']['user_id']

    profile_memories = store.search(('profile', user_id))
    user_profile = profile_memories[0].value if profile_memories else None 

    content_calendar_memories = store.search(('content_calendar', user_id))
    content_calendar = "\n".join(f"{item.key}: {item.value}" for item in content_calendar_memories)

    guideline_memories = store.search(('guidelines', user_id))
    content_guidelines = guideline_memories[0].value if guideline_memories else ""

    system_message = MODEL_SYSTEM_MESSAGE.format(
        user_profile=user_profile,
        content_calendar=content_calendar,
        guidelines=content_guidelines
    )

    response = model.bind_tools([UpdateMemory], parallel_tool_calls=True).invoke(
        [SystemMessage(content=system_message)] + state['messages']
    )

    return {'messages': [response]}


def route_message(state: MessagesState, config: RunnableConfig, store: BaseStore) ->  Literal[END, "update_content_calendar", "update_guidelines", "update_profile"]: # type: ignore
    """Decide where to update the memory collection"""
    message = state['messages'][-1]

    if len(message.tool_calls) == 0:
        return END
    tool_call = message.tool_calls[0]
    if tool_call['args']['update_type'] == 'user':
        return "update_profile"
    elif tool_call['args']['update_type'] == 'content_calendar':
        return "update_content_calendar"
    elif tool_call['args']['update_type'] == 'guidelines':
        return "update_guidelines"
    else:
        raise ValueError(f"Unknown update type: {tool_call['args']['update_type']}")
    

def create_workflow():
    workflow = StateGraph(MessagesState)

    workflow.add_node("content_manager", content_manager)
    workflow.add_node("update_profile", update_profile)
    workflow.add_node("update_content_calendar", update_content_calendar)
    workflow.add_node("update_guidelines", update_guidelines)

    workflow.add_edge(START, "content_manager")
    workflow.add_conditional_edges("content_manager", route_message)
    workflow.add_edge("update_profile", "content_manager")
    workflow.add_edge("update_content_calendar", "content_manager")
    workflow.add_edge("update_guidelines", "content_manager")

    across_thread_memory = InMemoryStore()
    within_thread_memory = MemorySaver()

    return workflow.compile(checkpointer=within_thread_memory, store=across_thread_memory)






