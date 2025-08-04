from venv import create
from trustcall import create_extractor
from langchain_openai import ChatOpenAI

from schemas import Profile, ContentCalendar

class Spy:
    def __init__(self):
        self.called_tools = []


    def __call__(self, run):
        q = [run]
        while q:
            r = q.pop()
            if r.child_runs:
                q.extend(r.child_runs)
            if r.run_type == "chat_model":
                self.called_tools.append(
                    r.outputs["generations"][0][0]["message"]["kwargs"]["tool_calls"]
                )



def extract_tool_info(tool_calls, schema_name="Memory"):
    """Extract information from tool calls for both patches and new memories.

    Args:
        tool_calls: List of tool calls from the model
        schema_name: Name of the schema tool (e.g., "Memory", "Profile")
    """
    call_info = []

    for call_group in tool_calls:
        for call in call_group:
            if call["name"] == "PatchDoc":
                call_info.append({
                    'type': 'update',
                    'doc_id': call['args']['json_doc_id'],
                    'planned_edits': call['args']['planned_edits'],
                    'value': call['args']['patches'][0]['value']
                })
            elif call["name"] == schema_name:
                call_info.append({
                    'type': 'new',
                    'value': call['args']
                })

    results = []
    for call in call_info:
        if call['type'] == 'update':
            results.append(
                f"Document {call['doc_id']} updated:\n"
                f"Plan: {call['planned_edits']}\n"
                f"Added content: {call['value']}"
            )
        else:
            import json
            results.append(
                f"New {schema_name} created:\n"
                f"Content: {json.dumps(call['value'], indent=2)}"
            )
    
    return "\n\n".join(results)



spy = Spy()
model = ChatOpenAI(model="gpt-4o-mini", temperature=0)

profile_extractor = create_extractor(
    model,
    tools=[Profile],
    tool_choice="Profile",
)

content_extractor = create_extractor(
    model,
    tools=[ContentCalendar],
    tool_choice="ContentCalendar",
    enable_inserts=True
).with_listeners(on_end=spy)

