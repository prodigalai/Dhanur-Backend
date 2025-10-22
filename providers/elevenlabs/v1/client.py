#!/usr/bin/env python3
"""
ElevenLabs API Client for Content Crew Prodigal
"""

import os
import requests
import logging
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class ElevenLabsClient:
    """ElevenLabs API Client for text-to-speech operations."""
    
    def __init__(self):
        self.api_key = os.getenv("ELEVENLABS_API_KEY") or os.getenv("ELEVENLABS_KEY")
        self.base_url = "https://api.elevenlabs.io/v1"
        self.headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key
        }
        
        if not self.api_key:
            logger.warning("ElevenLabs API key not found in environment variables")
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make authenticated request to ElevenLabs API."""
        if not self.api_key:
            raise ValueError("ElevenLabs API key is required")
        
        url = f"{self.base_url}{endpoint}"
        headers = {**self.headers, **kwargs.pop('headers', {})}
        
        try:
            response = requests.request(method, url, headers=headers, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"ElevenLabs API request failed: {e}")
            raise
    
    def get_voices(self) -> Dict[str, Any]:
        """Get list of available voices."""
        try:
            response = self._make_request("GET", "/voices")
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get voices: {e}")
            raise
    
    def get_voice(self, voice_id: str) -> Dict[str, Any]:
        """Get details of a specific voice."""
        try:
            response = self._make_request("GET", f"/voices/{voice_id}")
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get voice {voice_id}: {e}")
            raise
    
    def text_to_speech(
        self,
        text: str,
        voice_id: str = "21m00Tcm4TlvDq8ikWAM",  # Default voice (Rachel)
        model_id: str = "eleven_monolingual_v1",
        voice_settings: Optional[Dict[str, Any]] = None
    ) -> bytes:
        """
        Convert text to speech using ElevenLabs API.
        
        Args:
            text: Text to convert to speech
            voice_id: ElevenLabs voice ID
            model_id: Model to use for generation
            voice_settings: Voice settings (stability, similarity_boost, etc.)
            
        Returns:
            Audio data as bytes (MP3 format)
        """
        if not text.strip():
            raise ValueError("Text cannot be empty")
        
        # Default voice settings
        if voice_settings is None:
            voice_settings = {
                "stability": 0.5,
                "similarity_boost": 0.5
            }
        
        data = {
            "text": text,
            "model_id": model_id,
            "voice_settings": voice_settings
        }
        
        try:
            response = self._make_request(
                "POST",
                f"/text-to-speech/{voice_id}",
                json=data
            )
            return response.content
        except Exception as e:
            logger.error(f"Text-to-speech conversion failed: {e}")
            raise
    
    def get_models(self) -> Dict[str, Any]:
        """Get list of available models."""
        try:
            response = self._make_request("GET", "/models")
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get models: {e}")
            raise
    
    def get_user_info(self) -> Dict[str, Any]:
        """Get user account information."""
        try:
            response = self._make_request("GET", "/user")
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get user info: {e}")
            raise
    
    def get_usage(self) -> Dict[str, Any]:
        """Get user usage information."""
        try:
            response = self._make_request("GET", "/user/usage")
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get usage info: {e}")
            raise
    
    def validate_config(self) -> Dict[str, bool]:
        """Validate ElevenLabs configuration."""
        return {
            "api_key": bool(self.api_key),
            "base_url": bool(self.base_url),
            "fully_configured": bool(self.api_key)
        }
