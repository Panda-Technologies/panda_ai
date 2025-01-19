import os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, Literal

from src.api.orchestrator import ConversationTask, orchestrate_conversation, create_message

base = Path(__file__).resolve().parent
load_dotenv()

app = FastAPI()

# CORS configuration (same as original)
code_space = os.getenv("CODESPACE_NAME")
app_insights = os.getenv("APPINSIGHTS_CONNECTIONSTRING")

if code_space:
    origin_8000 = f"https://{code_space}-8000.app.github.dev"
    origin_5173 = f"https://{code_space}-5173.app.github.dev"
    ingestion_endpoint = app_insights.split(';')[1].split('=')[1]
    origins = [origin_8000, origin_5173, os.getenv("API_SERVICE_ACA_URI"),
              os.getenv("WEB_SERVICE_ACA_URI"), ingestion_endpoint]
else:
    origins = ['*']

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ValidatedIntent(BaseModel):
    type: Literal["degree_planning", "course_scheduling", "career_guidance", "general_question"]
    data: Dict[str, Any]

class ValidatedRequest(BaseModel):
    message: str
    intent: ValidatedIntent
    conversation_state: Optional[Dict[str, Any]] = None
    context: Optional[Dict[str, Any]] = None


@app.post("/api/chat")
async def chat(request: ValidatedRequest):
    try:
        task = ConversationTask(...)

        async def error_handled_stream():
            try:
                async for message in orchestrate_conversation(task):
                    yield message
            except Exception as e:
                error_msg = create_message(
                    "error",
                    "Stream error",
                    {"error": str(e)}
                )
                yield error_msg

        return StreamingResponse(
            error_handled_stream(),
            media_type="text/event-stream",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {"message": "UNC Academic Advisor API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)