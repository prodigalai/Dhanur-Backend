import logging
import traceback
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from typing import Dict, Any

logger = logging.getLogger(__name__)

class ProductionErrorHandler:
    """Production-ready error handler for the API."""
    
    @staticmethod
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        """Handle HTTP exceptions with proper logging and user-friendly messages."""
        try:
            # Log the error
            logger.error(f"HTTP Exception: {exc.status_code} - {exc.detail} - Path: {request.url.path}")
            
            # Create user-friendly error response
            error_response = {
                "success": False,
                "error": {
                    "code": "HTTP_ERROR",
                    "message": exc.detail,
                    "status_code": exc.status_code,
                    "path": str(request.url.path)
                },
                "timestamp": None  # Will be set by middleware
            }
            
            # Add additional context for specific error types
            if exc.status_code == 404:
                error_response["error"]["message"] = "Resource not found"
            elif exc.status_code == 403:
                error_response["error"]["message"] = "Access denied"
            elif exc.status_code == 401:
                error_response["error"]["message"] = "Authentication required"
            elif exc.status_code == 400:
                # Keep the original error message for 400 errors
                error_response["error"]["message"] = exc.detail
            elif exc.status_code >= 500:
                error_response["error"]["message"] = "Internal server error"
            
            return JSONResponse(
                status_code=exc.status_code,
                content=error_response
            )
            
        except Exception as e:
            logger.error(f"Error in HTTP exception handler: {e}")
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": {
                        "code": "HANDLER_ERROR",
                        "message": "An error occurred while processing your request",
                        "status_code": 500
                    }
                }
            )
    
    @staticmethod
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        """Handle validation errors with detailed field information."""
        try:
            logger.error(f"Validation Error: {exc.errors()} - Path: {request.url.path}")
            
            # Extract field errors
            field_errors = []
            for error in exc.errors():
                field_path = " -> ".join(str(loc) for loc in error["loc"])
                field_errors.append({
                    "field": field_path,
                    "message": error["msg"],
                    "type": error["type"]
                })
            
            error_response = {
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request validation failed",
                    "status_code": 422,
                    "field_errors": field_errors,
                    "path": str(request.url.path)
                }
            }
            
            return JSONResponse(
                status_code=422,
                content=error_response
            )
            
        except Exception as e:
            logger.error(f"Error in validation exception handler: {e}")
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": {
                        "code": "HANDLER_ERROR",
                        "message": "An error occurred while processing your request",
                        "status_code": 500
                    }
                }
            )
    
    @staticmethod
    async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Handle general exceptions with proper logging."""
        try:
            # Log the full error with traceback
            logger.error(f"Unhandled Exception: {str(exc)} - Path: {request.url.path}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Create safe error response (don't expose internal details)
            error_response = {
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred. Please try again later.",
                    "status_code": 500,
                    "path": str(request.url.path)
                }
            }
            
            return JSONResponse(
                status_code=500,
                content=error_response
            )
            
        except Exception as e:
            logger.error(f"Error in general exception handler: {e}")
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": {
                        "code": "CRITICAL_ERROR",
                        "message": "A critical error occurred",
                        "status_code": 500
                    }
                }
            )

def setup_error_handlers(app):
    """Setup all error handlers for the FastAPI app."""
    app.add_exception_handler(HTTPException, ProductionErrorHandler.http_exception_handler)
    app.add_exception_handler(RequestValidationError, ProductionErrorHandler.validation_exception_handler)
    app.add_exception_handler(Exception, ProductionErrorHandler.general_exception_handler)

