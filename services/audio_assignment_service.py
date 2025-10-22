#!/usr/bin/env python3
"""
Audio Assignment Service
Manages audio assignments to brands and campaigns
"""

import os
import secrets
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection
import logging

logger = logging.getLogger(__name__)

class AudioAssignmentService:
    """Service for managing audio assignments to brands and campaigns."""
    
    def __init__(self):
        self.mongo_url = os.getenv("MONGODB_URL", "mongodb+srv://ashwini:Ashwini1234@cluster0.lyeisj1.mongodb.net/Dhanur-AI")
        self.database_name = os.getenv("MONGODB_DATABASE", "Dhanur-AI")
        self.assignments_collection_name = "audio_campaign_assignments"
        
        try:
            self.client = MongoClient(self.mongo_url)
            self.db: Database = self.client[self.database_name]
            self.assignments_collection: Collection = self.db[self.assignments_collection_name]
            
            # Create indexes for better performance
            self.assignments_collection.create_index("assignment_id", unique=True)
            self.assignments_collection.create_index("audio_id")
            self.assignments_collection.create_index("campaign_id")
            self.assignments_collection.create_index("brand_id")
            self.assignments_collection.create_index("user_id")
            self.assignments_collection.create_index("assigned_at")
            self.assignments_collection.create_index("status")
            
            logger.info(f"MongoDB connected successfully to {self.database_name}")
            
        except Exception as e:
            logger.error(f"MongoDB connection failed: {str(e)}")
            self.client = None
            self.db = None
            self.assignments_collection = None
    
    def is_connected(self) -> bool:
        """Check if MongoDB connection is available."""
        return self.client is not None and self.db is not None
    
    async def assign_audio_to_brand(
        self, 
        audio_id: str, 
        brand_id: str, 
        user_id: str, 
        assigned_by: str,
        campaign_id: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Assign an audio to a brand (and optionally to a campaign).
        
        Args:
            audio_id: ID of the audio to assign
            brand_id: ID of the brand to assign to
            user_id: ID of the user who owns the audio
            assigned_by: ID of the user making the assignment
            campaign_id: Optional campaign ID to assign to
            notes: Optional notes about the assignment
            
        Returns:
            Dictionary with success status and assignment details
        """
        try:
            if not self.is_connected():
                return {
                    "success": False,
                    "error": "MongoDB connection not available"
                }
            
            # Check if audio is already assigned to this brand
            existing_assignment = self.assignments_collection.find_one({
                "audio_id": audio_id,
                "brand_id": brand_id,
                "status": "active"
            })
            
            if existing_assignment:
                return {
                    "success": False,
                    "error": "Audio is already assigned to this brand"
                }
            
            # Create assignment document
            assignment_id = f"assign_{secrets.token_hex(12)}"
            assignment_doc = {
                "assignment_id": assignment_id,
                "audio_id": audio_id,
                "brand_id": brand_id,
                "user_id": user_id,
                "assigned_by": assigned_by,
                "assigned_at": datetime.now(timezone.utc),
                "status": "active",
                "notes": notes,
                "metadata": {
                    "campaign_id": campaign_id,
                    "assignment_type": "brand" if not campaign_id else "campaign"
                }
            }
            
            # Insert assignment
            result = self.assignments_collection.insert_one(assignment_doc)
            
            if result.inserted_id:
                logger.info(f"Audio {audio_id} assigned to brand {brand_id} by user {assigned_by}")
                return {
                    "success": True,
                    "assignment_id": assignment_id,
                    "message": "Audio assigned to brand successfully"
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to create assignment"
                }
                
        except Exception as e:
            logger.error(f"Failed to assign audio to brand: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to assign audio to brand: {str(e)}"
            }
    
    async def unassign_audio_from_brand(
        self, 
        audio_id: str, 
        brand_id: str, 
        user_id: str
    ) -> Dict[str, Any]:
        """
        Unassign an audio from a brand.
        
        Args:
            audio_id: ID of the audio to unassign
            brand_id: ID of the brand to unassign from
            user_id: ID of the user making the request
            
        Returns:
            Dictionary with success status
        """
        try:
            if not self.is_connected():
                return {
                    "success": False,
                    "error": "MongoDB connection not available"
                }
            
            # Find and update assignment
            result = self.assignments_collection.update_one(
                {
                    "audio_id": audio_id,
                    "brand_id": brand_id,
                    "user_id": user_id,
                    "status": "active"
                },
                {
                    "$set": {
                        "status": "inactive",
                        "unassigned_at": datetime.now(timezone.utc),
                        "unassigned_by": user_id
                    }
                }
            )
            
            if result.modified_count > 0:
                logger.info(f"Audio {audio_id} unassigned from brand {brand_id}")
                return {
                    "success": True,
                    "message": "Audio unassigned from brand successfully"
                }
            else:
                return {
                    "success": False,
                    "error": "Audio assignment not found or already inactive"
                }
                
        except Exception as e:
            logger.error(f"Failed to unassign audio from brand: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to unassign audio from brand: {str(e)}"
            }
    
    async def get_brand_audios(
        self, 
        brand_id: str, 
        user_id: str,
        limit: int = 50,
        skip: int = 0,
        status: str = "active"
    ) -> Dict[str, Any]:
        """
        Get all audios assigned to a brand.
        
        Args:
            brand_id: ID of the brand
            user_id: ID of the user making the request
            limit: Maximum number of results
            skip: Number of results to skip
            status: Status of assignments to retrieve
            
        Returns:
            Dictionary with assigned audios and metadata
        """
        try:
            if not self.is_connected():
                return {
                    "success": False,
                    "error": "MongoDB connection not available"
                }
            
            # Get assignments for the brand
            query = {
                "brand_id": brand_id,
                "status": status
            }
            
            # Get total count
            total_count = self.assignments_collection.count_documents(query)
            
            # Get assignments with pagination
            cursor = (
                self.assignments_collection
                .find(query)
                .sort("assigned_at", -1)
                .skip(skip)
                .limit(limit)
            )
            
            assignments = []
            for doc in cursor:
                # Convert ObjectId and datetime to string
                doc["_id"] = str(doc["_id"])
                doc["assigned_at"] = doc["assigned_at"].isoformat()
                if "unassigned_at" in doc:
                    doc["unassigned_at"] = doc["unassigned_at"].isoformat()
                assignments.append(doc)
            
            return {
                "success": True,
                "assignments": assignments,
                "total_count": total_count,
                "limit": limit,
                "skip": skip
            }
            
        except Exception as e:
            logger.error(f"Failed to get brand audios: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to get brand audios: {str(e)}"
            }
    
    async def get_user_audio_assignments(
        self, 
        user_id: str,
        limit: int = 50,
        skip: int = 0,
        status: str = "active"
    ) -> Dict[str, Any]:
        """
        Get all audio assignments for a user.
        
        Args:
            user_id: ID of the user
            limit: Maximum number of results
            skip: Number of results to skip
            status: Status of assignments to retrieve
            
        Returns:
            Dictionary with user's audio assignments
        """
        try:
            if not self.is_connected():
                return {
                    "success": False,
                    "error": "MongoDB connection not available"
                }
            
            # Get assignments for the user
            query = {
                "user_id": user_id,
                "status": status
            }
            
            # Get total count
            total_count = self.assignments_collection.count_documents(query)
            
            # Get assignments with pagination
            cursor = (
                self.assignments_collection
                .find(query)
                .sort("assigned_at", -1)
                .skip(skip)
                .limit(limit)
            )
            
            assignments = []
            for doc in cursor:
                # Convert ObjectId and datetime to string
                doc["_id"] = str(doc["_id"])
                doc["assigned_at"] = doc["assigned_at"].isoformat()
                if "unassigned_at" in doc:
                    doc["unassigned_at"] = doc["unassigned_at"].isoformat()
                assignments.append(doc)
            
            return {
                "success": True,
                "assignments": assignments,
                "total_count": total_count,
                "limit": limit,
                "skip": skip
            }
            
        except Exception as e:
            logger.error(f"Failed to get user audio assignments: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to get user audio assignments: {str(e)}"
            }
    
    async def get_audio_assignments(
        self, 
        audio_id: str, 
        user_id: str
    ) -> Dict[str, Any]:
        """
        Get all assignments for a specific audio.
        
        Args:
            audio_id: ID of the audio
            user_id: ID of the user making the request
            
        Returns:
            Dictionary with audio assignments
        """
        try:
            if not self.is_connected():
                return {
                    "success": False,
                    "error": "MongoDB connection not available"
                }
            
            # Get assignments for the audio
            query = {
                "audio_id": audio_id,
                "user_id": user_id
            }
            
            cursor = self.assignments_collection.find(query).sort("assigned_at", -1)
            
            assignments = []
            for doc in cursor:
                # Convert ObjectId and datetime to string
                doc["_id"] = str(doc["_id"])
                doc["assigned_at"] = doc["assigned_at"].isoformat()
                if "unassigned_at" in doc:
                    doc["unassigned_at"] = doc["unassigned_at"].isoformat()
                assignments.append(doc)
            
            return {
                "success": True,
                "assignments": assignments,
                "total_count": len(assignments)
            }
            
        except Exception as e:
            logger.error(f"Failed to get audio assignments: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to get audio assignments: {str(e)}"
            }

# Create global instance
audio_assignment_service = AudioAssignmentService()
