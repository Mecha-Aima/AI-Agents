from pydantic import BaseModel, Field
from typing_extensions import TypedDict, Literal 
from langgraph.graph import MessagesState

class RouterSchema(BaseModel):
    """Analyze incoming email and route it based on its content"""
    reasoning: str = Field(
        description="Logical reasoning behind classification"
    )
    classification: Literal["ignore", "respond", "notify"] = Field(
        description="The category assigned to the email:" \
        "'ignore' for irrelevant emails," \
        "'notify' for important information that doesn't require response" \
        "'respond' for emails that need a response"
    )


class StateInput(TypedDict):
    email_input: dict 


class State(MessagesState):
    email_input: dict
    classification_decision: Literal["ignore", "respond", "notify"]


class UserPreferences(BaseModel):
    chain_of_thought: str = Field(description="Reasoning about which user preferences need to add/update if required")
    user_preferences: str = Field(description="Updated user preferences")


class CriteriaGrade(BaseModel):
    grade: bool = Field(description="Does the response meet the provided criteria?")
    justification: str = Field(description="The justification for the grade and score, including specific examples from the response.")