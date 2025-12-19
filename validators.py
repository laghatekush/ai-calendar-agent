"""Input validation and sanitization"""

import re
from typing import Tuple
from exceptions import ValidationError


class InputValidator:
    """Validate and sanitize user inputs"""
    
    # Common prompt injection patterns
    PROMPT_INJECTION_PATTERNS = [
        r"ignore\s+(previous|all|above)",
        r"system\s*:",
        r"<\s*script",
        r"javascript\s*:",
        r"disregard",
        r"forget\s+(everything|instructions)",
        r"new\s+instructions",
        r"admin\s+mode"
    ]
    
    # Email validation regex
    EMAIL_PATTERN = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    @staticmethod
    def sanitize_user_input(user_input: str) -> str:
        """
        Sanitize user input to prevent injection attacks
        
        Args:
            user_input: Raw user input
            
        Returns:
            Sanitized input
            
        Raises:
            ValidationError: If input contains malicious patterns
        """
        # Check length
        if len(user_input) > 500:
            raise ValidationError(
                "user_input",
                user_input[:50],
                "Input too long (max 500 characters)"
            )
        
        if len(user_input.strip()) == 0:
            raise ValidationError(
                "user_input",
                "",
                "Input cannot be empty"
            )
        
        # Check for prompt injection patterns
        lower_input = user_input.lower()
        for pattern in InputValidator.PROMPT_INJECTION_PATTERNS:
            if re.search(pattern, lower_input, re.IGNORECASE):
                raise ValidationError(
                    "user_input",
                    user_input[:50],
                    "Input contains potentially malicious content"
                )
        
        # Remove any HTML/script tags
        sanitized = re.sub(r'<[^>]*>', '', user_input)
        
        # Remove excessive whitespace
        sanitized = ' '.join(sanitized.split())
        
        return sanitized
    
    @staticmethod
    def validate_email(email: str) -> str:
        """
        Validate and sanitize email address
        
        Args:
            email: Email address to validate
            
        Returns:
            Sanitized email
            
        Raises:
            ValidationError: If email is invalid
        """
        # Strip whitespace
        email = email.strip().lower()
        
        # Check format
        if not re.match(InputValidator.EMAIL_PATTERN, email):
            raise ValidationError(
                "email",
                email,
                "Invalid email format"
            )
        
        # Check length
        if len(email) > 254:  # RFC 5321
            raise ValidationError(
                "email",
                email[:50],
                "Email too long"
            )
        
        return email
    
    @staticmethod
    def validate_and_sanitize(user_input: str, user_email: str) -> Tuple[str, str]:
        """
        Validate and sanitize both inputs
        
        Args:
            user_input: Meeting request
            user_email: User email
            
        Returns:
            Tuple of (sanitized_input, sanitized_email)
            
        Raises:
            ValidationError: If validation fails
        """
        sanitized_input = InputValidator.sanitize_user_input(user_input)
        sanitized_email = InputValidator.validate_email(user_email)
        
        return sanitized_input, sanitized_email