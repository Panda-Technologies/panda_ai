from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import json
from src.api.type_def import ValidatedRequest, ValidatedIntent
from src.api.orchestrator import ConversationTask, orchestrate_conversation

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def stream_response(task: ConversationTask):
    async for message in orchestrate_conversation(task):
        yield message + "\n"

@app.post("/api/chat")
async def chat_endpoint(request: ValidatedRequest):
    try:
        intent_data = {
            "type": "career_guidance",
            "data": {
                "major": "Computer Science",
                "degree_type": "BS",
                "interests": ["artificial intelligence"],
                "topics": ["career_path", "grad_school"],
                "other_schools": ["Duke", "MIT", "Stanford"]
            }
        } if "major" in str(request.message).lower() else {
            "type": "general_question",
            "data": {
                "topic": request.message,
                "needs_research": True
            }
        }

        task = ConversationTask(
            message=request.message,
            intent=ValidatedIntent(**intent_data),
            conversation_state={
                "current_stage": "initial_contact",
                "collected_info": {
                    "student_intent": "explore_careers" if "major" in str(request.message).lower() else "general_inquiry",
                    "topic": request.message
                }
            },
            context={
                "academic_year": "2024",
                "research_needed": True,
                "research_topics": ["career_path", "other_universities"] if "major" in str(request.message).lower() else ["general_info"]
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