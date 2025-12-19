from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from email.mime.text import MIMEText
import base64
import os
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
        """Get or refresh Google credentials"""
        creds = None

        if os.path.exists(TOKEN_FILE):
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, GOOGLE_SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    CLIENT_SECRET_FILE,
                    GOOGLE_SCOPES
                )
                creds = flow.run_local_server(port=0)

            with open(TOKEN_FILE, 'w') as token:
                token.write(creds.to_json())

        return creds

    @retry(
        stop=stop_after_attempt(3),  # Try 3 times
        wait=wait_exponential(multiplier=1, min=2, max=10),  # Wait 2s, 4s, 8s
        retry=retry_if_exception_type(Exception),  # Retry on any error
        reraise=True  # Raise error after all retries fail
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
            raise  # Let tenacity handle the retry

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
            raise  # Let tenacity handle the retry