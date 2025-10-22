#!/usr/bin/env python3
"""
ElevenLabs Operations for Content Crew Prodigal
"""

import logging
import base64
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from services.mongodb_service import mongodb_service
from services.user_credits_service import user_credits_service
from .client import ElevenLabsClient

logger = logging.getLogger(__name__)

class ElevenLabsOps:
    """ElevenLabs operations for voice generation and management."""
    
    def __init__(self):
        self.client = ElevenLabsClient()
        self.audio_collection = mongodb_service.get_collection("elevenlabs_audios")
    
    async def generate_speech(
        self,
        text: str,
        voice_id: str = "21m00Tcm4TlvDq8ikWAM",
        model_id: str = "eleven_monolingual_v1",
        voice_settings: Optional[Dict[str, Any]] = None,
        user_id: str = None,
        brand_id: str = None,
        save_to_db: bool = True
    ) -> Dict[str, Any]:
        """
        Generate speech from text and optionally save to database.
        Deducts 10 credits per voice generation.
        
        Args:
            text: Text to convert to speech
            voice_id: ElevenLabs voice ID
            model_id: Model to use for generation
            voice_settings: Voice settings
            user_id: User ID for tracking
            brand_id: Brand ID for tracking
            save_to_db: Whether to save audio to database
            
        Returns:
            Dict containing audio data and metadata
        """
        try:
            # Check and deduct credits if user_id provided
            if user_id:
                credit_cost = 10  # 10 credits per voice generation
                credit_result = await user_credits_service.deduct_credits(
                    user_id=user_id,
                    amount=credit_cost,
                    reason=f"ElevenLabs voice generation - {voice_id}"
                )
                
                if not credit_result["success"]:
                    return {
                        "success": False,
                        "error": f"Insufficient credits: {credit_result['error']}",
                        "required_credits": credit_cost,
                        "current_credits": credit_result.get("current_credits", 0)
                    }
                
                logger.info(f"Deducted {credit_cost} credits from user {user_id}. New balance: {credit_result['new_balance']}")
            
            # Generate speech using ElevenLabs API
            audio_data = self.client.text_to_speech(
                text=text,
                voice_id=voice_id,
                model_id=model_id,
                voice_settings=voice_settings
            )
            
            # Convert audio to base64 for storage
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            
            result = {
                "success": True,
                "audio_data": audio_base64,
                "audio_size": len(audio_data),
                "voice_id": voice_id,
                "model_id": model_id,
                "text_length": len(text),
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "credits_used": credit_cost if user_id else 0
            }
            
            # Save to database if requested
            if save_to_db and user_id:
                audio_doc = {
                    "audio_id": f"el_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{voice_id}",
                    "user_id": user_id,
                    "brand_id": brand_id,
                    "text": text,
                    "voice_id": voice_id,
                    "model_id": model_id,
                    "voice_settings": voice_settings or {},
                    "audio_data": audio_base64,
                    "audio_size": len(audio_data),
                    "credits_used": credit_cost,
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc),
                    "status": "completed"
                }
                
                self.audio_collection.insert_one(audio_doc)
                result["audio_id"] = audio_doc["audio_id"]
                logger.info(f"Audio generated and saved: {audio_doc['audio_id']}")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to generate speech: {e}")
            return {
                "success": False,
                "error": str(e),
                "audio_data": None
            }
    
    async def get_user_audios(
        self,
        user_id: str,
        brand_id: Optional[str] = None,
        limit: int = 20,
        skip: int = 0
    ) -> Dict[str, Any]:
        """
        Get user's generated audios.
        
        Args:
            user_id: User ID
            brand_id: Optional brand filter
            limit: Number of audios to return
            skip: Number of audios to skip
            
        Returns:
            Dict containing list of audios
        """
        try:
            query = {"user_id": user_id}
            if brand_id:
                query["brand_id"] = brand_id
            
            # Get total count
            total = self.audio_collection.count_documents(query)
            
            # Get audios with pagination
            audios_cursor = self.audio_collection.find(query).sort("created_at", -1).skip(skip).limit(limit)
            audios = []
            
            for audio in audios_cursor:
                # Remove audio_data from response to reduce size
                audio_doc = {
                    "audio_id": audio.get("audio_id"),
                    "text": audio.get("text"),
                    "voice_id": audio.get("voice_id"),
                    "model_id": audio.get("model_id"),
                    "voice_settings": audio.get("voice_settings", {}),
                    "audio_size": audio.get("audio_size"),
                    "created_at": audio.get("created_at").isoformat() if audio.get("created_at") else None,
                    "status": audio.get("status")
                }
                audios.append(audio_doc)
            
            return {
                "success": True,
                "audios": audios,
                "total": total,
                "returned": len(audios),
                "limit": limit,
                "skip": skip
            }
            
        except Exception as e:
            logger.error(f"Failed to get user audios: {e}")
            return {
                "success": False,
                "error": str(e),
                "audios": []
            }
    
    async def get_audio_by_id(self, audio_id: str, user_id: str) -> Dict[str, Any]:
        """
        Get specific audio by ID.
        
        Args:
            audio_id: Audio ID
            user_id: User ID for authorization
            
        Returns:
            Dict containing audio data
        """
        try:
            audio = self.audio_collection.find_one({
                "audio_id": audio_id,
                "user_id": user_id
            })
            
            if not audio:
                return {
                    "success": False,
                    "error": "Audio not found"
                }
            
            return {
                "success": True,
                "audio": {
                    "audio_id": audio.get("audio_id"),
                    "text": audio.get("text"),
                    "voice_id": audio.get("voice_id"),
                    "model_id": audio.get("model_id"),
                    "voice_settings": audio.get("voice_settings", {}),
                    "audio_data": audio.get("audio_data"),
                    "audio_size": audio.get("audio_size"),
                    "created_at": audio.get("created_at").isoformat() if audio.get("created_at") else None,
                    "status": audio.get("status")
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get audio {audio_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def delete_audio(self, audio_id: str, user_id: str) -> Dict[str, Any]:
        """
        Delete audio by ID.
        
        Args:
            audio_id: Audio ID
            user_id: User ID for authorization
            
        Returns:
            Dict containing deletion result
        """
        try:
            result = self.audio_collection.delete_one({
                "audio_id": audio_id,
                "user_id": user_id
            })
            
            if result.deleted_count == 0:
                return {
                    "success": False,
                    "error": "Audio not found or access denied"
                }
            
            logger.info(f"Audio {audio_id} deleted by user {user_id}")
            return {
                "success": True,
                "message": "Audio deleted successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to delete audio {audio_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_voices(self) -> Dict[str, Any]:
        """Get available voices from ElevenLabs."""
        try:
            # Check if API key is valid
            if not self.client.api_key or self.client.api_key == "your_elevenlabs_api_key_here":
                # Return comprehensive mock voices for testing
                mock_voices = [
                    {
                        "voice_id": "21m00Tcm4TlvDq8ikWAM",
                        "name": "Rachel",
                        "category": "premade",
                        "description": "A calm, collected voice with a hint of warmth",
                        "gender": "female",
                        "age": "young_adult",
                        "accent": "american",
                        "style": "professional",
                        "icon": "👩",
                        "color": "blue"
                    },
                    {
                        "voice_id": "AZnzlk1XvdvUeBnXmlld",
                        "name": "Domi",
                        "category": "premade",
                        "description": "A confident, strong voice",
                        "gender": "female",
                        "age": "adult",
                        "accent": "american",
                        "style": "authoritative",
                        "icon": "👩‍💼",
                        "color": "red"
                    },
                    {
                        "voice_id": "EXAVITQu4vr4xnSDxMaL",
                        "name": "Bella",
                        "category": "premade",
                        "description": "A warm, friendly voice",
                        "gender": "female",
                        "age": "young_adult",
                        "accent": "american",
                        "style": "friendly",
                        "icon": "😊",
                        "color": "green"
                    },
                    {
                        "voice_id": "ErXwobaYiN019PkySvjV",
                        "name": "Antoni",
                        "category": "premade",
                        "description": "A smooth, deep voice with a hint of mystery",
                        "gender": "male",
                        "age": "adult",
                        "accent": "american",
                        "style": "smooth",
                        "icon": "👨",
                        "color": "purple"
                    },
                    {
                        "voice_id": "MF3mGyEYCl7XYWbV9V6O",
                        "name": "Elli",
                        "category": "premade",
                        "description": "A young, energetic voice full of enthusiasm",
                        "gender": "female",
                        "age": "young",
                        "accent": "american",
                        "style": "energetic",
                        "icon": "👧",
                        "color": "yellow"
                    },
                    {
                        "voice_id": "TxGEqnHWrfWFTfGW9XjX",
                        "name": "Josh",
                        "category": "premade",
                        "description": "A deep, masculine voice with authority",
                        "gender": "male",
                        "age": "adult",
                        "accent": "american",
                        "style": "authoritative",
                        "icon": "👨‍💼",
                        "color": "indigo"
                    },
                    {
                        "voice_id": "VR6AewLTigWG4xSOukaG",
                        "name": "Arnold",
                        "category": "premade",
                        "description": "A gruff, tough voice with character",
                        "gender": "male",
                        "age": "senior",
                        "accent": "american",
                        "style": "gruff",
                        "icon": "👴",
                        "color": "orange"
                    },
                    {
                        "voice_id": "pNInz6obpgDQGcFmaJgB",
                        "name": "Adam",
                        "category": "premade",
                        "description": "A clear, professional voice perfect for narration",
                        "gender": "male",
                        "age": "adult",
                        "accent": "american",
                        "style": "professional",
                        "icon": "👨‍🎓",
                        "color": "teal"
                    },
                    {
                        "voice_id": "yoZ06aMxZJJ28mfd3POQ",
                        "name": "Sam",
                        "category": "premade",
                        "description": "A versatile voice that adapts to any content",
                        "gender": "male",
                        "age": "young_adult",
                        "accent": "american",
                        "style": "versatile",
                        "icon": "🎭",
                        "color": "pink"
                    }
                ]
                return {
                    "success": True,
                    "voices": mock_voices,
                    "layout": {
                        "columns": 2,
                        "categories": ["all", "premade", "cloned", "designed"],
                        "filters": ["gender", "age", "accent", "style"],
                        "default_category": "all"
                    }
                }
            
            voices_data = self.client.get_voices()
            return {
                "success": True,
                "voices": voices_data.get("voices", [])
            }
        except Exception as e:
            logger.error(f"Failed to get voices: {e}")
            return {
                "success": False,
                "error": str(e),
                "voices": []
            }
    
    async def get_models(self) -> Dict[str, Any]:
        """Get available models from ElevenLabs."""
        try:
            # Check if API key is valid
            if not self.client.api_key or self.client.api_key == "your_elevenlabs_api_key_here":
                # Return comprehensive mock models for testing
                mock_models = [
                    {
                        "model_id": "eleven_multilingual_v2",
                        "name": "Eleven Multilingual v2",
                        "description": "Our most advanced multilingual model. Supports 28 languages with improved quality and stability.",
                        "category": "multilingual",
                        "languages": ["en", "es", "fr", "de", "it", "pt", "pl", "tr", "ru", "nl", "cs", "ar", "zh", "ja", "hi", "ko", "th", "sv", "da", "no", "fi", "el", "hu", "ro", "bg", "hr", "sk", "sl"],
                        "max_characters": 5000,
                        "features": [
                            "28 languages supported",
                            "High quality output",
                            "Stable performance",
                            "Multilingual context"
                        ],
                        "icon": "🌍",
                        "color": "blue",
                        "status": "stable"
                    },
                    {
                        "model_id": "eleven_multilingual_v1",
                        "name": "Eleven Multilingual v1",
                        "description": "Our first multilingual model supporting 28 languages. Good quality with broad language support.",
                        "category": "multilingual",
                        "languages": ["en", "es", "fr", "de", "it", "pt", "pl", "tr", "ru", "nl", "cs", "ar", "zh", "ja", "hi", "ko", "th", "sv", "da", "no", "fi", "el", "hu", "ro", "bg", "hr", "sk", "sl"],
                        "max_characters": 5000,
                        "features": [
                            "28 languages supported",
                            "Good quality output",
                            "Broad language support"
                        ],
                        "icon": "🌐",
                        "color": "green",
                        "status": "stable"
                    },
                    {
                        "model_id": "eleven_monolingual_v1",
                        "name": "Eleven Monolingual v1",
                        "description": "Our fastest model optimized for English. Best for English-only content with maximum speed.",
                        "category": "monolingual",
                        "languages": ["en"],
                        "max_characters": 5000,
                        "features": [
                            "English only",
                            "Fastest processing",
                            "High quality for English",
                            "Optimized performance"
                        ],
                        "icon": "🇺🇸",
                        "color": "red",
                        "status": "stable"
                    },
                    {
                        "model_id": "eleven_turbo_v2_5",
                        "name": "Eleven Turbo v2.5",
                        "description": "Ultra-fast model with excellent quality. Perfect for real-time applications and quick generation.",
                        "category": "turbo",
                        "languages": ["en", "es", "fr", "de", "it", "pt", "pl", "tr", "ru", "nl", "cs", "ar", "zh", "ja", "hi", "ko", "th", "sv", "da", "no", "fi", "el", "hu", "ro", "bg", "hr", "sk", "sl"],
                        "max_characters": 3000,
                        "features": [
                            "Ultra-fast processing",
                            "28 languages supported",
                            "Real-time capable",
                            "High quality output"
                        ],
                        "icon": "⚡",
                        "color": "yellow",
                        "status": "stable"
                    },
                    {
                        "model_id": "eleven_turbo_v2",
                        "name": "Eleven Turbo v2",
                        "description": "Fast model with good quality. Great balance between speed and output quality.",
                        "category": "turbo",
                        "languages": ["en", "es", "fr", "de", "it", "pt", "pl", "tr", "ru", "nl", "cs", "ar", "zh", "ja", "hi", "ko", "th", "sv", "da", "no", "fi", "el", "hu", "ro", "bg", "hr", "sk", "sl"],
                        "max_characters": 3000,
                        "features": [
                            "Fast processing",
                            "28 languages supported",
                            "Good quality",
                            "Balanced performance"
                        ],
                        "icon": "🚀",
                        "color": "orange",
                        "status": "stable"
                    },
                    {
                        "model_id": "eleven_flash_v2_5",
                        "name": "Eleven Flash v2.5",
                        "description": "Lightning-fast model for instant generation. Optimized for speed with good quality output.",
                        "category": "flash",
                        "languages": ["en", "es", "fr", "de", "it", "pt", "pl", "tr", "ru", "nl", "cs", "ar", "zh", "ja", "hi", "ko", "th", "sv", "da", "no", "fi", "el", "hu", "ro", "bg", "hr", "sk", "sl"],
                        "max_characters": 2000,
                        "features": [
                            "Lightning-fast processing",
                            "28 languages supported",
                            "Instant generation",
                            "Good quality"
                        ],
                        "icon": "⚡",
                        "color": "purple",
                        "status": "stable"
                    },
                    {
                        "model_id": "eleven_flash_v2",
                        "name": "Eleven Flash v2",
                        "description": "Ultra-fast model for quick generation. Perfect for rapid prototyping and testing.",
                        "category": "flash",
                        "languages": ["en", "es", "fr", "de", "it", "pt", "pl", "tr", "ru", "nl", "cs", "ar", "zh", "ja", "hi", "ko", "th", "sv", "da", "no", "fi", "el", "hu", "ro", "bg", "hr", "sk", "sl"],
                        "max_characters": 2000,
                        "features": [
                            "Ultra-fast processing",
                            "28 languages supported",
                            "Quick generation",
                            "Rapid prototyping"
                        ],
                        "icon": "💨",
                        "color": "cyan",
                        "status": "stable"
                    },
                    {
                        "model_id": "eleven_express_v2",
                        "name": "Eleven Express v2",
                        "description": "Express model for quick content generation. Good quality with fast processing.",
                        "category": "express",
                        "languages": ["en", "es", "fr", "de", "it", "pt", "pl", "tr", "ru", "nl", "cs", "ar", "zh", "ja", "hi", "ko", "th", "sv", "da", "no", "fi", "el", "hu", "ro", "bg", "hr", "sk", "sl"],
                        "max_characters": 2500,
                        "features": [
                            "Express processing",
                            "28 languages supported",
                            "Quick content generation",
                            "Good quality"
                        ],
                        "icon": "🎯",
                        "color": "indigo",
                        "status": "stable"
                    }
                ]
                return {
                    "success": True,
                    "models": mock_models,
                    "layout": {
                        "columns": 2,
                        "categories": ["all", "multilingual", "monolingual", "turbo", "flash", "express"],
                        "default_category": "all"
                    }
                }
            
            models_data = self.client.get_models()
            return {
                "success": True,
                "models": models_data,
                "layout": {
                    "columns": 2,
                    "categories": ["all", "multilingual", "monolingual", "turbo", "flash", "express"],
                    "default_category": "all"
                }
            }
        except Exception as e:
            logger.error(f"Failed to get models: {e}")
            return {
                "success": False,
                "error": str(e),
                "models": []
            }
    
    async def get_user_usage(self) -> Dict[str, Any]:
        """Get user usage information."""
        try:
            usage_data = self.client.get_usage()
            return {
                "success": True,
                "usage": usage_data
            }
        except Exception as e:
            logger.error(f"Failed to get usage: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def validate_config(self) -> Dict[str, Any]:
        """Validate ElevenLabs configuration."""
        try:
            config_status = self.client.validate_config()
            return {
                "success": True,
                "config": config_status
            }
        except Exception as e:
            logger.error(f"Failed to validate config: {e}")
            return {
                "success": False,
                "error": str(e)
            }
