#!/usr/bin/env python3
"""
MongoDB-Compatible API routes for Content Crew Prodigal
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional
import logging
from datetime import datetime
import os

from services.mongodb_service import mongodb_service
from middleware.auth import get_current_user

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "database": "MongoDB"
    }

@router.get("/health/db")
async def database_health_check():
    """Database health check endpoint."""
    return mongodb_service.test_connection()

@router.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Content Crew Prodigal API - MongoDB Edition",
        "version": "1.0.0",
        "status": "production-ready",
        "database": "MongoDB",
        "features": [
            "MongoDB Database Integration",
            "TTS (Text-to-Speech) Integration", 
            "Audio Storage & Management",
            "User Authentication",
            "Rate Limiting",
            "Security Headers",
            "Comprehensive Error Handling",
            "Production Logging"
        ]
    }

# MongoDB-specific endpoints
@router.get("/collections")
async def get_collections():
    """Get all MongoDB collections."""
    try:
        if not mongodb_service.is_connected():
            raise HTTPException(status_code=503, detail="MongoDB not connected")
        
        collections = mongodb_service.db.list_collection_names()
        return {
            "success": True,
            "collections": collections,
            "count": len(collections)
        }
    except Exception as e:
        logger.error(f"Failed to get collections: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get collections: {str(e)}")

@router.get("/collections/{collection_name}/stats")
async def get_collection_stats(collection_name: str):
    """Get statistics for a specific collection."""
    try:
        if not mongodb_service.is_connected():
            raise HTTPException(status_code=503, detail="MongoDB not connected")
        
        collection = mongodb_service.get_collection(collection_name)
        stats = mongodb_service.db.command("collStats", collection_name)
        
        return {
            "success": True,
            "collection": collection_name,
            "stats": {
                "count": stats.get("count", 0),
                "size": stats.get("size", 0),
                "storage_size": stats.get("storageSize", 0),
                "avg_obj_size": stats.get("avgObjSize", 0),
                "indexes": stats.get("nindexes", 0)
            }
        }
    except Exception as e:
        logger.error(f"Failed to get collection stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get collection stats: {str(e)}")

@router.get("/database/info")
async def get_database_info():
    """Get database information."""
    try:
        return mongodb_service.get_database_info()
    except Exception as e:
        logger.error(f"Failed to get database info: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get database info: {str(e)}")

# Legacy compatibility endpoints
@router.get("/api/health")
async def api_health():
    """API health check."""
    return {
        "status": "healthy",
        "api": "Content Crew Prodigal",
        "database": "MongoDB",
        "timestamp": datetime.utcnow().isoformat()
    }

@router.get("/api/status")
async def api_status():
    """API status endpoint."""
    return {
        "service": "Content Crew Prodigal API",
        "status": "operational",
        "database": "MongoDB",
        "version": "1.0.0",
        "features": [
            "MongoDB Integration",
            "TTS Audio Generation",
            "Audio Storage",
            "User Management",
            "Authentication",
            "Health Monitoring"
        ],
        "timestamp": datetime.utcnow().isoformat()
    }
