from langchain_core.runnables import RunnableConfig
from langgraph.graph import MessagesState
from langgraph.store.base import BaseStore
from langchain_core.messages import merge_message_runs, HumanMessage, SystemMessage
from datetime import datetime
from uuid import uuid4

from prompts import *
from tools.extractor import *

def update_profile(state: MessagesState, config: RunnableConfig, store: BaseStore):
    """Reflect on the chat history and update user profile"""
    user_id = config["configurable"]["user_id"]
    namespace = ("profile", user_id)

    existing_items = store.search(namespace)
    tool_name = "Profile"
    existing_memories = [(item.key, tool_name, item.value) for item in existing_items] if existing_items else None

    system_message = TRUSTCALL_INSTRUCTION.format(time=datetime.now().isoformat())
    updated_messages = list(merge_message_runs(messages=[SystemMessage(content=system_message)] + state['messages'][:-1]))

    result = profile_extractor.invoke({'messages': updated_messages, 'existing': existing_memories})

    for r, rmeta in zip(result['responses'], result['response_metadata']):
       store.put(namespace, rmeta.get('json_doc_id', uuid4()), r.model_dump(mode='json'))

    tool_calls = state['messages'][-1].tool_calls
    return {"messages": [{"role": "tool", "content": "Updated user profile", "tool_call_id": tool_calls[0]['id']}]}


def update_content_calendar(state: MessagesState, config: RunnableConfig, store: BaseStore):
    user_id = config['configurable']['user_id']
    namespace = ('content_calendar', user_id)

    existing_items = store.search(namespace)
    tool_name = 'ContentCalendar'
    existing_memories = [(item.key, tool_name, item.value) for item in existing_items] if existing_items else None

    system_message = TRUSTCALL_INSTRUCTION.format(time=datetime.now().isoformat())
    updated_messages = list(merge_message_runs(messages=[SystemMessage(content=system_message)] + state['messages'][:-1]))

    result = content_extractor.invoke({'messages': updated_messages, 'existing': existing_memories})

    for r, rmeta in zip(result['responses'], result['response_metadata']):
        store.put(namespace, rmeta.get('json_doc_id', uuid4()), r.model_dump(mode='json'))
    
    tool_calls = state['messages'][-1].tool_calls
    calendar_update_message = extract_tool_info(spy.called_tools, 'ContentCalendar')

    return {"messages": [{"role": "tool", "content": calendar_update_message, "tool_call_id": tool_calls[0]['id']}]}


def update_guidelines(state: MessagesState, config: RunnableConfig, store: BaseStore):
    user_id = config['configurable']['user_id']
    namespace = ('guidelines', user_id)

    existing_memory = store.get(namespace, "content_guidelines")
    system_message = CREATE_GUIDELINES.format(guidelines=existing_memory.value if existing_memory else "")

    new_memory = model.invoke(
        [SystemMessage(content=system_message)] +
        state['messages'][:-1] +
        [HumanMessage(content="Please update the guidelines.")]
    )

    store.put(namespace, "content_guidelines", {'memory': new_memory.content})
    tool_calls = state['messages'][-1].tool_calls

    return {'messages': [{'role': 'tool', 'content': 'Updated content creation guidelines', 'tool_call_id': tool_calls[0]['id']}]}