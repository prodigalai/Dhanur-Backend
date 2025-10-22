#!/usr/bin/env python3
"""
Spotify Content Creation API Routes
Endpoints for audio content creation, playlist management, and analytics
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from core.db import get_db
from controllers.spotify_content_controller import SpotifyContentController
from middleware.auth import get_current_user
from models.sqlalchemy_models import User

router = APIRouter(prefix="/spotify", tags=["Spotify Content"])

# ===== REQUEST MODELS =====

class MoodPlaylistRequest(BaseModel):
    mood: str
    custom_energy: Optional[float] = None
    custom_tempo: Optional[float] = None

class CustomPlaylistRequest(BaseModel):
    name: str
    description: str = ""
    track_queries: Optional[List[str]] = None
    mood: Optional[str] = None
    public: bool = False

class SearchAddRequest(BaseModel):
    playlist_id: str
    search_query: str
    limit: int = 5

class AudioAnalysisRequest(BaseModel):
    track_ids: List[str]

class RecommendationsRequest(BaseModel):
    seed_tracks: Optional[List[str]] = None
    seed_artists: Optional[List[str]] = None
    mood: Optional[str] = None
    limit: int = 20

# ===== PLAYLIST MANAGEMENT ENDPOINTS =====

@router.post("/playlists/mood")
async def create_mood_playlist(
    request: MoodPlaylistRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a mood-based playlist with AI-curated tracks."""
    try:
        result = SpotifyContentController.create_mood_playlist(
            user_id=current_user.id,
            mood=request.mood,
            db_session=db,
            custom_energy=request.custom_energy,
            custom_tempo=request.custom_tempo
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/playlists/custom")
async def create_custom_playlist(
    request: CustomPlaylistRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a custom playlist with optional mood influence."""
    try:
        result = SpotifyContentController.create_custom_playlist(
            user_id=current_user.id,
            db_session=db,
            name=request.name,
            description=request.description,
            track_queries=request.track_queries,
            mood=request.mood,
            public=request.public
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/playlists")
async def get_user_playlists(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's Spotify playlists."""
    try:
        result = SpotifyContentController.get_user_playlists(
            user_id=current_user.id,
            db_session=db,
            limit=limit,
            offset=offset
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/playlists/search-add")
async def search_and_add_to_playlist(
    request: SearchAddRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Search for tracks and add them to a playlist."""
    try:
        result = SpotifyContentController.search_and_add_to_playlist(
            user_id=current_user.id,
            db_session=db,
            playlist_id=request.playlist_id,
            search_query=request.search_query,
            limit=request.limit
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ===== AUDIO ANALYTICS ENDPOINTS =====

@router.get("/analytics/insights")
async def get_user_audio_insights(
    time_range: str = Query("short_term", regex="^(short_term|medium_term|long_term)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get comprehensive audio insights for the user."""
    try:
        result = SpotifyContentController.get_user_audio_insights(
            user_id=current_user.id,
            db_session=db,
            time_range=time_range
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/analytics/report")
async def generate_audio_report(
    time_range: str = Query("short_term", regex="^(short_term|medium_term|long_term)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate a comprehensive audio listening report."""
    try:
        result = SpotifyContentController.generate_audio_report(
            user_id=current_user.id,
            db_session=db,
            time_range=time_range
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/analytics/track-features")
async def analyze_track_audio_features(
    request: AudioAnalysisRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Analyze audio features of specific tracks."""
    try:
        result = SpotifyContentController.analyze_track_audio_features(
            user_id=current_user.id,
            db_session=db,
            track_ids=request.track_ids
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ===== RECOMMENDATIONS ENDPOINTS =====

@router.post("/recommendations")
async def get_audio_recommendations(
    request: RecommendationsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get personalized audio recommendations."""
    try:
        result = SpotifyContentController.get_audio_recommendations(
            user_id=current_user.id,
            db_session=db,
            seed_tracks=request.seed_tracks,
            seed_artists=request.seed_artists,
            mood=request.mood,
            limit=request.limit
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ===== QUICK ACTIONS ENDPOINTS =====

@router.post("/quick/energetic-playlist")
async def create_energetic_playlist(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Quick create an energetic workout playlist."""
    try:
        result = SpotifyContentController.create_mood_playlist(
            user_id=current_user.id,
            mood="energetic",
            db_session=db
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/quick/chill-playlist")
async def create_chill_playlist(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Quick create a chill relaxation playlist."""
    try:
        result = SpotifyContentController.create_mood_playlist(
            user_id=current_user.id,
            mood="chill",
            db_session=db
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/quick/focus-playlist")
async def create_focus_playlist(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Quick create a focus/concentration playlist."""
    try:
        result = SpotifyContentController.create_mood_playlist(
            user_id=current_user.id,
            mood="focused",
            db_session=db
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ===== HEALTH CHECK =====

@router.get("/health")
async def spotify_content_health():
    """Health check for Spotify content endpoints."""
    return {
        "status": "healthy",
        "service": "spotify-content",
        "features": [
            "mood-based playlists",
            "custom playlist creation",
            "audio analytics",
            "track recommendations",
            "audio feature analysis"
        ]
    }
