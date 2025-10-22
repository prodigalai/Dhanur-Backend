#!/usr/bin/env python3
"""
Logging middleware for Content Crew Prodigal API
Production-ready request/response logging
"""

import time
import logging
import json
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from typing import Dict, Any

logger = logging.getLogger(__name__)

class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for comprehensive request/response logging."""
    
    async def dispatch(self, request: Request, call_next):
        # Log request
        start_time = time.time()
        self._log_request(request)
        
        # Process request
        response = await call_next(request)
        
        # Calculate process time
        process_time = time.time() - start_time
        
        # Log response
        self._log_response(request, response, process_time)
        
        return response
    
    def _log_request(self, request: Request):
        """Log incoming request details."""
        try:
            # Get client IP
            client_ip = self._get_client_ip(request)
            
            # Get user agent
            user_agent = request.headers.get("user-agent", "Unknown")
            
            # Get request body size (if available)
            content_length = request.headers.get("content-length", 0)
            
            # Log request
            logger.info(
                f"REQUEST: {request.method} {request.url.path} | "
                f"IP: {client_ip} | "
                f"User-Agent: {user_agent[:100]} | "
                f"Content-Length: {content_length} | "
                f"Query: {dict(request.query_params)}"
            )
            
        except Exception as e:
            logger.error(f"Error logging request: {e}")
    
    def _log_response(self, request: Request, response: Response, process_time: float):
        """Log response details."""
        try:
            # Get client IP
            client_ip = self._get_client_ip(request)
            
            # Get response status
            status_code = response.status_code
            
            # Get response size
            response_size = len(response.body) if hasattr(response, 'body') else 0
            
            # Determine log level based on status code
            if status_code >= 500:
                log_level = "ERROR"
            elif status_code >= 400:
                log_level = "WARNING"
            else:
                log_level = "INFO"
            
            # Log response
            log_message = (
                f"RESPONSE: {request.method} {request.url.path} | "
                f"Status: {status_code} | "
                f"IP: {client_ip} | "
                f"Process Time: {process_time:.3f}s | "
                f"Response Size: {response_size} bytes"
            )
            
            if log_level == "ERROR":
                logger.error(log_message)
            elif log_level == "WARNING":
                logger.warning(log_message)
            else:
                logger.info(log_message)
                
        except Exception as e:
            logger.error(f"Error logging response: {e}")
    
    def _get_client_ip(self, request: Request) -> str:
        """Get real client IP address."""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.client.host if request.client else "Unknown"
    
    def _sanitize_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize sensitive data before logging."""
        sensitive_fields = ['password', 'token', 'secret', 'key', 'authorization']
        sanitized = data.copy()
        
        for field in sensitive_fields:
            if field in sanitized:
                sanitized[field] = "***REDACTED***"
        
        return sanitized

