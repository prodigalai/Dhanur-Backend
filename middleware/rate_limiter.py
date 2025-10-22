import time
import logging
from typing import Dict, Any
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from collections import defaultdict, deque

logger = logging.getLogger(__name__)

class RateLimiter:
    """Production-ready rate limiter with sliding window."""
    
    def __init__(self, requests_per_minute: int = 100):
        self.requests_per_minute = requests_per_minute
        self.requests = defaultdict(lambda: deque())
        self.cleanup_interval = 60  # Clean up old entries every 60 seconds
        self.last_cleanup = time.time()
    
    def is_allowed(self, client_ip: str) -> bool:
        """Check if request is allowed for the given client IP."""
        current_time = time.time()
        
        # Clean up old entries periodically
        if current_time - self.last_cleanup > self.cleanup_interval:
            self._cleanup_old_entries(current_time)
            self.last_cleanup = current_time
        
        # Get client's request history
        client_requests = self.requests[client_ip]
        
        # Remove requests older than 1 minute
        while client_requests and client_requests[0] < current_time - 60:
            client_requests.popleft()
        
        # Check if under rate limit
        if len(client_requests) >= self.requests_per_minute:
            return False
        
        # Add current request
        client_requests.append(current_time)
        return True
    
    def _cleanup_old_entries(self, current_time: float):
        """Clean up old entries to prevent memory leaks."""
        cutoff_time = current_time - 60  # Remove entries older than 1 minute
        
        # Remove clients with no recent requests
        clients_to_remove = []
        for client_ip, requests in self.requests.items():
            # Remove old requests
            while requests and requests[0] < cutoff_time:
                requests.popleft()
            
            # Mark for removal if no recent requests
            if not requests:
                clients_to_remove.append(client_ip)
        
        # Remove empty client entries
        for client_ip in clients_to_remove:
            del self.requests[client_ip]
    
    def get_remaining_requests(self, client_ip: str) -> int:
        """Get remaining requests for the client."""
        current_time = time.time()
        client_requests = self.requests[client_ip]
        
        # Remove old requests
        while client_requests and client_requests[0] < current_time - 60:
            client_requests.popleft()
        
        return max(0, self.requests_per_minute - len(client_requests))
    
    def get_reset_time(self, client_ip: str) -> float:
        """Get time when the rate limit resets for the client."""
        client_requests = self.requests[client_ip]
        if not client_requests:
            return time.time()
        
        # Return time when the oldest request will expire
        return client_requests[0] + 60

# Global rate limiter instance
rate_limiter = RateLimiter()

async def rate_limit_middleware(request: Request, call_next):
    """Rate limiting middleware."""
    try:
        # Get client IP
        client_ip = request.client.host
        if "x-forwarded-for" in request.headers:
            client_ip = request.headers["x-forwarded-for"].split(",")[0].strip()
        
        # Check rate limit
        if not rate_limiter.is_allowed(client_ip):
            remaining = rate_limiter.get_remaining_requests(client_ip)
            reset_time = rate_limiter.get_reset_time(client_ip)
            
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            
            return JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": "Too many requests. Please try again later.",
                        "status_code": 429,
                        "retry_after": int(reset_time - time.time()),
                        "remaining_requests": remaining
                    }
                },
                headers={
                    "Retry-After": str(int(reset_time - time.time())),
                    "X-RateLimit-Limit": str(rate_limiter.requests_per_minute),
                    "X-RateLimit-Remaining": str(remaining),
                    "X-RateLimit-Reset": str(int(reset_time))
                }
            )
        
        # Add rate limit headers to response
        response = await call_next(request)
        
        remaining = rate_limiter.get_remaining_requests(client_ip)
        reset_time = rate_limiter.get_reset_time(client_ip)
        
        response.headers["X-RateLimit-Limit"] = str(rate_limiter.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(reset_time))
        
        return response
        
    except Exception as e:
        logger.error(f"Error in rate limiting middleware: {e}")
        # Don't block requests if rate limiter fails
        return await call_next(request)

