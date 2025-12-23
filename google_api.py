from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from email.mime.text import MIMEText
import base64
import os
import json
from config import GOOGLE_SCOPES, CLIENT_SECRET_FILE, TOKEN_FILE
from models import MeetingDetails
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type


class GoogleCalendarAPI:
    """Handles Google Calendar and Gmail operations"""

    def __init__(self):
        self.creds = self._get_credentials()
        self.calendar_service = build('calendar', 'v3', credentials=self.creds)
        self.gmail_service = build('gmail', 'v1', credentials=self.creds)

    def _get_credentials(self):
        """Get or refresh Google credentials (works locally and in production)"""
        creds = None
        
        # PRODUCTION: Try environment variables first
        if os.getenv('GOOGLE_TOKEN'):
            print("📍 Using Google credentials from environment variables")
            token_data = json.loads(os.getenv('GOOGLE_TOKEN'))
            creds = Credentials.from_authorized_user_info(token_data, GOOGLE_SCOPES)
        
        # LOCAL: Try token.json file
        elif os.path.exists(TOKEN_FILE):
            print("📍 Using Google credentials from token.json file")
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, GOOGLE_SCOPES)
        
        # Refresh if expired
        if creds and creds.expired and creds.refresh_token:
            print("🔄 Refreshing expired credentials")
            creds.refresh(Request())
            
            # Save refreshed token (only works locally)
            if not os.getenv('GOOGLE_TOKEN') and os.path.exists(TOKEN_FILE):
                with open(TOKEN_FILE, 'w') as token:
                    token.write(creds.to_json())
        
        # If no valid credentials, need to authenticate
        if not creds or not creds.valid:
            print("⚠️ No valid credentials found")
            
            # PRODUCTION: Use client secret from env var
            if os.getenv('GOOGLE_CLIENT_SECRET'):
                print("📍 Authenticating with client secret from environment")
                client_config = json.loads(os.getenv('GOOGLE_CLIENT_SECRET'))
                flow = InstalledAppFlow.from_client_config(client_config, GOOGLE_SCOPES)
            
            # LOCAL: Use client_secret.json file
            elif os.path.exists(CLIENT_SECRET_FILE):
                print("📍 Authenticating with client_secret.json file")
                flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, GOOGLE_SCOPES)
            
            else:
                raise Exception("No Google credentials found. Please set GOOGLE_TOKEN and GOOGLE_CLIENT_SECRET environment variables for production, or ensure client_secret.json exists locally.")
            
            # This will open browser (only works locally)
            creds = flow.run_local_server(port=0)
            
            # Save credentials (only works locally)
            if not os.getenv('GOOGLE_TOKEN'):
                with open(TOKEN_FILE, 'w') as token:
                    token.write(creds.to_json())
        
        print("✅ Google credentials loaded successfully")
        return creds

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True
    )
    def create_calendar_event(self, meeting: MeetingDetails) -> dict:
        """Create a Google Calendar event with automatic retries"""
        print(f"🔄 Attempting to create calendar event (will retry up to 3 times)...")
        
        try:
            event = {
                "summary": meeting.title,
                "description": meeting.description or "",
                "start": {
                    "dateTime": f"{meeting.date}T{meeting.start_time}:00",
                    "timeZone": "Asia/Kolkata",
                },
                "end": {
                    "dateTime": f"{meeting.date}T{meeting.end_time}:00",
                    "timeZone": "Asia/Kolkata",
                },
            }

            if meeting.attendee_email:
                event["attendees"] = [{"email": meeting.attendee_email}]

            created_event = self.calendar_service.events().insert(
                calendarId="primary",
                body=event,
                sendUpdates="all"
            ).execute()

            print(f"✅ Calendar event created successfully")

            return {
                "success": True,
                "event_id": created_event["id"],
                "event_link": created_event.get("htmlLink"),
                "message": f"Meeting '{meeting.title}' scheduled successfully"
            }

        except Exception as e:
            print(f"❌ Calendar API error (will retry): {str(e)}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True
    )
    def send_email(self, to: str, subject: str, body: str) -> dict:
        """Send an email via Gmail with automatic retries"""
        print(f"🔄 Attempting to send email (will retry up to 3 times)...")
        
        try:
            message = MIMEText(body)
            message["to"] = to
            message["subject"] = subject

            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

            send_message = self.gmail_service.users().messages().send(
                userId="me",
                body={"raw": raw}
            ).execute()

            print(f"✅ Email sent successfully")

            return {
                "success": True,
                "message_id": send_message["id"],
                "message": f"Email sent to {to}"
            }

        except Exception as e:
            print(f"❌ Gmail API error (will retry): {str(e)}")
            raise