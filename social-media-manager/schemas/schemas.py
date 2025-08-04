from pydantic import BaseModel, Field
from typing import Optional, Literal, TypedDict
from datetime import datetime


# User Profile Schema
class Profile(BaseModel):
    """The user's profile information"""
    name: Optional[str] = Field(description="Full name of the user", default=None)
    location: Optional[str] = Field(description="Geographical location of the user", default=None)
    target_audience: Optional[str] = Field(description="Intended audience for the user's content", default=None)
    preferred_platforms: list[str] = Field(description="List of platforms where the user prefers to share content", default_factory=list)


# Content Calendar Schema
class ContentCalendar(BaseModel):
    """A single entry representing a planned or ongoing content item in the calendar."""
    title: str = Field(description="Title or main subject of the content piece.")
    platform: Optional[str] = Field(description="Platform where this content will be published (e.g., Instagram, Blog).", default=None)
    deadline: Optional[datetime] = Field(description="Scheduled date and time for publishing.", default=None)
    status: Literal["idea", "draft", "review", "posted"] = Field(description="Current progress stage of the content (e.g., idea, draft, review, posted).", default="idea")
    tags: list[str] = Field(description="Keywords or categories related to this content.", default_factory=list)
    idea: str = Field(description="Brief summary or concept behind the content.", default=None)


# Update memory schema
class UpdateMemory(TypedDict):
    """ Decision on what memory type to update """
    update_type: Literal['user', 'content_calendar', 'guidelines']