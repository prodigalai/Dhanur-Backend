#!/usr/bin/env python3
"""
Security middleware for Content Crew Prodigal API
"""

import time
import hashlib
from typing import Dict, List, Optional
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import logging

logger = logging.getLogger(__name__)

class SecurityMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.rate_limit_store: Dict[str, List[float]] = {}
        self.max_requests_per_minute = 100
        self.max_requests_per_hour = 1000
        self.blocked_ips: Dict[str, float] = {}
        self.block_duration = 3600  # 1 hour

    async def dispatch(self, request: Request, call_next):
        # Get client IP
        client_ip = self._get_client_ip(request)
        
        # Skip rate limiting for OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            response = await call_next(request)
            self._add_security_headers(response)
            return response
        
        # Check if IP is blocked
        if self._is_ip_blocked(client_ip):
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "IP address temporarily blocked due to excessive requests",
                    "retry_after": int(self.block_duration - (time.time() - self.blocked_ips[client_ip]))
                }
            )

        # Rate limiting
        if not self._check_rate_limit(client_ip):
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Rate limit exceeded. Please try again later.",
                    "retry_after": 60
                }
            )

        # Add security headers
        response = await call_next(request)
        self._add_security_headers(response)
        
        return response

    def _get_client_ip(self, request: Request) -> str:
        """Get real client IP address."""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.client.host

    def _is_ip_blocked(self, client_ip: str) -> bool:
        """Check if IP is blocked."""
        if client_ip in self.blocked_ips:
            if time.time() - self.blocked_ips[client_ip] < self.block_duration:
                return True
            else:
                del self.blocked_ips[client_ip]
        return False

    def _check_rate_limit(self, client_ip: str) -> bool:
        """Check rate limiting for client IP."""
        current_time = time.time()
        
        if client_ip not in self.rate_limit_store:
            self.rate_limit_store[client_ip] = []
        
        # Clean old timestamps
        self.rate_limit_store[client_ip] = [
            ts for ts in self.rate_limit_store[client_ip] 
            if current_time - ts < 3600  # Keep last hour
        ]
        
        # Check minute rate limit
        minute_requests = [
            ts for ts in self.rate_limit_store[client_ip] 
            if current_time - ts < 60
        ]
        
        if len(minute_requests) >= self.max_requests_per_minute:
            self.blocked_ips[client_ip] = current_time
            logger.warning(f"IP {client_ip} blocked due to rate limit violation")
            return False
        
        # Check hour rate limit
        if len(self.rate_limit_store[client_ip]) >= self.max_requests_per_hour:
            self.blocked_ips[client_ip] = current_time
            logger.warning(f"IP {client_ip} blocked due to hourly rate limit violation")
            return False
        
        # Add current request
        self.rate_limit_store[client_ip].append(current_time)
        return True

    def _add_security_headers(self, response):
        """Add security headers to response."""
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

class RequestValidationMiddleware(BaseHTTPMiddleware):
    """Middleware for request validation and sanitization."""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.max_content_length = 10 * 1024 * 1024  # 10MB
        self.blocked_user_agents = [
            "bot", "crawler", "spider", "scraper", "curl", "wget", "python"
        ]

    async def dispatch(self, request: Request, call_next):
        # Check content length
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_content_length:
            return JSONResponse(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                content={
                    "detail": "Request content too large",
                    "max_size_mb": self.max_content_length // (1024 * 1024)
                }
            )

        # Check user agent
        user_agent = request.headers.get("user-agent", "").lower()
        if any(blocked in user_agent for blocked in self.blocked_user_agents):
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "detail": "Access denied for automated tools"
                }
            )

        # Validate request path
        if not self._is_valid_path(request.url.path):
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "detail": "Invalid API endpoint"
                }
            )

        response = await call_next(request)
        return response

    def _is_valid_path(self, path: str) -> bool:
        """Validate API path."""
        valid_paths = [
            "/auth/", "/health", "/brand/", "/organization/", 
            "/project/", "/scheduled-posts/", "/users/", "/oauth/",
            "/api/reviews/", "/api/assets/", "/api/", "/docs", "/openapi.json"
        ]
        return any(path.startswith(valid_path) for valid_path in valid_paths)
