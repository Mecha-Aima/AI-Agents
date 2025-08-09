from typing import Literal 

from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, START, END 
from langgraph.store.base import BaseStore
from langgraph.types import interrupt, Command

from gmail_assistant.tools import get_tools_by_name, get_tools
from gmail_assistant.prompts import *
from gmail_assistant.tools.gmail_tools import mark_as_read
from gmail_assistant.schemas import State, RouterSchema, StateInput, UserPreferences
from gmail_assistant.utils import parse_gmail, format_for_display, format_gmail_markdown
from dotenv import load_dotenv

load_dotenv(".env")

tools = get_tools(["send_email_tool", "check_calendar_tool", "schedule_meeting_tool", "Question", "Done"]) 
tools_by_name = get_tools_by_name(tools)

llm = init_chat_model("openai:gpt-4o-mini", temperature=0)
llm_router = llm.with_structured_output(RouterSchema)

llm = init_chat_model("openai:gpt-4o-mini", temperature=0.1)
llm_with_tools = llm.bind_tools(tools, tool_choice="required")

def get_memory(store: BaseStore, namespace: tuple, default_content=None):
    user_preferences = store.get(namespace, "user_preferences")

    if user_preferences:
        return user_preferences.value
    
    store.put(namespace, "user_preferences", default_content)
    return default_content


def update_memory(store: BaseStore, namespace, messages):
   user_preferences = store.get(namespace, "user_preferences")
   if user_preferences:
      llm = init_chat_model("openai:gpt-4o-mini", temperature=0.0).with_structured_output(UserPreferences)
      result = llm.invoke(
         [
               {"role": "system", "content": MEMORY_UPDATE_INSTRUCTIONS.format(current_profile=user_preferences.value, namespace=namespace)},
         ] + messages
      )
      store.put(namespace, "user_preferences", result.user_preferences)
   else:
      print(f"🔍 No user preferences found for namespace: {namespace}")


def triage_router(state: State, store: BaseStore) -> Command[Literal["triage_interrupt_handler", "response_agent", "__end__"]]:
   author, to, subject, email_thread, email_id = parse_gmail(state["email_input"])
   user_prompt = triage_user_prompt.format(
      author=author,
      to=to,
      subject=subject,
      email_thread=format_gmail_markdown(subject, author, to, email_thread, email_id)
   )
   print(f"🔍 User prompt: {user_prompt}")

   
   triage_preferences = get_memory(store, ("gmail_assistant", "triage_preferences"), default_content=default_triage_instructions)

   system_prompt = triage_system_prompt.format(
       background=default_background,
       triage_instructions=triage_preferences
   )

   result = llm_router.invoke(
       [
           {"role": "system", "content": system_prompt},
           {"role": "user", "content": user_prompt}
       ]
   )

   classification = result.classification 

   if classification == "ignore":
      print("🚫 Classification: IGNORE - This email can be safely ignored")

      goto = END 
      update = {
         'classification_decision': classification
      }
   
   elif classification == "respond":
      print("📬 Classification: RESPOND - This email requires a response")
      email_markdown = format_gmail_markdown(subject=subject, author=author, to=to, email_id=email_id, email_thread=email_thread)
      print(f"🔍 Email markdown: {email_markdown}")
      goto = "response_agent"
      update = {
         'messages': [{
               'role': 'user',
               'content': f"Respond to the following email:\n{email_markdown}"

            }],
         
         'classification_decision': classification
      }

   elif classification == "notify":
      print("🔔 Classification: NOTIFY - This email contains important information but does not require a response")
      update = {
         'classification_decision': classification
      }
      goto = "triage_interrupt_handler"
   else:
      raise ValueError(f"⛔️ Unexpected classification: {classification}")
   
   return Command(goto=goto, update=update)


def triage_interrupt_handler(state: State, store: BaseStore) -> Command[Literal["response_agent", "__end__"]]:
   author, to, subject, email_thread, email_id = parse_gmail(state["email_input"])
   email_markdown = format_gmail_markdown(subject, author, to, email_thread, email_id)

   messages = [{
      'role': 'user',
      'content': f"Email to notify user about: {email_markdown}"
   }]

   request = {
      'action_request': {
         'action': f"Postman: {state['classification_decision']}",
         'args': {}
      },
      'config': {
         'allow_ignore': True,
         'allow_respond': True,
         'allow_edit': False,
         'allow_accept': False
      },
      'description': email_markdown
   }

   response = interrupt([request])[0]

   if response["type"] == "ignore":
      messages.append({
         'role':'user',
         'content': 'The user decided to ignore the email even though it was classified as notify. Update triage preferences to capture this.'
      })
      update_memory(store, ("gmail_assistant", "triage_preferences"), messages)
      goto = END
   elif response["type"] == "response":
      user_input = response["args"]
      messages.append({
         'role': 'user',
         'content': f"User wants to respond to the email. Use this feedback to respond: {user_input}"
      }) 
      update_memory(store, ("gmail_assistant", "triage_preferences"), [{
         'role': 'user',
         'content': "The user decided to respond to the email, so update the triage preferences to capture this."
      }] + messages)
      goto = "response_agent"
   else:
      raise ValueError(f"🟥 Unexpected response type: {response['type']}")
   
   update = {
      "messages": messages
   }

   return Command(goto=goto, update=update)


