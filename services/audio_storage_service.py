#!/usr/bin/env python3
"""
MongoDB Audio Storage Service for Content Crew Prodigal
Handles audio file metadata storage and retrieval
"""

import os
import logging
import base64
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from bson import ObjectId
import json

logger = logging.getLogger(__name__)

class AudioStorageService:
    """Service for storing and retrieving audio metadata in MongoDB."""
    
    def __init__(self):
        self.mongo_url = os.getenv("MONGODB_URL", "mongodb+srv://ashwini:Ashwini1234@cluster0.lyeisj1.mongodb.net/Dhanur-AI")
        self.database_name = os.getenv("MONGODB_DATABASE", "Dhanur-AI")
        self.collection_name = "audio_files"
        self.elevenlabs_collection_name = "elevenlabs_audios"
        
        try:
            self.client = MongoClient(self.mongo_url)
            self.db: Database = self.client[self.database_name]
            self.collection: Collection = self.db[self.collection_name]
            self.elevenlabs_collection: Collection = self.db[self.elevenlabs_collection_name]
            
            # Create indexes for better performance
            self.collection.create_index("user_id")
            self.collection.create_index("created_at")
            self.collection.create_index("language")
            self.collection.create_index("status")
            
            # Create indexes for ElevenLabs collection
            self.elevenlabs_collection.create_index("user_id")
            self.elevenlabs_collection.create_index("created_at")
            self.elevenlabs_collection.create_index("status")
            
            logger.info(f"MongoDB connected successfully to {self.database_name}")
            
        except Exception as e:
            logger.error(f"MongoDB connection failed: {str(e)}")
            self.client = None
            self.db = None
            self.collection = None
            self.elevenlabs_collection = None
    
    def is_connected(self) -> bool:
        """Check if MongoDB is connected."""
        try:
            if self.client:
                self.client.admin.command('ping')
                return True
        except Exception:
            pass
        return False
    
    def _save_audio_data_as_wav(self, audio_data: str, audio_id: str) -> str:
        """Save base64 audio data as wav file and return URL."""
        try:
            # Create static directory if it doesn't exist
            static_dir = "static"
            if not os.path.exists(static_dir):
                os.makedirs(static_dir)
            
            # Generate unique filename
            filename = f"elevenlabs_{audio_id}.wav"
            file_path = os.path.join(static_dir, filename)
            
            # Decode base64 audio data
            audio_bytes = base64.b64decode(audio_data)
            
            # Save as wav file
            with open(file_path, 'wb') as f:
                f.write(audio_bytes)
            
            # Generate URL (assuming server serves static files)
            base_url = os.getenv("BASE_URL", "https://dhanur-ai-10fd99bc9730.herokuapp.com")
            audio_url = f"{base_url}/static/{filename}"
            
            logger.info(f"Saved ElevenLabs audio as wav: {file_path}")
            return audio_url
            
        except Exception as e:
            logger.error(f"Failed to save audio data as wav: {str(e)}")
            return ""
    
    def _get_audio_assignments_info(self, audio_id: str) -> Dict[str, Any]:
        """Get assignment information for an audio."""
        try:
            if not self.is_connected():
                return {}
            
            # Get assignments for this audio
            assignments_collection = self.db["audio_campaign_assignments"]
            assignments = list(assignments_collection.find({
                "audio_id": audio_id,
                "status": "active"
            }))
            
            if not assignments:
                return {}
            
            # Get brand and campaign names
            assignment_info = []
            for assignment in assignments:
                brand_id = assignment.get("brand_id")
                campaign_id = assignment.get("metadata", {}).get("campaign_id")
                
                # Get brand name
                brand_name = "Unknown Brand"
                if brand_id:
                    brand_doc = self.db["brands"].find_one({"brand_id": brand_id})
                    if brand_doc:
                        brand_name = brand_doc.get("name", "Unknown Brand")
                
                # Get campaign name
                campaign_name = None
                if campaign_id:
                    campaign_doc = self.db["campaigns"].find_one({"campaign_id": campaign_id})
                    if campaign_doc:
                        campaign_name = campaign_doc.get("name", "Unknown Campaign")
                
                assignment_info.append({
                    "brand_id": brand_id,
                    "brand_name": brand_name,
                    "campaign_id": campaign_id,
                    "campaign_name": campaign_name,
                    "assigned_at": assignment.get("assigned_at").isoformat() if assignment.get("assigned_at") else None,
                    "assigned_by": assignment.get("assigned_by"),
                    "notes": assignment.get("notes")
                })
            
            return {
                "is_assigned": len(assignment_info) > 0,
                "assignments": assignment_info
            }
            
        except Exception as e:
            logger.error(f"Failed to get audio assignments info: {str(e)}")
            return {}

    def _normalize_elevenlabs_doc(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize ElevenLabs document to match TTS format."""
        try:
            # Convert ObjectId to string
            doc["_id"] = str(doc["_id"])
            
            # Convert datetime to string
            if "created_at" in doc:
                doc["created_at"] = doc["created_at"].isoformat()
            if "updated_at" in doc:
                doc["updated_at"] = doc["updated_at"].isoformat()
            
            # Generate audio URL from base64 data
            audio_url = ""
            if doc.get("audio_data"):
                audio_url = self._save_audio_data_as_wav(
                    doc.get("audio_data"), 
                    doc.get("audio_id", str(doc["_id"]))
                )
            
            # Map ElevenLabs fields to TTS format
            normalized_doc = {
                "_id": doc["_id"],
                "user_id": doc.get("user_id"),
                "audio_url": audio_url,  # Generated wav file URL
                "audio_data": doc.get("audio_data"),  # Keep original audio data
                "text": doc.get("text", ""),
                "text_length": len(doc.get("text", "")),
                "language": "english",  # Default for ElevenLabs
                "gender": "unknown",  # Not specified in ElevenLabs
                "model_used": doc.get("model_id", "elevenlabs"),
                "processing_time": 0.0,  # Not tracked in ElevenLabs
                "status": doc.get("status", "completed"),
                "created_at": doc.get("created_at"),
                "updated_at": doc.get("updated_at"),
                "metadata": {
                    "voice_priority": f"elevenlabs_{doc.get('voice_id', 'unknown')}",
                    "speaker_name": doc.get("voice_id", "unknown"),
                    "generation_method": "elevenlabs",
                    "voice_id": doc.get("voice_id"),
                    "voice_settings": doc.get("voice_settings", {}),
                    "audio_size": doc.get("audio_size", 0),
                    "credits_used": doc.get("credits_used", 0),
                    "brand_id": doc.get("brand_id")
                }
            }
            
            return normalized_doc
            
        except Exception as e:
            logger.error(f"Failed to normalize ElevenLabs document: {str(e)}")
            return doc
    
    async def save_audio_metadata(
        self, 
        user_id: str,
        audio_url: str,
        text: str,
        language: str = "english",
        gender: str = "male",
        model_used: str = "chatterbox_real_ai",
        processing_time: float = 0.0,
        status: str = "completed"
    ) -> Dict[str, Any]:
        """
        Save audio metadata to MongoDB.
        
        Args:
            user_id: User ID who generated the audio
            audio_url: URL of the generated audio file
            text: Original text that was converted to speech
            language: Language used for TTS
            gender: Gender of the voice
            model_used: TTS model used
            processing_time: Time taken to generate audio
            status: Status of the audio generation
            
        Returns:
            Dictionary with success status and audio ID
        """
        try:
            if not self.is_connected():
                return {
                    "success": False,
                    "error": "MongoDB connection not available"
                }
            
            audio_doc = {
                "user_id": user_id,
                "audio_url": audio_url,
                "text": text,
                "text_length": len(text),
                "language": language,
                "gender": gender,
                "model_used": model_used,
                "processing_time": processing_time,
                "status": status,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "metadata": {
                    "voice_priority": f"{language}_{gender}",
                    "speaker_name": "default",
                    "generation_method": "ai_orchestration"
                }
            }
            
            result = self.collection.insert_one(audio_doc)
            audio_id = str(result.inserted_id)
            
            logger.info(f"Audio metadata saved for user {user_id}, audio_id: {audio_id}")
            
            return {
                "success": True,
                "audio_id": audio_id,
                "message": "Audio metadata saved successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to save audio metadata: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to save audio metadata: {str(e)}"
            }
    
    async def get_user_audios(
        self, 
        user_id: str, 
        limit: int = 50, 
        skip: int = 0,
        language: Optional[str] = None,
        status: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get audio files for a specific user from both TTS and ElevenLabs collections.
        
        Args:
            user_id: User ID
            limit: Maximum number of results
            skip: Number of results to skip
            language: Filter by language
            status: Filter by status
            
        Returns:
            Dictionary with audio files list
        """
        try:
            if not self.is_connected():
                return {
                    "success": False,
                    "error": "MongoDB connection not available"
                }
            
            # Build query for TTS collection
            tts_query = {"user_id": user_id}
            if language:
                tts_query["language"] = language
            if status:
                tts_query["status"] = status
            
            # Build query for ElevenLabs collection
            el_query = {"user_id": user_id}
            if status:
                el_query["status"] = status
            # Note: ElevenLabs doesn't have language field, so we skip language filter for it
            
            # Get total count from both collections
            tts_count = self.collection.count_documents(tts_query)
            el_count = self.elevenlabs_collection.count_documents(el_query)
            total_count = tts_count + el_count
            
            # Get TTS audio files
            tts_cursor = self.collection.find(tts_query).sort("created_at", -1)
            tts_files = []
            for doc in tts_cursor:
                doc["_id"] = str(doc["_id"])
                doc["created_at"] = doc["created_at"].isoformat()
                doc["updated_at"] = doc["updated_at"].isoformat()
                
                # Add assignment information
                audio_id = str(doc["_id"])
                assignment_info = self._get_audio_assignments_info(audio_id)
                doc["assignment_info"] = assignment_info
                
                tts_files.append(doc)
            
            # Get ElevenLabs audio files
            el_cursor = self.elevenlabs_collection.find(el_query).sort("created_at", -1)
            el_files = []
            for doc in el_cursor:
                normalized_doc = self._normalize_elevenlabs_doc(doc)
                
                # Add assignment information
                audio_id = doc.get("audio_id", str(doc["_id"]))
                assignment_info = self._get_audio_assignments_info(audio_id)
                normalized_doc["assignment_info"] = assignment_info
                
                el_files.append(normalized_doc)
            
            # Combine and sort all files by created_at
            all_files = tts_files + el_files
            all_files.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            
            # Apply pagination
            paginated_files = all_files[skip:skip + limit]
            
            return {
                "success": True,
                "audio_files": paginated_files,
                "total_count": total_count,
                "tts_count": tts_count,
                "elevenlabs_count": el_count,
                "limit": limit,
                "skip": skip
            }
            
        except Exception as e:
            logger.error(f"Failed to get user audios: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to get user audios: {str(e)}"
            }
    
    async def get_audio_by_id(self, audio_id: str, user_id: str) -> Dict[str, Any]:
        """
        Get specific audio file by ID from both TTS and ElevenLabs collections.
        
        Args:
            audio_id: Audio file ID
            user_id: User ID (for security)
            
        Returns:
            Dictionary with audio file data
        """
        try:
            if not self.is_connected():
                return {
                    "success": False,
                    "error": "MongoDB connection not available"
                }
            
            # First try to find in TTS collection
            try:
                object_id = ObjectId(audio_id)
                doc = self.collection.find_one({"_id": object_id, "user_id": user_id})
                
                if doc:
                    # Convert ObjectId and datetime to string
                    doc["_id"] = str(doc["_id"])
                    doc["created_at"] = doc["created_at"].isoformat()
                    doc["updated_at"] = doc["updated_at"].isoformat()
                    
                    # Add assignment information
                    audio_id = str(doc["_id"])
                    assignment_info = self._get_audio_assignments_info(audio_id)
                    doc["assignment_info"] = assignment_info
                    
                    return {
                        "success": True,
                        "audio_file": doc,
                        "source": "tts"
                    }
            except Exception:
                # If ObjectId conversion fails, try ElevenLabs collection
                pass
            
            # Try ElevenLabs collection (first by _id, then by audio_id)
            el_doc = None
            try:
                # Try with _id as ObjectId first
                object_id = ObjectId(audio_id)
                el_doc = self.elevenlabs_collection.find_one({"_id": object_id, "user_id": user_id})
            except Exception:
                pass
            
            # If not found by _id, try by audio_id field
            if not el_doc:
                el_doc = self.elevenlabs_collection.find_one({"audio_id": audio_id, "user_id": user_id})
            
            if el_doc:
                normalized_doc = self._normalize_elevenlabs_doc(el_doc)
                
                # Add assignment information using the _id for lookups
                lookup_id = str(el_doc["_id"])
                assignment_info = self._get_audio_assignments_info(lookup_id)
                normalized_doc["assignment_info"] = assignment_info
                
                return {
                    "success": True,
                    "audio_file": normalized_doc,
                    "source": "elevenlabs"
                }
            
            # If not found in either collection
            return {
                "success": False,
                "error": "Audio file not found or access denied"
            }
            
        except Exception as e:
            logger.error(f"Failed to get audio by ID: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to get audio by ID: {str(e)}"
            }
    
    async def delete_audio(self, audio_id: str, user_id: str) -> Dict[str, Any]:
        """
        Delete audio file metadata from both TTS and ElevenLabs collections.
        
        Args:
            audio_id: Audio file ID
            user_id: User ID (for security)
            
        Returns:
            Dictionary with deletion result
        """
        try:
            if not self.is_connected():
                return {
                    "success": False,
                    "error": "MongoDB connection not available"
                }
            
            # First try to delete from TTS collection
            try:
                object_id = ObjectId(audio_id)
                result = self.collection.delete_one({"_id": object_id, "user_id": user_id})
                
                if result.deleted_count > 0:
                    logger.info(f"TTS audio file {audio_id} deleted for user {user_id}")
                    return {
                        "success": True,
                        "message": "Audio file deleted successfully",
                        "source": "tts"
                    }
            except Exception:
                # If ObjectId conversion fails, try ElevenLabs collection
                pass
            
            # Try ElevenLabs collection (using audio_id as string)
            el_result = self.elevenlabs_collection.delete_one({"audio_id": audio_id, "user_id": user_id})
            
            if el_result.deleted_count > 0:
                logger.info(f"ElevenLabs audio file {audio_id} deleted for user {user_id}")
                return {
                    "success": True,
                    "message": "Audio file deleted successfully",
                    "source": "elevenlabs"
                }
            
            # If not found in either collection
            return {
                "success": False,
                "error": "Audio file not found or access denied"
            }
            
        except Exception as e:
            logger.error(f"Failed to delete audio: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to delete audio: {str(e)}"
            }
    
    async def get_audio_statistics(self, user_id: str) -> Dict[str, Any]:
        """
        Get audio generation statistics for a user from both TTS and ElevenLabs collections.
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary with statistics
        """
        try:
            if not self.is_connected():
                return {
                    "success": False,
                    "error": "MongoDB connection not available"
                }
            
            # Get total count from both collections
            tts_count = self.collection.count_documents({"user_id": user_id})
            el_count = self.elevenlabs_collection.count_documents({"user_id": user_id})
            total_audios = tts_count + el_count
            
            # Get language distribution from TTS collection
            language_pipeline = [
                {"$match": {"user_id": user_id}},
                {"$group": {"_id": "$language", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}}
            ]
            language_stats = list(self.collection.aggregate(language_pipeline))
            
            # Add ElevenLabs count to language stats (as "elevenlabs")
            if el_count > 0:
                language_stats.append({"_id": "elevenlabs", "count": el_count})
                language_stats.sort(key=lambda x: x["count"], reverse=True)
            
            # Get recent activity (last 30 days) from both collections
            from datetime import timedelta
            thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
            tts_recent = self.collection.count_documents({
                "user_id": user_id,
                "created_at": {"$gte": thirty_days_ago}
            })
            el_recent = self.elevenlabs_collection.count_documents({
                "user_id": user_id,
                "created_at": {"$gte": thirty_days_ago}
            })
            recent_audios = tts_recent + el_recent
            
            # Get average processing time from TTS collection only
            processing_pipeline = [
                {"$match": {"user_id": user_id, "processing_time": {"$gt": 0}}},
                {"$group": {"_id": None, "avg_time": {"$avg": "$processing_time"}}}
            ]
            avg_processing = list(self.collection.aggregate(processing_pipeline))
            avg_processing_time = avg_processing[0]["avg_time"] if avg_processing else 0
            
            return {
                "success": True,
                "statistics": {
                    "total_audios": total_audios,
                    "tts_audios": tts_count,
                    "elevenlabs_audios": el_count,
                    "recent_audios_30_days": recent_audios,
                    "tts_recent_30_days": tts_recent,
                    "elevenlabs_recent_30_days": el_recent,
                    "average_processing_time": round(avg_processing_time, 2),
                    "language_distribution": language_stats
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get audio statistics: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to get audio statistics: {str(e)}"
            }
    
    def close_connection(self):
        """Close MongoDB connection."""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")

# Create singleton instance
audio_storage_service = AudioStorageService()
