# type_def.py
from pydantic import BaseModel
from dataclasses import field
from typing import Dict, Any, List, Literal, Union, Optional

class TypeChatContext(BaseModel):
    category: str
    confidence: float
    data: Optional[Dict[str, Any]] = field(default_factory=dict)
    message: Optional[str]
    notTranslated: Optional[str]

class ValidatedIntent(BaseModel):
    type: Literal["degree_planning", "course_scheduling", "career_guidance", "general_question"]
    data: Dict[str, Any] = field(default_factory=dict)
    typechat_context: Optional[TypeChatContext] = None

class ConversationState(BaseModel):
    current_stage: str
    collected_info: Dict[str, Any] = field(default_factory=dict)
    typechat_history: Optional[List[Dict[str, Any]]] = field(default_factory=list)

class Message(BaseModel):
    type: Literal[
        "message",
        "researcher",
        "academic_info",
        "advisor",
        "state_validation",
        "error",
        "partial",
        "complete_response"
    ]
    message: str
    data: Union[List, Dict] = field(default_factory=dict)

    def to_json_line(self):
        return self.model_dump_json().replace("\n", "") + "\n"

class ConversationTask(BaseModel):
    message: str
    intent: ValidatedIntent
    conversation_state: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)

class ValidationResult(BaseModel):
    is_ready_to_proceed: bool
    current_stage: str
    missing_info: List[Dict[str, str]] = field(default_factory=list)
    next_action: str
    suggested_prompt: Optional[str] = None
    state_valid: bool
    collected_info: Dict[str, Any] = field(default_factory=dict)
    message: str

class ValidatedRequest(BaseModel):
    message: str
    intent: ValidatedIntent
    conversation_state: dict[str, Any] = None
    context: Optional[Dict[str, Any]] = field(default_factory=dict)