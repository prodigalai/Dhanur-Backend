#!/usr/bin/env python3
"""
MongoDB Database Service for Content Crew Prodigal
Primary database service using MongoDB only
"""

import os
import logging
from typing import Dict, Any
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# MongoDB connection details
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb+srv://ashwini:Ashwini1234@cluster0.lyeisj1.mongodb.net/Dhanur-AI")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "Dhanur-AI")

class MongoDBService:
    """MongoDB service for database operations."""
    
    def __init__(self):
        self.mongo_url = MONGODB_URL
        self.database_name = MONGODB_DATABASE
        self.client = None
        self.db = None
        
        try:
            self.client = MongoClient(self.mongo_url)
            self.db: Database = self.client[self.database_name]
            
            # Test connection
            self.client.admin.command('ping')
            logger.info(f"MongoDB connected successfully to {self.database_name}")
            
        except Exception as e:
            logger.error(f"MongoDB connection failed: {str(e)}")
            self.client = None
            self.db = None
    
    def is_connected(self) -> bool:
        """Check if MongoDB is connected."""
        try:
            if self.client:
                self.client.admin.command('ping')
                return True
        except Exception:
            pass
        return False
    
    def get_collection(self, collection_name: str) -> Collection:
        """Get a MongoDB collection."""
        if not self.is_connected():
            raise Exception("MongoDB not connected")
        return self.db[collection_name]
    
    def get_database_info(self) -> Dict[str, Any]:
        """Get database connection information."""
        return {
            "database_type": "MongoDB",
            "url": self.mongo_url,
            "database": self.database_name,
            "connected": self.is_connected()
        }
    
    def test_connection(self) -> Dict[str, Any]:
        """Test database connection."""
        try:
            if self.is_connected():
                # Get database stats
                stats = self.db.command("dbStats")
                return {
                    "status": "success",
                    "message": "MongoDB connection successful",
                    "database_type": "MongoDB",
                    "database": self.database_name,
                    "collections": stats.get("collections", 0),
                    "data_size": stats.get("dataSize", 0),
                    "storage_size": stats.get("storageSize", 0)
                }
            else:
                return {
                    "status": "error",
                    "message": "MongoDB connection failed",
                    "database_type": "MongoDB",
                    "database": self.database_name
                }
        except Exception as e:
            return {
                "status": "error",
                "message": f"MongoDB connection failed: {str(e)}",
                "database_type": "MongoDB",
                "database": self.database_name
            }
    
    def close_connection(self):
        """Close MongoDB connection."""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")

# Create singleton instance
mongodb_service = MongoDBService()

# Legacy compatibility functions
def get_database_session():
    """Legacy function for compatibility - returns MongoDB service."""
    return mongodb_service

def test_database_connection() -> Dict[str, Any]:
    """Test database connection."""
    return mongodb_service.test_connection()

def get_database_info() -> Dict[str, Any]:
    """Get database information."""
    return mongodb_service.get_database_info()
