import json
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from typing import Dict, Any, AsyncGenerator

from src.api.agents.validator.validator import validate_state
from src.api.state_manager import ConversationStateManager
from src.api.type_def import ValidatedRequest, ValidatedIntent
from src.api.orchestrator import ConversationTask, orchestrate_conversation, create_message

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

state_manager = ConversationStateManager()


async def stream_response(task: ConversationTask) -> AsyncGenerator[str, None]:
    """Stream response with both partial updates and complete message"""
    complete_chunks = []

    async for message in orchestrate_conversation(task):
        # Store message chunk if it's a partial or complete_response
        json_msg = json.loads(message)
        if json_msg["type"] in ["partial", "complete_response"]:
            if "text" in json_msg["data"]:
                complete_chunks.append(json_msg["data"]["text"])

        # Yield each message line
        yield message

    # Add the complete message to the state
    conversation_id = task.context.get("conversation_id", "default")
    current_state = state_manager.get_history(conversation_id)
    current_state["chat_history"].append({
        "role": "assistant",
        "message": "".join(complete_chunks),
        "timestamp": datetime.now().isoformat()
    })
    state_manager.update_history(conversation_id, current_state)


def process_intent_data(intent: ValidatedIntent) -> Dict[str, Any]:
    """Extract relevant information from TypeChat intent data"""
    collected_info = {}

    if intent.data:
        # Process initial info
        if initial_info := intent.data.get("initialInfo", {}):
            collected_info.update({
                "major": initial_info.get("major"),
                "degree_type": initial_info.get("degreeType"),
                "student_intent": initial_info.get("category")
            })

        # Process scheduling preferences
        if scheduling := intent.data.get("schedulingPreferences", {}):
            collected_info["preferences"] = {
                "time_preference": scheduling.get("timePreference"),
                "summer_available": scheduling.get("summerAvailable"),
                "constraints": scheduling.get("constraints", [])
            }

        # Process course focus preferences
        if preferences := intent.data.get("courseFocusPreferences", {}):
            collected_info["interests"] = preferences.get("preferredGenEdFocuses", {}).get("focusAreas", [])

    return {k: v for k, v in collected_info.items() if v is not None}


@app.post("/api/chat")
async def chat_endpoint(request: ValidatedRequest):
    """Handle chat interactions while maintaining state"""
    try:
        conversation_id = request.context.get("conversation_id", "default")
        current_state = state_manager.get_history(conversation_id)

        # Merge new intent data with existing state
        new_info = process_intent_data(request.intent)

        # Preserve existing collected info and merge with new info
        current_state["collected_info"] = {
            **current_state.get("collected_info", {}),
            **new_info
        }

        # Add message to chat history with full context
        current_state["chat_history"].append({
            "role": "user",
            "message": request.message,
            "intent": request.intent.model_dump(),
            "timestamp": datetime.now().isoformat()
        })

        # Validate state and flow
        flow_validation = await validate_state(
            intent=request.intent,
            state=current_state,
            message=request.message
        )

        # Update state with new information
        current_state["collected_info"].update(new_info)
        current_state["current_stage"] = flow_validation.get("current_stage", current_state["current_stage"])
        current_state["validation_result"] = flow_validation
        current_state["last_intent"] = request.intent.model_dump()

        # Store updated state
        state_manager.update_history(conversation_id, current_state)

        # Create conversation task with conversation_id in context
        task = ConversationTask(
            message=request.message,
            intent=request.intent,
            conversation_state=current_state,
            context={
                "validation_result": flow_validation,
                "conversation_id": conversation_id
            }
        )

        return StreamingResponse(
            stream_response(task),
            media_type="text/event-stream"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)