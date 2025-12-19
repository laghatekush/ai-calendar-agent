from pydantic import BaseModel, EmailStr, field_validator
from datetime import datetime
from typing import Optional

class MeetingRequest(BaseModel):
    """User's input for scheduling a meeting"""
    user_input: str
    user_email: EmailStr

class MeetingDetails(BaseModel):
    """Parsed meeting information"""
    title: str
    date: str  # Format: YYYY-MM-DD
    start_time: str  # Format: HH:MM (24-hour)
    end_time: str  # Format: HH:MM (24-hour)
    attendee_email: Optional[str] = None
    description: Optional[str] = None
    
    @field_validator('date')
    @classmethod
    def validate_date(cls, v: str) -> str:
        """Ensure date is not in the past"""
        try:
            meeting_date = datetime.strptime(v, '%Y-%m-%d').date()
            if meeting_date < datetime.now().date():
                raise ValueError("Meeting date cannot be in the past")
            return v
        except ValueError as e:
            raise ValueError(f"Invalid date format. Use YYYY-MM-DD: {e}")

class MeetingResponse(BaseModel):
    """Response after scheduling"""
    success: bool
    message: str
    event_link: Optional[str] = None
    error: Optional[str] = None