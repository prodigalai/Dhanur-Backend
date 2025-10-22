#!/usr/bin/env python3
"""
AI Orchestration Service for Content Crew Prodigal
Handles TTS (Text-to-Speech) integration with external AI services
"""

import os
import logging
import requests
from typing import Dict, Any, Optional
from fastapi import HTTPException
import asyncio
import aiohttp

logger = logging.getLogger(__name__)

class AIOrchestrationService:
    """Service for AI orchestration including TTS functionality."""
    
    def __init__(self):
        self.base_url = os.getenv("AI_ORCHESTRATION_URL", "https://a389b2d990a2.ngrok.app")
        self.timeout = 600  # 10 minutes timeout for long text
        self.max_text_length = 2000  # Maximum text length per request
        
    async def generate_voice(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate voice using AI TTS service.
        
        Args:
            params: Dictionary containing text, language, gender, model
            
        Returns:
            Dictionary with success status and audio data
        """
        text = params.get("text", "")
        language = params.get("language", "english")
        gender = params.get("gender", "male")
        model = params.get("model", "chattrebox")
        
        if not text:
            raise HTTPException(status_code=400, detail="Text is required")
        
        payload = {
            "text": text,
            "language": language,
            "gender": gender,
            "speaker_name": "default"
        }
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.post(
                    f"{self.base_url}/models/{model}/inference",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"TTS generation successful for text length: {len(text)}")
                        return {
                            "success": True,
                            "data": data,
                            "text_length": len(text),
                            "language": language,
                            "gender": gender
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"TTS API error: {response.status} - {error_text}")
                        return {
                            "success": False,
                            "error": f"TTS service error: {response.status}",
                            "details": error_text
                        }
                        
        except asyncio.TimeoutError:
            logger.error("TTS request timeout")
            return {
                "success": False,
                "error": "Request timeout - TTS service took too long to respond"
            }
        except Exception as e:
            logger.error(f"TTS generation error: {str(e)}")
            return {
                "success": False,
                "error": f"TTS service error: {str(e)}"
            }
    
    async def check_health(self) -> Dict[str, Any]:
        """Check health of AI orchestration service."""
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60)) as session:
                async with session.get(f"{self.base_url}/health") as response:
                    if response.status == 200:
                        content_type = response.headers.get('content-type', '')
                        if 'application/json' in content_type:
                            data = await response.json()
                        else:
                            # Handle plain text response
                            text_data = await response.text()
                            data = {"message": text_data}
                        return {
                            "status": "healthy",
                            "service": "AI Orchestration",
                            "url": self.base_url,
                            "details": data
                        }
                    else:
                        return {
                            "status": "unhealthy",
                            "service": "AI Orchestration",
                            "url": self.base_url,
                            "error": f"HTTP {response.status}"
                        }
        except Exception as e:
            return {
                "status": "unhealthy",
                "service": "AI Orchestration",
                "url": self.base_url,
                "error": str(e)
            }
    
    async def get_models(self) -> Dict[str, Any]:
        """Get available AI models."""
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60)) as session:
                async with session.get(self.base_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "success": True,
                            "models": data.get("models", []),
                            "service_url": self.base_url
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"Failed to fetch models: HTTP {response.status}"
                        }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to fetch models: {str(e)}"
            }
    
    def sync_generate_voice(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Synchronous version of generate_voice for non-async contexts."""
        text = params.get("text", "")
        language = params.get("language", "english")
        gender = params.get("gender", "male")
        model = params.get("model", "chattrebox")
        
        if not text:
            return {
                "success": False,
                "error": "Text is required"
            }
        
        # Check if text is too long and needs to be split
        if len(text) > self.max_text_length:
            logger.warning(f"Text length ({len(text)}) exceeds maximum ({self.max_text_length}). Attempting to process anyway...")
            # For now, try to process the full text but with extended timeout
            # In future, we can implement text splitting here
        
        payload = {
            "text": text,
            "language": language,
            "gender": gender,
            "speaker_name": "default"
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/models/{model}/inference",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"TTS generation successful for text length: {len(text)}")
                return {
                    "success": True,
                    "data": data,
                    "text_length": len(text),
                    "language": language,
                    "gender": gender
                }
            else:
                logger.error(f"TTS API error: {response.status_code} - {response.text}")
                return {
                    "success": False,
                    "error": f"TTS service error: {response.status_code}",
                    "details": response.text
                }
                
        except requests.exceptions.Timeout:
            logger.error("TTS request timeout")
            return {
                "success": False,
                "error": "Request timeout - TTS service took too long to respond"
            }
        except Exception as e:
            logger.error(f"TTS generation error: {str(e)}")
            return {
                "success": False,
                "error": f"TTS service error: {str(e)}"
            }
    
    def sync_check_health(self) -> Dict[str, Any]:
        """Synchronous version of check_health."""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=60)
            if response.status_code == 200:
                content_type = response.headers.get('content-type', '')
                if 'application/json' in content_type:
                    data = response.json()
                else:
                    # Handle plain text response
                    data = {"message": response.text}
                return {
                    "status": "healthy",
                    "service": "AI Orchestration",
                    "url": self.base_url,
                    "details": data
                }
            else:
                return {
                    "status": "unhealthy",
                    "service": "AI Orchestration",
                    "url": self.base_url,
                    "error": f"HTTP {response.status_code}"
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "service": "AI Orchestration",
                "url": self.base_url,
                "error": str(e)
            }

# Create singleton instance
ai_orchestration_service = AIOrchestrationService()
