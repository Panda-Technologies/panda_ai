from pydantic import BaseModel, Field
from typing import Dict, Any, List, Literal, Union, Optional


class ValidatedIntent(BaseModel):
    type: Literal["degree_planning", "course_scheduling", "career_guidance", "general_question"]
    data: Dict[str, Any]

class Message(BaseModel):
    type: Literal[
        "message",
        "researcher",
        "academic_info",
        "advisor",
        "state_validation",
        "error",
        "partial",
    ]
    message: str
    data: Union[List, Dict] = Field(default_factory={})

    def to_json_line(self):
        return self.model_dump_json().replace("\n", "") + "\n"

class ConversationTask(BaseModel):
    message: str
    intent: ValidatedIntent
    conversation_state: Dict[str, Any] = Field(default_factory={})
    context: Dict[str, Any] = Field(default_factory={})

class ValidationResult(BaseModel):
    is_ready_to_proceed: bool
    current_stage: str
    missing_info: List[Dict[str, str]]
    next_action: str
    suggested_prompt: Optional[str]  # Make it optional
    state_valid: bool