from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from typing import TypedDict
from datetime import datetime, timedelta
import json
from models import MeetingDetails, MeetingResponse
from google_api import GoogleCalendarAPI
from config import OPENAI_API_KEY
from logger import setup_logger, TimestampedLogger
from exceptions import ParseError, ValidationError, GoogleAPIError
from cache import AgentCache
from validators import InputValidator


base_logger = setup_logger("agent")
logger = TimestampedLogger(base_logger)


class AgentState(TypedDict):
    """State that flows through the graph"""
    user_input: str
    user_email: str
    meeting_details: dict
    calendar_result: dict
    email_result: dict
    final_response: dict
    error: str


class MeetingSchedulerAgent:
    """AI Agent that schedules meetings using LangGraph"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            api_key=OPENAI_API_KEY,
            temperature=0
        )
        self.google_api = GoogleCalendarAPI()
        self.cache = AgentCache(max_size=100, ttl_seconds=300)
        self.graph = self._build_graph()
    
    def _build_graph(self):
        """Build the LangGraph workflow"""
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("parse", self.parse_meeting_details)
        workflow.add_node("validate", self.validate_details)
        workflow.add_node("create_event", self.create_calendar_event)
        workflow.add_node("send_email", self.send_confirmation_email)
        
        # Define edges (flow)
        workflow.set_entry_point("parse")
        workflow.add_edge("parse", "validate")
        workflow.add_edge("validate", "create_event")
        workflow.add_edge("create_event", "send_email")
        workflow.add_edge("send_email", END)
        
        return workflow.compile()
    
    def parse_meeting_details(self, state: AgentState) -> AgentState:
        """Node 1: Parse user input using LLM (with caching)"""
        logger.info("parse_started", user_input=state['user_input'][:100])
        
        # Check cache first
        cached_result = self.cache.get(state['user_input'])
        if cached_result:
            state["meeting_details"] = cached_result
            logger.info("parse_success_from_cache", meeting_title=cached_result.get('title'))
            return state
        
        # Cache miss - call LLM
        prompt = f"""
        Extract meeting details from this request: "{state['user_input']}"
        
        Today's date is: {datetime.now().strftime('%Y-%m-%d')}
        Current time is: {datetime.now().strftime('%H:%M')}
        
        You MUST respond with ONLY valid JSON, nothing else. No explanation, no markdown.
        
        Format:
        {{
            "title": "meeting title or 'Meeting' if not specified",
            "date": "YYYY-MM-DD format",
            "start_time": "HH:MM in 24-hour format",
            "end_time": "HH:MM in 24-hour format (1 hour after start if not specified)",
            "attendee_email": "email@example.com or null",
            "description": "brief description or null"
        }}
        
        Rules:
        - "tomorrow" = add 1 day to today's date
        - "today" = use today's date
        - "2pm" = "14:00"
        - "5pm" = "17:00"
        - If no end time mentioned, add 1 hour to start time
        - If duration mentioned (e.g., "30 minutes"), calculate end time accordingly
        
        Return ONLY the JSON object, nothing else.
        """
        
        try:
            response = self.llm.invoke(prompt)
            content = response.content.strip()
            
            # Remove markdown code blocks if present
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()
            
            # Parse JSON
            meeting_dict = json.loads(content)
            
            # Store in cache
            self.cache.set(state['user_input'], meeting_dict)
            
            state["meeting_details"] = meeting_dict
            logger.info("parse_success_from_llm", meeting_title=meeting_dict.get('title'))
            
        except json.JSONDecodeError as e:
            error = ParseError(state['user_input'], response.content[:200])
            logger.error("parse_failed", error=str(error), llm_response=response.content[:200])
            state["error"] = str(error)
        except Exception as e:
            error = ParseError(state['user_input'])
            logger.error("parse_failed", error=str(e))
            state["error"] = str(error)
        
        return state
    
    def validate_details(self, state: AgentState) -> AgentState:
        """Node 2: Validate parsed details"""
        logger.info("validation_started")
        
        if state.get("error"):
            return state
        
        try:
            details = state["meeting_details"]
            
            # Validate using Pydantic model
            meeting = MeetingDetails(**details)
            
            # Additional validation: end_time after start_time
            start = datetime.strptime(meeting.start_time, "%H:%M")
            end = datetime.strptime(meeting.end_time, "%H:%M")
            
            if end <= start:
                error = ValidationError("end_time", meeting.end_time, "End time must be after start time")
                logger.error("validation_failed", error=str(error))
                state["error"] = str(error)
                return state
            
            logger.info("validation_success", meeting_title=meeting.title, meeting_date=meeting.date)
            
        except Exception as e:
            if "date" in str(e).lower() and "past" in str(e).lower():
                error = ValidationError("date", details.get("date", ""), "Date cannot be in the past")
            else:
                error = ValidationError("unknown", str(details), str(e))
            logger.error("validation_failed", error=str(error))
            state["error"] = str(error)
        
        return state
    
    def create_calendar_event(self, state: AgentState) -> AgentState:
        """Node 3: Create Google Calendar event"""
        logger.info("calendar_event_creation_started")
    
        if state.get("error"):
            return state
    
        try:
            meeting = MeetingDetails(**state["meeting_details"])
            result = self.google_api.create_calendar_event(meeting)
            state["calendar_result"] = result
        
            if result["success"]:
                logger.info("calendar_event_created", event_link=result['event_link'])
            else:
                error = GoogleAPIError("Calendar", "create_event", Exception(result["message"]))
                logger.error("calendar_event_failed", error=str(error))
                state["error"] = str(error)
            
        except Exception as e:
            error = GoogleAPIError("Calendar", "create_event", e)
            logger.error("calendar_event_failed", error=str(error), retries_exhausted=True)
            state["error"] = str(error)
            state["calendar_result"] = {"success": False}
        
        return state
    
    def send_confirmation_email(self, state: AgentState) -> AgentState:
        """Node 4: Send confirmation email"""
        logger.info("email_sending_started", user_email=state["user_email"])
        
        if state.get("error"):
            # Send error email
            logger.warning("sending_error_notification", error=state["error"])
            error_body = f"""
            Failed to schedule your meeting.
            
            Error: {state['error']}
            
            Please try again or contact support.
            """
            result = self.google_api.send_email(
                to=state["user_email"],
                subject="❌ Meeting Scheduling Failed",
                body=error_body
            )
            state["email_result"] = result
            state["final_response"] = {
                "success": False,
                "message": state["error"]
            }
            logger.info("error_notification_sent")
            return state
        
        try:
            calendar_result = state["calendar_result"]
            meeting = state["meeting_details"]
            
            # Success email
            email_body = f"""
            ✅ Your meeting has been scheduled!
            
            Title: {meeting['title']}
            Date: {meeting['date']}
            Time: {meeting['start_time']} - {meeting['end_time']} (IST)
            {f"Attendee: {meeting['attendee_email']}" if meeting.get('attendee_email') else ""}
            
            View in calendar: {calendar_result['event_link']}
            
            Best regards,
            AI Calendar Agent
            """
            
            result = self.google_api.send_email(
                to=state["user_email"],
                subject=f"✅ Meeting Scheduled: {meeting['title']}",
                body=email_body
            )
            
            state["email_result"] = result
            state["final_response"] = {
                "success": True,
                "message": "Meeting scheduled successfully!",
                "event_link": calendar_result['event_link']
            }
            
            logger.info("confirmation_email_sent", meeting_title=meeting['title'])
            
        except Exception as e:
            error = GoogleAPIError("Gmail", "send_email", e)
            logger.error("email_sending_failed", error=str(error))
            state["error"] = str(error)
            state["final_response"] = {
                "success": False,
                "message": f"Event created but email failed: {str(error)}"
            }
        
        return state
    
    def run(self, user_input: str, user_email: str) -> MeetingResponse:
        """Run the agent workflow"""
        logger.info("agent_workflow_started", user_email=user_email)
        
        # Validate and sanitize inputs BEFORE processing
        try:
            sanitized_input, sanitized_email = InputValidator.validate_and_sanitize(
                user_input, 
                user_email
            )
        except ValidationError as e:
            logger.error("input_validation_failed", error=str(e))
            return MeetingResponse(
                success=False,
                message=str(e),
                event_link=None,
                error=str(e)
            )
        
        initial_state = {
            "user_input": sanitized_input,
            "user_email": sanitized_email,
            "meeting_details": {},
            "calendar_result": {},
            "email_result": {},
            "final_response": {},
            "error": ""
        }
        
        # Run the graph
        final_state = self.graph.invoke(initial_state)
        
        success = final_state["final_response"].get("success", False)
        logger.info("agent_workflow_completed", success=success)
        
        return MeetingResponse(**final_state["final_response"])