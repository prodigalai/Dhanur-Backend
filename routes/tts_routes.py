#!/usr/bin/env python3
"""
TTS (Text-to-Speech) Routes for Content Crew Prodigal
Handles AI orchestration endpoints for voice generation
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import logging
from datetime import datetime

from services.ai_orchestration_service import ai_orchestration_service
from services.audio_storage_service import audio_storage_service
from services.user_credits_service import user_credits_service
from services.audio_assignment_service import audio_assignment_service
from middleware.auth import get_current_user

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v2/tts", tags=["TTS - Text to Speech"])

# Pydantic models for request/response
class TTSRequest(BaseModel):
    """Request model for TTS generation."""
    text: str = Field(..., min_length=1, max_length=10000, description="Text to convert to speech (max 10000 characters)")
    language: Optional[str] = Field(default="english", description="Language for TTS (english, hindi, etc.)")
    gender: Optional[str] = Field(default="male", description="Voice gender (male, female)")
    model: Optional[str] = Field(default="chattrebox", description="TTS model to use")

class TTSResponse(BaseModel):
    """Response model for TTS generation."""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    text_length: Optional[int] = None
    language: Optional[str] = None
    gender: Optional[str] = None
    timestamp: str

class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str
    service: str
    url: str
    details: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

@router.post("/generate", response_model=TTSResponse)
async def generate_voice(
    request: TTSRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Generate voice from text using AI TTS service.
    
    This endpoint converts text to speech using the integrated AI orchestration service.
    Requires authentication.
    """
    try:
        logger.info(f"TTS generation request from user {current_user.get('user_id', current_user.get('id', 'unknown'))} for text length: {len(request.text)}")
        logger.info(f"DEBUG - current_user keys: {list(current_user.keys()) if current_user else 'None'}")
        logger.info(f"DEBUG - current_user: {current_user}")
        
        # Check text length and provide better error handling
        text_length = len(request.text)
        if text_length > 10000:
            return TTSResponse(
                success=False,
                message="Text too long",
                error=f"Text length ({text_length}) exceeds maximum allowed (10000 characters). Please split your text into smaller chunks.",
                timestamp=datetime.utcnow().isoformat()
            )
        
        # Check user credits before generating voice
        user_id = current_user.get('user_id', current_user.get('id', 'unknown'))
        logger.info(f"DEBUG - extracted user_id: {user_id}")
        credits_info = await user_credits_service.get_user_credits(user_id)
        
        if not credits_info["success"]:
            return TTSResponse(
                success=False,
                message="Failed to check user credits",
                error=credits_info["error"],
                timestamp=datetime.utcnow().isoformat()
            )
        
        current_credits = credits_info["credits"]
        required_credits = max(1, text_length // 50)  # 1 credit per 50 characters, minimum 1
        
        if current_credits < required_credits:
            return TTSResponse(
                success=False,
                message="Insufficient credits",
                error=f"Required: {required_credits} credits, Available: {current_credits} credits",
                timestamp=datetime.utcnow().isoformat()
            )
        
        # Generate voice using AI service
        logger.info(f"Starting TTS generation for {text_length} characters...")
        
        # For long text, use sync version to avoid timeout issues
        if text_length > 1000:
            logger.info(f"Using sync TTS generation for long text ({text_length} characters)")
            result = ai_orchestration_service.sync_generate_voice({
                "text": request.text,
                "language": request.language,
                "gender": request.gender,
                "model": request.model
            })
        else:
            result = await ai_orchestration_service.generate_voice({
            "text": request.text,
            "language": request.language,
            "gender": request.gender,
            "model": request.model
        })
        
        if result["success"]:
            # Deduct credits
            deduct_result = await user_credits_service.deduct_credits(
                user_id,
                required_credits,
                f"TTS generation - {len(request.text)} characters"
            )
            
            if not deduct_result["success"]:
                logger.error(f"Failed to deduct credits: {deduct_result['error']}")
                # Continue with voice generation even if credit deduction fails
            
            # Log successful usage
            logger.info(f"TTS generation successful for user {user_id}, credits deducted: {required_credits}")
            
            # Save audio metadata to MongoDB
            audio_data = result["data"]
            if audio_data and audio_data.get("success"):
                save_result = await audio_storage_service.save_audio_metadata(
                    user_id=user_id,
                    audio_url=audio_data.get("audio_url", ""),
                    text=request.text,
                    language=result["language"],
                    gender=result["gender"],
                    model_used=audio_data.get("voice_info", {}).get("model_used", "chatterbox_real_ai"),
                    processing_time=audio_data.get("processing_time", 0.0),
                    status="completed"
                )
                
                if save_result["success"]:
                    logger.info(f"Audio metadata saved with ID: {save_result.get('audio_id')}")
                else:
                    logger.warning(f"Failed to save audio metadata: {save_result.get('error')}")
            
            return TTSResponse(
                success=True,
                message="Voice generated successfully",
                data=result["data"],
                text_length=result["text_length"],
                language=result["language"],
                gender=result["gender"],
                timestamp=datetime.utcnow().isoformat()
            )
        else:
            error_msg = result.get("error", "Unknown error")
            logger.error(f"TTS generation failed: {error_msg}")
            
            # Check for specific error types
            if "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
                return TTSResponse(
                    success=False,
                    message="Voice generation timed out",
                    error="TTS service timeout. For long text, please try splitting into smaller chunks or try again later.",
                    timestamp=datetime.utcnow().isoformat()
                )
            elif "503" in error_msg or "service unavailable" in error_msg.lower():
                return TTSResponse(
                    success=False,
                    message="TTS service temporarily unavailable",
                    error="The TTS service is currently overloaded. Please try again in a few minutes or use shorter text.",
                    timestamp=datetime.utcnow().isoformat()
                )
            elif "text too long" in error_msg.lower() or "length" in error_msg.lower():
                return TTSResponse(
                    success=False,
                    message="Text too long for processing",
                    error="The text is too long for the TTS service. Please split it into smaller chunks (max 2000 characters per request).",
                    timestamp=datetime.utcnow().isoformat()
                )
            
            return TTSResponse(
                success=False,
                message="Voice generation failed",
                error=f"TTS service error: {error_msg}",
                timestamp=datetime.utcnow().isoformat()
            )
            
    except Exception as e:
        logger.error(f"TTS generation error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@router.post("/generate-long-text", response_model=TTSResponse)
async def generate_voice_long_text(
    request: TTSRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Generate voice from long text using AI TTS service.
    
    This endpoint is optimized for longer text (up to 10000 characters).
    Uses synchronous processing to avoid timeout issues.
    Requires authentication.
    """
    try:
        text_length = len(request.text)
        logger.info(f"Long text TTS generation request from user {current_user.get('user_id', current_user.get('id', 'unknown'))} for text length: {text_length}")
        
        # Check text length
        if text_length > 10000:
            return TTSResponse(
                success=False,
                message="Text too long",
                error=f"Text length ({text_length}) exceeds maximum allowed (10000 characters). Please split your text into smaller chunks.",
                timestamp=datetime.utcnow().isoformat()
            )
        
        # Check user credits
        user_id = current_user.get('user_id', current_user.get('id', 'unknown'))
        credits_info = await user_credits_service.get_user_credits(user_id)
        
        if not credits_info["success"]:
            return TTSResponse(
                success=False,
                message="Failed to check user credits",
                error=credits_info["error"],
                timestamp=datetime.utcnow().isoformat()
            )
        
        current_credits = credits_info["credits"]
        required_credits = max(1, text_length // 50)
        
        if current_credits < required_credits:
            return TTSResponse(
                success=False,
                message="Insufficient credits",
                error=f"Required: {required_credits} credits, Available: {current_credits} credits",
                timestamp=datetime.utcnow().isoformat()
            )
        
        # Use sync generation for long text
        logger.info(f"Starting long text TTS generation for {text_length} characters...")
        result = ai_orchestration_service.sync_generate_voice({
            "text": request.text,
            "language": request.language,
            "gender": request.gender,
            "model": request.model
        })
        
        if result["success"]:
            # Deduct credits
            deduct_result = await user_credits_service.deduct_credits(
                user_id,
                required_credits,
                "TTS generation (long text)"
            )
            
            if not deduct_result["success"]:
                logger.warning(f"Failed to deduct credits: {deduct_result.get('error')}")
            
            # Save audio metadata
            if "data" in result and "audio_url" in result["data"]:
                save_result = await audio_storage_service.save_audio_metadata({
                    "user_id": user_id,
                    "text": request.text,
                    "audio_url": result["data"]["audio_url"],
                    "language": request.language,
                    "gender": request.gender,
                    "model": request.model,
                    "text_length": text_length,
                    "credits_used": required_credits
                })
                
                if not save_result["success"]:
                    logger.warning(f"Failed to save audio metadata: {save_result.get('error')}")
            
            return TTSResponse(
                success=True,
                message="Voice generated successfully (long text)",
                data=result["data"],
                text_length=result["text_length"],
                language=result["language"],
                gender=result["gender"],
                timestamp=datetime.utcnow().isoformat()
            )
        else:
            error_msg = result.get("error", "Unknown error")
            logger.error(f"Long text TTS generation failed: {error_msg}")
            
            return TTSResponse(
                success=False,
                message="Long text voice generation failed",
                error=f"TTS service error: {error_msg}",
                timestamp=datetime.utcnow().isoformat()
            )
            
    except Exception as e:
        logger.error(f"Long text TTS generation error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@router.post("/generate-sync", response_model=TTSResponse)
async def generate_voice_sync(
    request: TTSRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Generate voice from text using AI TTS service (synchronous version).
    
    This endpoint converts text to speech using the integrated AI orchestration service.
    Uses synchronous requests for compatibility with certain environments.
    Requires authentication.
    """
    try:
        logger.info(f"TTS sync generation request from user {current_user.get('user_id', current_user.get('id', 'unknown'))} for text length: {len(request.text)}")
        
        # Generate voice using AI service (sync version)
        result = ai_orchestration_service.sync_generate_voice({
            "text": request.text,
            "language": request.language,
            "gender": request.gender,
            "model": request.model
        })
        
        if result["success"]:
            # Log successful usage
            logger.info(f"TTS sync generation successful for user {current_user.get('user_id', current_user.get('id', 'unknown'))}")
            
            # Save audio metadata to MongoDB
            audio_data = result["data"]
            if audio_data and audio_data.get("success"):
                save_result = await audio_storage_service.save_audio_metadata(
                    user_id=current_user.get('user_id', current_user.get('id', 'unknown')),
                    audio_url=audio_data.get("audio_url", ""),
                    text=request.text,
                    language=result["language"],
                    gender=result["gender"],
                    model_used=audio_data.get("voice_info", {}).get("model_used", "chatterbox_real_ai"),
                    processing_time=audio_data.get("processing_time", 0.0),
                    status="completed"
                )
                
                if save_result["success"]:
                    logger.info(f"Audio metadata saved with ID: {save_result.get('audio_id')}")
                else:
                    logger.warning(f"Failed to save audio metadata: {save_result.get('error')}")
            
            return TTSResponse(
                success=True,
                message="Voice generated successfully (sync)",
                data=result["data"],
                text_length=result["text_length"],
                language=result["language"],
                gender=result["gender"],
                timestamp=datetime.utcnow().isoformat()
            )
        else:
            logger.error(f"TTS sync generation failed: {result.get('error', 'Unknown error')}")
            return TTSResponse(
                success=False,
                message="Voice generation failed (sync)",
                error=result.get("error", "Unknown error"),
                timestamp=datetime.utcnow().isoformat()
            )
            
    except Exception as e:
        logger.error(f"TTS sync generation error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@router.get("/health", response_model=HealthResponse)
async def check_tts_health():
    """
    Check health of TTS service.
    
    This endpoint checks if the AI orchestration service is healthy and responding.
    """
    try:
        health_status = await ai_orchestration_service.check_health()
        
        return HealthResponse(
            status=health_status["status"],
            service=health_status["service"],
            url=health_status["url"],
            details=health_status.get("details"),
            error=health_status.get("error")
        )
        
    except Exception as e:
        logger.error(f"TTS health check error: {str(e)}")
        return HealthResponse(
            status="unhealthy",
            service="AI Orchestration",
            url="unknown",
            error=str(e)
        )

@router.get("/health-sync", response_model=HealthResponse)
async def check_tts_health_sync():
    """
    Check health of TTS service (synchronous version).
    
    This endpoint checks if the AI orchestration service is healthy and responding.
    Uses synchronous requests for compatibility.
    """
    try:
        health_status = ai_orchestration_service.sync_check_health()
        
        return HealthResponse(
            status=health_status["status"],
            service=health_status["service"],
            url=health_status["url"],
            details=health_status.get("details"),
            error=health_status.get("error")
        )
        
    except Exception as e:
        logger.error(f"TTS sync health check error: {str(e)}")
        return HealthResponse(
            status="unhealthy",
            service="AI Orchestration",
            url="unknown",
            error=str(e)
        )

@router.get("/models")
async def get_available_models():
    """
    Get available TTS models.
    
    This endpoint returns the list of available TTS models from the AI orchestration service.
    """
    try:
        models_result = await ai_orchestration_service.get_models()
        
        if models_result["success"]:
            return {
                "success": True,
                "models": models_result["models"],
                "service_url": models_result["service_url"],
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            return {
                "success": False,
                "error": models_result["error"],
                "timestamp": datetime.utcnow().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Get models error: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

@router.get("/status")
async def get_tts_status():
    """
    Get TTS service status and configuration.
    
    This endpoint returns the current status and configuration of the TTS service.
    """
    try:
        return {
            "service": "TTS - Text to Speech",
            "status": "active",
            "ai_service_url": ai_orchestration_service.base_url,
            "timeout": ai_orchestration_service.timeout,
            "features": [
                "Text to Speech Generation",
                "Multiple Language Support",
                "Gender Selection",
                "Model Selection",
                "Health Monitoring",
                "Async and Sync Support"
            ],
            "endpoints": [
                "POST /api/v2/tts/generate - Generate voice (async)",
                "POST /api/v2/tts/generate-sync - Generate voice (sync)",
                "GET /api/v2/tts/health - Check health (async)",
                "GET /api/v2/tts/health-sync - Check health (sync)",
                "GET /api/v2/tts/models - Get available models",
                "GET /api/v2/tts/status - Get service status"
            ],
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"TTS status error: {str(e)}")
        return {
            "service": "TTS - Text to Speech",
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

# Audio Storage Endpoints
@router.get("/audios", response_model=Dict[str, Any])
async def get_user_audios(
    current_user: dict = Depends(get_current_user),
    limit: int = 50,
    skip: int = 0,
    language: Optional[str] = None,
    status: Optional[str] = None
):
    """
    Get user's audio files from both TTS and ElevenLabs collections.
    
    This endpoint retrieves all audio files generated by the authenticated user
    from both TTS (Text-to-Speech) and ElevenLabs services. Supports pagination 
    and filtering by language and status.
    
    Returns:
    - audio_files: List of all audio files (TTS + ElevenLabs)
    - total_count: Total count from both collections
    - tts_count: Count from TTS collection only
    - elevenlabs_count: Count from ElevenLabs collection only
    """
    try:
        result = await audio_storage_service.get_user_audios(
            user_id=current_user.get('user_id', current_user.get('id', 'unknown')),
            limit=limit,
            skip=skip,
            language=language,
            status=status
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to get user audios: {str(e)}")
        return {
            "success": False,
            "error": f"Failed to get user audios: {str(e)}"
        }

@router.get("/audios/{audio_id}", response_model=Dict[str, Any])
async def get_audio_by_id(
    audio_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get specific audio file by ID from both TTS and ElevenLabs collections.
    
    This endpoint retrieves a specific audio file by its ID from either
    TTS or ElevenLabs collections. Only returns audio files belonging 
    to the authenticated user.
    
    Returns:
    - audio_file: The requested audio file data
    - source: "tts" or "elevenlabs" indicating the source collection
    """
    try:
        result = await audio_storage_service.get_audio_by_id(
            audio_id=audio_id,
            user_id=current_user.get('user_id', current_user.get('id', 'unknown'))
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to get audio by ID: {str(e)}")
        return {
            "success": False,
            "error": f"Failed to get audio by ID: {str(e)}"
        }

@router.delete("/audios/{audio_id}", response_model=Dict[str, Any])
async def delete_audio(
    audio_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete audio file metadata.
    
    This endpoint deletes the metadata of a specific audio file.
    Only allows deletion of audio files belonging to the authenticated user.
    """
    try:
        result = await audio_storage_service.delete_audio(
            audio_id=audio_id,
            user_id=current_user.get('user_id', current_user.get('id', 'unknown'))
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to delete audio: {str(e)}")
        return {
            "success": False,
            "error": f"Failed to delete audio: {str(e)}"
        }

@router.get("/audios/statistics", response_model=Dict[str, Any])
async def get_audio_statistics(
    current_user: dict = Depends(get_current_user)
):
    """
    Get audio generation statistics for the user from both TTS and ElevenLabs.
    
    This endpoint returns comprehensive statistics about the user's audio 
    generation activity from both TTS and ElevenLabs services, including 
    total counts, language distribution, and recent activity.
    
    Returns:
    - total_audios: Total count from both collections
    - tts_audios: Count from TTS collection only
    - elevenlabs_audios: Count from ElevenLabs collection only
    - recent_audios_30_days: Recent activity from both collections
    - language_distribution: Language breakdown including ElevenLabs
    """
    try:
        result = await audio_storage_service.get_audio_statistics(
            user_id=current_user.get('user_id', current_user.get('id', 'unknown'))
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to get audio statistics: {str(e)}")
        return {
            "success": False,
            "error": f"Failed to get audio statistics: {str(e)}"
        }

# Audio Assignment Models
class AudioAssignmentRequest(BaseModel):
    """Request model for assigning audio to brand."""
    audio_id: str = Field(..., description="ID of the audio to assign")
    brand_id: str = Field(..., description="ID of the brand to assign to")
    campaign_id: Optional[str] = Field(None, description="Optional campaign ID")
    notes: Optional[str] = Field(None, description="Optional notes about the assignment")

class AudioUnassignmentRequest(BaseModel):
    """Request model for unassigning audio from brand."""
    audio_id: str = Field(..., description="ID of the audio to unassign")
    brand_id: str = Field(..., description="ID of the brand to unassign from")

# Audio Assignment Endpoints
@router.post("/audios/assign", response_model=Dict[str, Any])
async def assign_audio_to_brand(
    request: AudioAssignmentRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Assign an audio to a brand (and optionally to a campaign).
    
    This endpoint allows users to assign their generated audios to specific brands.
    The audio will then be visible in the brand's audio library.
    """
    try:
        user_id = current_user.get('user_id', current_user.get('id', 'unknown'))
        
        result = await audio_assignment_service.assign_audio_to_brand(
            audio_id=request.audio_id,
            brand_id=request.brand_id,
            user_id=user_id,
            assigned_by=user_id,
            campaign_id=request.campaign_id,
            notes=request.notes
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to assign audio to brand: {str(e)}")
        return {
            "success": False,
            "error": f"Failed to assign audio to brand: {str(e)}"
        }

@router.post("/audios/unassign", response_model=Dict[str, Any])
async def unassign_audio_from_brand(
    request: AudioUnassignmentRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Unassign an audio from a brand.
    
    This endpoint allows users to remove their audios from brand assignments.
    """
    try:
        user_id = current_user.get('user_id', current_user.get('id', 'unknown'))
        
        result = await audio_assignment_service.unassign_audio_from_brand(
            audio_id=request.audio_id,
            brand_id=request.brand_id,
            user_id=user_id
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to unassign audio from brand: {str(e)}")
        return {
            "success": False,
            "error": f"Failed to unassign audio from brand: {str(e)}"
        }

@router.get("/audios/assignments", response_model=Dict[str, Any])
async def get_user_audio_assignments(
    current_user: dict = Depends(get_current_user),
    limit: int = 50,
    skip: int = 0,
    status: str = "active"
):
    """
    Get all audio assignments for the current user.
    
    This endpoint returns all audio assignments made by the authenticated user.
    """
    try:
        user_id = current_user.get('user_id', current_user.get('id', 'unknown'))
        
        result = await audio_assignment_service.get_user_audio_assignments(
            user_id=user_id,
            limit=limit,
            skip=skip,
            status=status
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to get user audio assignments: {str(e)}")
        return {
            "success": False,
            "error": f"Failed to get user audio assignments: {str(e)}"
        }

@router.get("/audios/{audio_id}/assignments", response_model=Dict[str, Any])
async def get_audio_assignments(
    audio_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get all assignments for a specific audio.
    
    This endpoint returns all brand assignments for a specific audio file.
    """
    try:
        user_id = current_user.get('user_id', current_user.get('id', 'unknown'))
        
        result = await audio_assignment_service.get_audio_assignments(
            audio_id=audio_id,
            user_id=user_id
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to get audio assignments: {str(e)}")
        return {
            "success": False,
            "error": f"Failed to get audio assignments: {str(e)}"
        }
