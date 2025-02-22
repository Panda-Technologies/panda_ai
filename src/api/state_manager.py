from typing import Dict, Any, Optional
from datetime import datetime


class ConversationStateManager:
    _instance = None
    _conversation_history = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConversationStateManager, cls).__new__(cls)
        return cls._instance

    @classmethod
    def get_history(cls, conversation_id: str = "default") -> dict:
        """Get conversation history with proper initialization of empty state"""
        if conversation_id not in cls._conversation_history:
            cls._conversation_history[conversation_id] = {
                "current_stage": "initial_contact",
                "collected_info": {
                    "major": None,
                    "degree_type": None,
                    "academic_year": None,
                    "student_intent": None,
                    "completed_courses": [],
                    "current_courses": [],
                    "preferences": {},
                },
                "chat_history": [],
                "typechat_history": [],
                "last_update": datetime.now().isoformat()
            }
        return cls._conversation_history[conversation_id]

    @classmethod
    def update_history(cls, conversation_id: str, state: dict):
        current_state = cls.get_history(conversation_id)

        # Properly format and append chat history
        if "chat_history" in state and len(state["chat_history"]) > 0:
            new_messages = []
            for msg in state["chat_history"]:
                if isinstance(msg, dict) and "role" in msg and "message" in msg:
                    new_messages.append(msg)
                elif isinstance(msg, str):
                    new_messages.append({
                        "role": "user" if len(current_state["chat_history"]) % 2 == 0 else "assistant",
                        "message": msg,
                        "timestamp": datetime.now().isoformat()
                    })

            # Keep last N messages
            MAX_HISTORY = 15
            current_state["chat_history"] = (
            current_state["chat_history"] + new_messages
            )[-MAX_HISTORY:]

    @classmethod
    def get_current_info(cls, conversation_id: str) -> Dict[str, Any]:
        """Get the current collected information"""
        state = cls.get_history(conversation_id)
        return state.get("collected_info", {})

    @classmethod
    def clear_history(cls, conversation_id: Optional[str] = None):
        """Clear history for specific conversation or all conversations"""
        if conversation_id:
            cls._conversation_history.pop(conversation_id, None)
        else:
            cls._conversation_history.clear()