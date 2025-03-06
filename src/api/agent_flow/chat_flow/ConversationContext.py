from enum import Enum
from typing import List, Any, Dict, Optional

from pydantic import BaseModel, Field
from semantic_kernel.contents import ChatHistory


class AcademicTerm(BaseModel):
    """Represents an academic term with season and year."""
    term: Optional[str] = None  # "Fall", "Spring", "Summer"
    year: Optional[int] = None

    def __str__(self):
        if self.term and self.year:
            return f"{self.term} {self.year}"
        return "Unspecified Term"


class ConversationArtifact(BaseModel):
    """Conversation state and collected degree planning information."""
    # Conversation state
    current_state: str = "initial"

    # Basic degree information
    degree_type: Optional[str] = None  # "BA" or "BS"
    major: Optional[str] = None
    concentration: Optional[str] = None
    minor: Optional[List[str]] = Field(default_factory=list)

    # Term information
    start_term: Optional[AcademicTerm] = None
    current_term: Optional[AcademicTerm] = None

    # Course load and scheduling preferences
    preferred_courses_per_semester: Optional[int] = None
    min_courses_per_semester: Optional[int] = None
    max_courses_per_semester: Optional[int] = None
    time_preference: Optional[str] = None  # "morning", "afternoon", "evening", "no preference"
    summer_available: Optional[bool] = None

    # Career and interest information
    career_goals: Optional[List[str]] = Field(default_factory=list)

    total_credits_needed: Optional[int] = None
    courses_selected: Optional[List[str]] = Field(default_factory=list)


class ConversationContext(BaseModel):
    """Context for the current conversation."""
    messages: List[Dict[str, Any]] = Field(default_factory=list)
    # cached_rag_results: List[Dict[str, str]] = Field(default_factory=list)
    last_intent: Optional[str] = None
    artifact: ConversationArtifact = Field(default_factory=ConversationArtifact)


    def add_message(self, role: str, content: str, name: Optional[str] = None) -> None:
        """Add a message to the history."""
        message = {
            "role": role,
            "content": content
        }
        if name:
            message["name"] = name
        self.messages.append(message)

    # def add_rag_result(self, content: str) -> None:


    def add_user_message(self, content: str) -> None:
        """Add a user message to the history."""
        self.add_message("user", content)

    def add_assistant_message(self, content: str) -> None:
        """Add an assistant message to the history."""
        self.add_message("assistant", content)

    def add_system_message(self, content: str) -> None:
        """Add a system message to the history."""
        self.add_message("system", content)

    def to_chat_history(self) -> ChatHistory:
        """Convert internal message format to Semantic Kernel's ChatHistory."""
        chat_history = ChatHistory()

        for msg in self.messages:
            role = msg["role"]
            content = msg["content"]

            if role == "user":
                chat_history.add_user_message(content)
            elif role == "assistant":
                chat_history.add_assistant_message(content)
            elif role == "system":
                chat_history.add_system_message(content)

        return chat_history

    def from_chat_history(self, chat_history: ChatHistory) -> None:
        """Update internal messages from a ChatHistory object."""
        self.messages = []

        # Convert each message in the ChatHistory to our internal format
        for message in chat_history:
            role = message.role.value.lower()  # Convert AuthorRole to string
            self.add_message(role, message.content)