def llm_call(state: State, store: BaseStore):
   cal_preferences = get_memory(store, ("gmail_assistant", "cal_preferences"), default_cal_preferences)
   response_preferences = get_memory(store, ("gmail_assistant", "response_preferences"), default_response_preferences)

   return {
      'messages': llm_with_tools.invoke([
         {
            'role': 'system', 'content': agent_system_prompt.format(
               tools_prompt=GMAIL_TOOLS_PROMPT,
               background=default_background,
               response_preferences=response_preferences,
               cal_preferences=cal_preferences
            )
         }
      ] + state["messages"])
   }


def interrupt_handler(state: State, store: BaseStore) -> Command[Literal["llm_call", "__end__"]]:
   result = []
   goto = "llm_call"

   require_review = ["send_email_tool", "schedule_meeting_tool", "Question"]

   for tool_call in state["messages"][-1].tool_calls:
      if tool_call["name"] not in require_review:
         # Execute tool call directly
         tool = tools_by_name[tool_call["name"]]
         observation = tool.invoke(tool_call["args"])
         result.append({ 'role': 'tool', 'content': observation, 'tool_call_id': tool_call["id"]})
         continue

      email_input = state["email_input"]
      author, to, subject, email_thread, email_id = parse_gmail(email_input)
      email_markdown = format_gmail_markdown(subject, author, to, email_thread, email_id)

      tool_formatted = format_for_display(tool_call)
      description = email_markdown + "\n\n" + tool_formatted

      if tool_call['name'] == 'send_email_tool':
         config = {
            "allow_ignore": True,
            "allow_respond": True,
            "allow_edit": True,
            "allow_accept": True,
         }
      elif tool_call['name'] == 'schedule_meeting_tool':
         config = {
            "allow_ignore": True,
            "allow_respond": True,
            "allow_edit": True,
            "allow_accept": True,
         }
      elif tool_call['name'] == 'Question':
         config = {
            "allow_ignore": True,
            "allow_respond": True,
            "allow_edit": False,
            "allow_accept": False,
         } 
      else:
         raise ValueError(f"❗️ Invalid tool call: {tool_call['name']}")
      

      request = {
         'action_request': {
            'action': tool_call["name"],
            "args": tool_call["args"]
         },
         'config': config,
         'description': description
      }

      response = interrupt([request])[0]

      if response["type"] == "accept":
         tool = tools_by_name[tool_call["name"]]
         observation = tool.invoke(tool_call["args"])
         result.append({"role": 'tool', 'content': observation, "tool_call_id": tool_call["id"]})

      elif response["type"] == "edit":
         tool = tools_by_name[tool_call["name"]]
         initial_tool_call = tool_call["args"]

         edited_args = response['args']['args']
         ai_message = state['messages'][-1]
         current_id = tool_call["id"]

         updated_tool_calls = [tc for tc in ai_message.tool_calls if tc["id"] != current_id] + [
            {'type': 'tool_call', 'name': tool_call['name'], 'args': edited_args, 'id': current_id}
         ]

         result.append(ai_message.model_copy(update={'tool_calls': updated_tool_calls}))

         if tool_call["name"] == 'send_email_tool':
            observation = tool.invoke(edited_args)
            result.append({'role': 'tool', 'content': observation, 'tool_call_id': current_id})
            update_memory(store, ('gmail_assistant', 'response_preferences'), [{
               'role': 'user',
               "content": f"User edited the email response. Here is the initial email generated by the assistant: {initial_tool_call}. Here is the edited email: {edited_args}. Follow all instructions above, and remember: {MEMORY_UPDATE_INSTRUCTIONS_REINFORCEMENT}."
            }])
         elif tool_call["name"] == 'schedule_meeting_tool':
            observation = tool.invoke(edited_args)
            result.append({"role": "tool", "content": observation, "tool_call_id": current_id})
            update_memory(store, ("gmail_assistant", 'cal_preferences'), [{
               'role': 'user',
               "content": f"User edited the calendar invitation. Here is the initial calendar invitation generated by the assistant: {initial_tool_call}. Here is the edited calendar invitation: {edited_args}. Follow all instructions above, and remember: {MEMORY_UPDATE_INSTRUCTIONS_REINFORCEMENT}."
            }])
         else:
            raise ValueError(f"❗️ Invalid tool call: {tool_call['name']}")

      elif response["type"] == "ignore":
         if tool_call["name"] == "send_email_tool":
            goto = END 
            result.append({
               'role': 'tool', 
               'content': "User ignored this email draft. Ignore this email and end the workflow.", 
               "tool_call_id": tool_call["id"]
            })

            update_memory(store, ('gmail_assistant', 'response_preferences'), [{
               'role': 'user',
               "content": "The user ignored the email draft. That means they did not want to respond to the email. Update the triage preferences to ensure emails of this type are not classified as respond. Follow all instructions above, and remember: {MEMORY_UPDATE_INSTRUCTIONS_REINFORCEMENT}."
            }])
         
         elif tool_call["name"] == "schedule_meeting_tool":
            goto = END 
            result.append({
               "role": "tool", "content": "User ignored this calendar meeting draft. Ignore this email and end the workflow.", "tool_call_id": tool_call["id"]
            })
            update_memory(store, ("gmail_assistant", "cal_preferences"), [{
               "role": "user",
               'content': 'The user ignored the calendar meeting draft. This means they did not want to schedule a meeting for this email. Update triage preferences to ensure emails of this type are not classified as respond. Follow all instructions above, and remember: {MEMORY_UPDATE_INSTRUCTIONS_REINFORCEMENT}'
            }])

         elif tool_call["name"] == "Question":
            result.append({"role": "tool", "content": "User ignored this question. Ignore this email and end the workflow.", "tool_call_id": tool_call["id"]})
            goto = END
            update_memory(store, ("gmail_assistant", "triage_preferences"), state["messages"] + result + [{
               "role": "user",
               "content": f"The user ignored the Question. That means they did not want to answer the question or deal with this email. Update the triage preferences to ensure emails of this type are not classified as respond. Follow all instructions above, and remember: {MEMORY_UPDATE_INSTRUCTIONS_REINFORCEMENT}."
            }])

      elif response["type"] == "response":
         user_feedback = response['args']
         if tool_call['name'] == 'send_email_tool':
            result.append({'role': 'tool', 'content': f"User gave feedback, which can we incorporate into the email. Feedback: {user_feedback}", 'tool_call_id': tool_call["id"]})
            update_memory(store, ('gmail_assistant', 'response_preferences'), state['messages'] + result + [{
               'role': 'user',
               'content': f"User gave feedback, which we can use to update response preferences. Follow all instructions above, and remember: {MEMORY_UPDATE_INSTRUCTIONS_REINFORCEMENT}"
            }])
         elif tool_call["name"] == 'schedule_meeting_tool':
            result.append({"role": "tool", "content": f"User gave feedback, which can we incorporate into the meeting request. Feedback: {user_feedback}", "tool_call_id": tool_call["id"]})
            update_memory(store, ("gmail_assistant", "cal_preferences"), state["messages"] + result + [{
               "role": "user",
               "content": f"User gave feedback, which we can use to update calendar preferences. Follow all instructions above, and remember: {MEMORY_UPDATE_INSTRUCTIONS_REINFORCEMENT}"
            }])
         elif tool_call['name'] == 'Question': 
            result.append({'role': 'tool', 'content': f"User answered the question, which we can use for any follow-up actions. Feedback: {user_feedback}", "tool_call_id": tool_call['id']})
            update_memory(store, ("gmail_assistant", "cal_preferences"), state["messages"] + result + [{
               "role": "user",
               "content": f"User gave feedback, which we can use to update the calendar preferences. Follow all instructions above, and remember: {MEMORY_UPDATE_INSTRUCTIONS_REINFORCEMENT}."
            }])
         else:
            raise ValueError(f"❗️ Invalid tool call: {tool_call['name']}")

   update = {
      'messages': result
   }

   return Command(goto=goto, update=update)


