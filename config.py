import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LANGCHAIN_TRACING_V2 = os.getenv("LANGCHAIN_TRACING_V2", "false")
LANGCHAIN_ENDPOINT = os.getenv("LANGCHAIN_ENDPOINT")
LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY")
LANGCHAIN_PROJECT = os.getenv("LANGCHAIN_PROJECT", "ai-calendar-agent")

GOOGLE_SCOPES =  [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/gmail.send'
]

CLIENT_SECRET_FILE = 'client_secret.json'
TOKEN_FILE = 'token.json'

if not OPENAI_API_KEY:
    raise ValueError ("OPENAI_API_KEY not found in .env file")

print("Config Loaded")