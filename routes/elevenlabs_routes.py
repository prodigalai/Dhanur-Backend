#!/usr/bin/env python3
"""
ElevenLabs API Routes for Content Crew Prodigal
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from starlette import status
from starlette.responses import Response
import base64

from middleware.auth import get_current_user
from providers.elevenlabs.v1.ops import ElevenLabsOps
from services.user_credits_service import user_credits_service

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize ElevenLabs operations
elevenlabs_ops = ElevenLabsOps()

@router.post("/generate", response_model=Dict[str, Any])
async def generate_speech(
    text: str = Body(..., description="Text to convert to speech"),
    voice_id: str = Body("21m00Tcm4TlvDq8ikWAM", description="ElevenLabs voice ID"),
    model_id: str = Body("eleven_monolingual_v1", description="Model ID"),
    voice_settings: Optional[Dict[str, Any]] = Body(None, description="Voice settings"),
    brand_id: Optional[str] = Body(None, description="Brand ID for tracking"),
    current_user: dict = Depends(get_current_user)
):
    """Generate speech from text using ElevenLabs."""
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        if not text.strip():
            raise HTTPException(status_code=400, detail="Text cannot be empty")
        
        result = await elevenlabs_ops.generate_speech(
            text=text,
            voice_id=voice_id,
            model_id=model_id,
            voice_settings=voice_settings,
            user_id=user_id,
            brand_id=brand_id,
            save_to_db=True
        )
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])
        
        # Get updated credits after generation
        updated_credits = await user_credits_service.get_user_credits(user_id)
        current_credits = updated_credits.get("credits", 0) if updated_credits["success"] else 0
        
        return {
            "success": True,
            "message": "Speech generated successfully",
            "data": {
                "audio_id": result.get("audio_id"),
                "audio_size": result["audio_size"],
                "voice_id": result["voice_id"],
                "model_id": result["model_id"],
                "text_length": result["text_length"],
                "generated_at": result["generated_at"],
                "credits_used": result.get("credits_used", 0),
                "remaining_credits": current_credits
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating speech: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate speech: {str(e)}")

@router.get("/audios", response_model=Dict[str, Any])
async def get_user_audios(
    current_user: dict = Depends(get_current_user),
    brand_id: Optional[str] = Query(None, description="Filter by brand ID"),
    limit: int = Query(20, description="Number of audios to return"),
    skip: int = Query(0, description="Number of audios to skip")
):
    """Get user's generated audios."""
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        result = await elevenlabs_ops.get_user_audios(
            user_id=user_id,
            brand_id=brand_id,
            limit=limit,
            skip=skip
        )
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return {
            "success": True,
            "message": "Audios retrieved successfully",
            "data": {
                "audios": result["audios"],
                "total": result["total"],
                "returned": result["returned"],
                "limit": result["limit"],
                "skip": result["skip"]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user audios: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get audios: {str(e)}")

@router.get("/audio/{audio_id}", response_model=Dict[str, Any])
async def get_audio(
    audio_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get specific audio by ID."""
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        result = await elevenlabs_ops.get_audio_by_id(audio_id, user_id)
        
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result["error"])
        
        return {
            "success": True,
            "message": "Audio retrieved successfully",
            "data": result["audio"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting audio {audio_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get audio: {str(e)}")

@router.get("/audio/{audio_id}/download")
async def download_audio(
    audio_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Download audio file."""
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        result = await elevenlabs_ops.get_audio_by_id(audio_id, user_id)
        
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result["error"])
        
        audio_data = result["audio"]["audio_data"]
        audio_bytes = base64.b64decode(audio_data)
        
        return Response(
            content=audio_bytes,
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": f"attachment; filename={audio_id}.mp3"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading audio {audio_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to download audio: {str(e)}")

@router.delete("/audio/{audio_id}", response_model=Dict[str, Any])
async def delete_audio(
    audio_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete audio by ID."""
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        result = await elevenlabs_ops.delete_audio(audio_id, user_id)
        
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result["error"])
        
        return {
            "success": True,
            "message": result["message"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting audio {audio_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete audio: {str(e)}")

@router.get("/voices", response_model=Dict[str, Any])
async def get_voices():
    """Get available voices from ElevenLabs."""
    try:
        result = await elevenlabs_ops.get_voices()
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return {
            "success": True,
            "message": "Voices retrieved successfully",
            "data": {
                "voices": result["voices"]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting voices: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get voices: {str(e)}")

@router.get("/models", response_model=Dict[str, Any])
async def get_models():
    """Get available models from ElevenLabs."""
    try:
        result = await elevenlabs_ops.get_models()
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return {
            "success": True,
            "message": "Models retrieved successfully",
            "data": {
                "models": result["models"]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting models: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get models: {str(e)}")

@router.get("/usage", response_model=Dict[str, Any])
async def get_usage(current_user: dict = Depends(get_current_user)):
    """Get user usage information."""
    try:
        result = await elevenlabs_ops.get_user_usage()
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return {
            "success": True,
            "message": "Usage retrieved successfully",
            "data": result["usage"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting usage: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get usage: {str(e)}")

@router.get("/config", response_model=Dict[str, Any])
async def get_config():
    """Get ElevenLabs configuration status."""
    try:
        result = await elevenlabs_ops.validate_config()
        
        return {
            "success": True,
            "message": "Configuration status retrieved",
            "data": result
        }
        
    except Exception as e:
        logger.error(f"Error getting config: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get config: {str(e)}")

@router.get("/credits", response_model=Dict[str, Any])
async def get_user_credits(current_user: dict = Depends(get_current_user)):
    """Get user's current credits."""
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        credits_result = await user_credits_service.get_user_credits(user_id)
        
        if not credits_result["success"]:
            raise HTTPException(status_code=500, detail=credits_result["error"])
        
        return {
            "success": True,
            "message": "Credits retrieved successfully",
            "data": {
                "credits": credits_result["credits"],
                "total_earned": credits_result["total_earned"],
                "total_spent": credits_result["total_spent"],
                "voice_generation_cost": 10
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user credits: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get credits: {str(e)}")

@router.get("/credits/history", response_model=Dict[str, Any])
async def get_credit_history(
    current_user: dict = Depends(get_current_user),
    limit: int = Query(20, description="Number of history entries to return")
):
    """Get user's credit history."""
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        history_result = await user_credits_service.get_credit_history(user_id, limit)
        
        if not history_result["success"]:
            raise HTTPException(status_code=500, detail=history_result["error"])
        
        return {
            "success": True,
            "message": "Credit history retrieved successfully",
            "data": {
                "current_credits": history_result["current_credits"],
                "total_earned": history_result["total_earned"],
                "total_spent": history_result["total_spent"],
                "history": history_result["history"],
                "history_count": history_result["history_count"]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting credit history: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get credit history: {str(e)}")