def should_continue(state: State, store: BaseStore) -> Literal["interrupt_handler", "__end__"]:
   """Route to tool handler, or end if Done tool called"""
   messages = state['messages']
   last_message = messages[-1] if messages else None 
   if last_message and last_message.tool_calls:
      for tool_call in last_message.tool_calls:
         if tool_call["name"] == "Done":
            return "mark_as_read_node"
         else:
            return "interrupt_handler"
         
def mark_as_read_node(state: State, store: BaseStore) :
   email_input = state["email_input"]
   author, to, subject, email_thread, email_id = parse_gmail(email_input)
   mark_as_read(email_id)

# response sub-agent
builder = StateGraph(State)
builder.add_node("llm_call", llm_call)
builder.add_node("interrupt_handler", interrupt_handler)
builder.add_node("mark_as_read_node", mark_as_read_node)

builder.add_edge(START, "llm_call")
builder.add_conditional_edges(
   "llm_call",
   should_continue,
   {
         "interrupt_handler": "interrupt_handler",
         "mark_as_read_node": "mark_as_read_node",
   }
)
builder.add_edge("mark_as_read_node", END)

response_agent = builder.compile()

overall_workflow = StateGraph(State, input=StateInput)
overall_workflow.add_node("triage_router", triage_router)
overall_workflow.add_node("triage_interrupt_handler", triage_interrupt_handler)
overall_workflow.add_node("response_agent", response_agent)
overall_workflow.add_node("mark_as_read_node", mark_as_read_node)

overall_workflow.add_edge(START, "triage_router")
overall_workflow.add_edge("mark_as_read_node", END)

gmail_assistant = overall_workflow.compile()
