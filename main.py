#!/usr/bin/env python3
"""
Content Crew Prodigal - Production-Ready Backend API
"""

import os
import logging
from datetime import datetime, timezone
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles

from routes.mongodb_routes import router as mongodb_router
from routes.auth_routes import router as auth_router
from routes.route import router as main_router
from routes.tts_routes import router as tts_router
from routes.chat_routes import router as chat_router
from routes.elevenlabs_routes import router as elevenlabs_router
from routes.team_management_routes import router as team_management_router
from routes.asset_management_routes import router as asset_management_router
from routes.review_management_routes import router as review_management_router
from middleware.security import SecurityMiddleware
from middleware.logging import LoggingMiddleware
from middleware.error_handler import setup_error_handlers
from middleware.rate_limiter import rate_limit_middleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Content Crew Prodigal API",
    description="Production-ready backend API for Content Crew Prodigal platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Add production middleware
app.add_middleware(SecurityMiddleware)
app.add_middleware(LoggingMiddleware)

# Add rate limiting middleware
app.middleware("http")(rate_limit_middleware)

# Add GZip compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Configure CORS with proper preflight handling
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8080,http://127.0.0.1:3000,http://127.0.0.1:8080,https://dhanur-frontend-nu.vercel.app,https://dhanur-ai-dashboard-omega.vercel.app").split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"],
    allow_headers=["*", "Authorization", "Content-Type", "Accept", "Origin", "X-Requested-With"],
    expose_headers=["*"],
    max_age=86400,  # Cache preflight for 24 hours
)

# Setup production error handlers
setup_error_handlers(app)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Global OPTIONS handler for CORS preflight
@app.options("/{full_path:path}")
async def options_handler(full_path: str):
    """Handle OPTIONS requests for CORS preflight."""
    return {"message": "OK"}

# Include MongoDB routes
app.include_router(mongodb_router, tags=["MongoDB API"])

# Include Authentication routes first (to avoid conflicts)
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])

# Include main routes (contains auth/create-entity and other endpoints)
app.include_router(main_router, tags=["Main Routes"])

# Include TTS routes
app.include_router(tts_router, tags=["TTS - Text to Speech"])

# Include Chat routes
app.include_router(chat_router, prefix="/chat", tags=["Chat System"])

# Include ElevenLabs routes
app.include_router(elevenlabs_router, prefix="/api/v2/elevenlabs", tags=["ElevenLabs AI Voice"])

# Include Team Management routes
app.include_router(team_management_router, prefix="/api/v2", tags=["Team Management"])

# Include Asset Management routes
app.include_router(asset_management_router, prefix="/api", tags=["Asset Management"])

# Include Review Management routes
app.include_router(review_management_router, tags=["Review Management"])

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Content Crew Prodigal API",
        "version": "1.0.0",
        "status": "production-ready",
        "docs": "/docs",
        "health": "/health",
        "features": [
            "Enhanced Authentication & Authorization",
            "User Management with Credit System",
            "MongoDB Database Integration",
            "TTS (Text-to-Speech) Integration",
            "ElevenLabs AI Voice Integration",
            "Audio Storage & Management",
            "User Credits Management",
            "Login Bonus System",
            "Rate Limiting",
            "Security Headers",
            "Comprehensive Error Handling",
            "Production Logging"
        ]
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0",
        "database": "MongoDB"
    }

@app.get("/health/db")
async def database_health_check():
    """Database health check endpoint."""
    from services.mongodb_service import mongodb_service
    return mongodb_service.test_connection()

@app.get("/api/v2/health/oauth")
async def oauth_health_check():
    """OAuth system health check."""
    return {
        "status": "healthy",
        "oauth_system": "enhanced",
        "features": [
            "User Registration",
            "User Login",
            "Spotify OAuth Integration",
            "OAuth Account Linking",
            "Token Management",
            "Database Storage"
        ]
    }

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add process time header to responses."""
    import time
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

@app.middleware("http")
async def add_request_id_header(request: Request, call_next):
    """Add request ID header to responses."""
    import uuid
    request_id = str(uuid.uuid4())
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response

if __name__ == "__main__":
    import uvicorn
    
    # Get port from environment or default to 8080
    port = int(os.getenv("PORT", 8080))
    
    print(f"🚀 Starting Content Crew Prodigal API on port {port}")
    print(f"📚 API Documentation: http://localhost:{port}/docs")
    print(f"🔍 Health Check: http://localhost:{port}/health")
    print(f"🔒 Security Features: Rate limiting, Security headers, Input validation")
    print(f"📊 Error Handling: Comprehensive error responses with logging")
    print(f"🆔 ID Format: UUID strings (like MongoDB ObjectId)")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        access_log=True
    )
