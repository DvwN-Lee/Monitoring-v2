# auth-service/errors.py
from typing import Optional
from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Standardized error response schema."""
    status: str = "error"
    code: str  # Error code (e.g., "AUTH_FAILED", "NOT_FOUND", "VALIDATION_ERROR")
    message: str  # Human-readable message
    details: Optional[dict] = None  # Additional error details


# Common error codes
class ErrorCode:
    # Authentication & Authorization
    AUTH_FAILED = "AUTH_FAILED"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    TOKEN_INVALID = "TOKEN_INVALID"
    UNAUTHORIZED = "UNAUTHORIZED"
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"

    # Resource errors
    NOT_FOUND = "NOT_FOUND"
    USER_NOT_FOUND = "USER_NOT_FOUND"

    # Validation errors
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_INPUT = "INVALID_INPUT"

    # Server errors
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    DATABASE_ERROR = "DATABASE_ERROR"
