from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from agent import MeetingSchedulerAgent
from models import MeetingResponse
import uvicorn

# Initialize FastAPI app
app = FastAPI(
    title="AI Calendar Agent API",
    description="Schedule meetings using natural language",
    version="1.0.0"
)

# Add CORS middleware (allows frontend to call this API)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the agent (singleton - created once)
agent = MeetingSchedulerAgent()


# Request model for the API
class ScheduleRequest(BaseModel):
    user_input: str
    user_email: EmailStr
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_input": "Schedule a meeting with john@example.com tomorrow at 2pm to discuss AI project",
                "user_email": "kush@example.com"
            }
        }


# Health check endpoint
@app.get("/")
def read_root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "message": "AI Calendar Agent API is running",
        "version": "1.0.0"
    }


# Main scheduling endpoint
@app.post("/schedule", response_model=MeetingResponse)
def schedule_meeting(request: ScheduleRequest):
    """
    Schedule a meeting using natural language
    
    Args:
        request: ScheduleRequest with user_input and user_email
        
    Returns:
        MeetingResponse with success status and event details
        
    Example:
        POST /schedule
        {
            "user_input": "Book a call tomorrow at 3pm with tim@example.com",
            "user_email": "kush@example.com"
        }
    """
    try:
        # Run the agent
        result = agent.run(
            user_input=request.user_input,
            user_email=request.user_email
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to schedule meeting: {str(e)}"
        )


# Get agent status
@app.get("/status")
def get_status():
    """Get agent status and configuration"""
    return {
        "agent": "MeetingSchedulerAgent",
        "llm_model": "gpt-4o-mini",
        "google_apis": ["Calendar", "Gmail"],
        "workflow_nodes": ["parse", "validate", "create_event", "send_email"]
    }


# Run the server
if __name__ == "__main__":
    print("🚀 Starting AI Calendar Agent API...")
    print("📍 API will be available at: http://localhost:8000")
    print("📚 API docs at: http://localhost:8000/docs")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True  # Auto-reload on code changes
    )