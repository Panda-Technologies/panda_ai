from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import json

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

async def stream_response(task: ConversationTask):
    async for message in orchestrate_conversation(task):
        yield message + "\n"

def advisor_response(message: str):
    async def generate():
        yield create_message("advisor", message, {"text": message})
    return generate()


@app.post("/api/chat")
async def chat_endpoint(request: ValidatedRequest):
    try:
        conversation_id = request.context.get("conversation_id", "default")
        current_state = state_manager.get_history(conversation_id)

        # Add message to history
        current_state["chat_history"].append({
            "role": "user",
            "message": request.message,
            "intent": request.intent.model_dump()
        })

        flow_validation = await validate_state(request.intent, current_state)

        # Update state with ALL previous info plus new info
        current_state["collected_info"].update(flow_validation.get("collected_info", {}))
        current_state["current_stage"] = flow_validation.get("current_stage", current_state["current_stage"])

        # Store updated state
        state_manager.update_history(conversation_id, current_state)

        task = ConversationTask(
            message=request.message,
            intent=request.intent,
            conversation_state=current_state,
            context={"validation_result": flow_validation}
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