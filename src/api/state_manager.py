# state_manager.py
class ConversationStateManager:
    _instance = None
    _conversation_history = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConversationStateManager, cls).__new__(cls)
        return cls._instance

    @classmethod
    def get_history(cls, conversation_id: str = "default"):
        return cls._conversation_history.get(conversation_id, {
            "current_stage": "initial_contact",
            "collected_info": {},
            "chat_history": []
        })

    @classmethod
    def update_history(cls, conversation_id: str, state: dict):
        cls._conversation_history[conversation_id] = state

    @classmethod
    def clear_history(cls, conversation_id: str = None):
        if conversation_id:
            cls._conversation_history.pop(conversation_id, None)
        else:
            cls._conversation_history.clear()