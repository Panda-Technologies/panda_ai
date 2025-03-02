from enum import Enum
from typing import List, Any, Dict, Optional

from pydantic import BaseModel, Field
from semantic_kernel.contents import ChatHistory

class ConversationState(str, Enum):
    """Enum representing possible conversation states."""
    INITIAL = "initial"
    DEGREE_PLANNING = "degree_planning"
    GENERAL_QA = "general_qa"
    COURSE_QUESTION = "course_question"

class ConversationArtifact(BaseModel):
    """Conversation state and collected information."""
    current_state: ConversationState = ConversationState.INITIAL
    student_name: Optional[str] = None
    student_id: Optional[str] = None
    degree_program: Optional[str] = None
    completed_courses: List[str] = Field(default_factory=list)
    current_semester: Optional[str] = None
    available_days: List[str] = Field(default_factory=list)
    interests: List[str] = Field(default_factory=list)
    grad_year: Optional[str] = None


class ConversationContext(BaseModel):
    """Context for the current conversation."""
    chat_history: List[Dict[str, Any]] = Field(default_factory=list)
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