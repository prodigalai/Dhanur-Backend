#!/usr/bin/env python3
"""
Content Crew Prodigal - Cloudflare Workers Compatible API
"""

import os
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from routes.enhanced_oauth_routes import router as enhanced_oauth_router
from routes.route import router as main_router
from middleware.security import SecurityMiddleware
from middleware.logging import LoggingMiddleware
from utils.error_handler import setup_exception_handlers

# Configure logging for Cloudflare
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Content Crew Prodigal API",
    description="Cloudflare Workers compatible backend API for Content Crew Prodigal platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Add security middleware
app.add_middleware(LoggingMiddleware)

# Add GZip compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Configure CORS for Cloudflare
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "https://yourdomain.com,https://api.yourdomain.com,https://597a8618a9f8.ngrok.app").split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"],
    allow_headers=["*", "Authorization", "Content-Type", "Accept", "Origin", "X-Requested-With"],
    expose_headers=["*"],
    max_age=86400,  # Cache preflight for 24 hours
)

# Setup exception handlers
setup_exception_handlers(app)

# Global OPTIONS handler for CORS preflight
@app.options("/{full_path:path}")
async def options_handler(full_path: str):
    """Handle OPTIONS requests for CORS preflight."""
    return {"message": "OK"}

# Include enhanced OAuth routes
app.include_router(enhanced_oauth_router, prefix="/api/v2", tags=["Enhanced OAuth"])

# Include main routes (authentication, etc.)
app.include_router(main_router, tags=["Main API"])

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Content Crew Prodigal API",
        "version": "1.0.0",
        "status": "cloudflare-workers-ready",
        "deployment": "Cloudflare Workers",
        "docs": "/docs",
        "health": "/health",
        "features": [
            "Enhanced Authentication & Authorization",
            "User Management with OAuth Integration",
            "Organization Management",
            "Brand Management",
            "Project Management",
            "Scheduled Posts",
            "Enhanced OAuth Integration",
            "Rate Limiting",
            "Security Headers",
            "Comprehensive Error Handling",
            "Cloudflare Workers Optimized"
        ]
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": "2024-01-01T00:00:00Z",
        "version": "1.0.0",
        "deployment": "cloudflare-workers"
    }

@app.get("/api/v2/health/oauth")
async def oauth_health_check():
    """OAuth system health check."""
    return {
        "status": "healthy",
        "oauth_providers": ["spotify", "linkedin", "youtube"],
        "timestamp": "2024-01-01T00:00:00Z"
    }

# Cloudflare Workers entry point
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
