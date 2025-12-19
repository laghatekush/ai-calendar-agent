"""Custom exceptions for AI Calendar Agent"""


class CalendarAgentError(Exception):
    """Base exception for all agent errors"""
    pass


class ParseError(CalendarAgentError):
    """Error parsing user input with LLM"""
    def __init__(self, user_input: str, llm_response: str = None):
        self.user_input = user_input
        self.llm_response = llm_response
        super().__init__(f"Failed to parse meeting details from: '{user_input[:50]}...'")


class ValidationError(CalendarAgentError):
    """Error validating meeting details"""
    def __init__(self, field: str, value: str, reason: str):
        self.field = field
        self.value = value
        self.reason = reason
        super().__init__(f"Validation failed for {field}='{value}': {reason}")


class GoogleAPIError(CalendarAgentError):
    """Error calling Google Calendar or Gmail API"""
    def __init__(self, api_name: str, operation: str, original_error: Exception):
        self.api_name = api_name
        self.operation = operation
        self.original_error = original_error
        super().__init__(f"{api_name} {operation} failed: {str(original_error)}")


class AuthenticationError(CalendarAgentError):
    """Error with Google authentication"""
    def __init__(self, message: str = "Failed to authenticate with Google"):
        super().__init__(message)


class RateLimitError(CalendarAgentError):
    """Rate limit exceeded"""
    def __init__(self, retry_after: int = None):
        self.retry_after = retry_after
        msg = "Rate limit exceeded"
        if retry_after:
            msg += f", retry after {retry_after} seconds"
        super().__init__(msg)