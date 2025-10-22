#!/usr/bin/env python3
"""
Error handling utilities for Content Crew Prodigal API
"""

import logging
import traceback
from typing import Dict, Any, Optional
from fastapi import HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.requests import Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)

class ContentCrewException(Exception):
    """Base exception for Content Crew API."""
    def __init__(self, message: str, error_code: str = None, status_code: int = 500):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        super().__init__(self.message)

class ValidationException(ContentCrewException):
    """Validation error exception."""
    def __init__(self, message: str, field: str = None):
        super().__init__(message, "VALIDATION_ERROR", 422)
        self.field = field

class AuthenticationException(ContentCrewException):
    """Authentication error exception."""
    def __init__(self, message: str):
        super().__init__(message, "AUTHENTICATION_ERROR", 401)

class AuthorizationException(ContentCrewException):
    """Authorization error exception."""
    def __init__(self, message: str):
        super().__init__(message, "AUTHORIZATION_ERROR", 403)

class ResourceNotFoundException(ContentCrewException):
    """Resource not found exception."""
    def __init__(self, resource_type: str, resource_id: str = None):
        message = f"{resource_type} not found"
        if resource_id:
            message += f" with ID: {resource_id}"
        super().__init__(message, "RESOURCE_NOT_FOUND", 404)

class ConflictException(ContentCrewException):
    """Resource conflict exception."""
    def __init__(self, message: str):
        super().__init__(message, "CONFLICT_ERROR", 409)

class RateLimitException(ContentCrewException):
    """Rate limit exceeded exception."""
    def __init__(self, retry_after: int = 60):
        super().__init__("Rate limit exceeded", "RATE_LIMIT_ERROR", 429)
        self.retry_after = retry_after

class DatabaseException(ContentCrewException):
    """Database operation exception."""
    def __init__(self, message: str, operation: str = None):
        super().__init__(message, "DATABASE_ERROR", 500)
        self.operation = operation

class ExternalServiceException(ContentCrewException):
    """External service exception."""
    def __init__(self, service_name: str, message: str):
        super().__init__(f"{service_name} service error: {message}", "EXTERNAL_SERVICE_ERROR", 502)

def create_error_response(
    status_code: int,
    message: str,
    error_code: str = None,
    details: Dict[str, Any] = None,
    request_id: str = None
) -> Dict[str, Any]:
    """Create standardized error response."""
    error_response = {
        "success": False,
        "error": {
            "code": error_code or f"HTTP_{status_code}",
            "message": message,
            "status_code": status_code
        }
    }
    
    if details:
        error_response["error"]["details"] = details
    
    if request_id:
        error_response["error"]["request_id"] = request_id
    
    return error_response

def log_error(error: Exception, request: Request = None, context: Dict[str, Any] = None):
    """Log error with context."""
    error_context = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "traceback": traceback.format_exc()
    }
    
    if request:
        error_context.update({
            "method": request.method,
            "url": str(request.url),
            "client_ip": request.client.host if request.client else "unknown",
            "user_agent": request.headers.get("user-agent", "unknown")
        })
    
    if context:
        error_context.update(context)
    
    logger.error(f"API Error: {error_context}")

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors."""
    errors = []
    for error in exc.errors():
        field = " -> ".join(str(loc) for loc in error["loc"])
        errors.append({
            "field": field,
            "message": error["msg"],
            "type": error["type"],
            "input": error.get("input")
        })
    
    error_response = create_error_response(
        status_code=422,
        message="Validation error",
        error_code="VALIDATION_ERROR",
        details={"validation_errors": errors}
    )
    
    log_error(exc, request, {"validation_errors": errors})
    return JSONResponse(status_code=422, content=error_response)

async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    error_response = create_error_response(
        status_code=exc.status_code,
        message=exc.detail,
        error_code=f"HTTP_{exc.status_code}"
    )
    
    log_error(exc, request)
    return JSONResponse(status_code=exc.status_code, content=error_response)

async def content_crew_exception_handler(request: Request, exc: ContentCrewException):
    """Handle custom Content Crew exceptions."""
    error_response = create_error_response(
        status_code=exc.status_code,
        message=exc.message,
        error_code=exc.error_code
    )
    
    log_error(exc, request)
    return JSONResponse(status_code=exc.status_code, content=error_response)

async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    error_response = create_error_response(
        status_code=500,
        message="Internal server error",
        error_code="INTERNAL_SERVER_ERROR"
    )
    
    log_error(exc, request)
    return JSONResponse(status_code=500, content=error_response)

def setup_exception_handlers(app):
    """Setup all exception handlers."""
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(ContentCrewException, content_crew_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
