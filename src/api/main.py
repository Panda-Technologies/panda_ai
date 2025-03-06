from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.api.api_fetch.models import UserModel, RequirementModel
from src.api.api_fetch.services import PandaService, UserService, DegreeService
import os
from typing import Dict, Any, List

# Initialize FastAPI app
app = FastAPI(title="Panda AI API", description="API for Panda user data")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Modify this in production to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get session cookie from environment variable or use default
SESSION_COOKIE = os.getenv("PANDA_SESSION_COOKIE", "gql-api=s%3AmZ9_NJ8jAs_Ajqq5B7Snfbx3ADBigNfa.nD0ni94Ku%2BnRYKhQYDXm%2BSMlHnHkIRS48RD84gaQbUA")

# Create services once at startup
panda_service = PandaService(session_cookie=SESSION_COOKIE)
user_service = UserService(panda_service=panda_service)
degree_service = DegreeService(panda_service=panda_service)

# API routes
@app.get("/")
async def root():
    return {"message": "Welcome to Panda AI API"}

@app.get("/user", response_model=UserModel)
async def get_user():
    try:
        user_data = user_service.get_user()
        return user_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch user data: {str(e)}")

@app.get("/degree", response_model=List[RequirementModel])
async def get_degree():
    try:
        degree_data = degree_service.get_degree_req("Business Administration")
        return degree_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch degree data: {str(e)}")

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Run the application using uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)