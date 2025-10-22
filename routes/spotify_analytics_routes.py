#!/usr/bin/env python3
"""
Spotify Analytics & Growth API Routes
Endpoints for analytics data collection, growth tracking, and automated insights
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import logging

from core.db import get_db
from controllers.spotify_analytics_controller import SpotifyAnalyticsController
from providers.spotify.v1.analytics_ops import SpotifyAnalyticsOps
from middleware.auth import get_current_user
from models.sqlalchemy_models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/spotify-analytics", tags=["Spotify Analytics"])

# ===== REQUEST MODELS =====

class TrackAnalyticsRequest(BaseModel):
    track_ids: List[str]
    store_snapshot: bool = True
    calculate_growth: bool = True

class ArtistAnalyticsRequest(BaseModel):
    artist_ids: List[str]
    store_snapshot: bool = True
    calculate_growth: bool = True

class PlaylistAnalyticsRequest(BaseModel):
    playlist_ids: List[str]
    store_snapshot: bool = True
    calculate_growth: bool = True

class AudioFeaturesRequest(BaseModel):
    track_ids: List[str]
    store_features: bool = True

class SearchRequest(BaseModel):
    query: str
    search_type: str = "track"  # track, artist, album, playlist
    market: str = "US"
    limit: int = 20

class GrowthMetricsRequest(BaseModel):
    entity_type: str  # track, artist, playlist
    entity_id: str

# ===== TRACK ANALYTICS ENDPOINTS =====

@router.post("/tracks/popularity")
async def get_tracks_popularity(
    request: TrackAnalyticsRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get popularity data for multiple tracks and optionally store snapshots."""
    try:
        # Get client credentials token for public data access
        spotify_ops = SpotifyAnalyticsOps()
        client_id = "YOUR_SPOTIFY_CLIENT_ID"  # Get from environment
        client_secret = "YOUR_SPOTIFY_CLIENT_SECRET"  # Get from environment
        
        # Get tracks popularity
        tracks_data = spotify_ops.get_multiple_tracks_popularity(request.track_ids)
        
        # Store snapshots in background if requested
        if request.store_snapshot:
            analytics_controller = SpotifyAnalyticsController(db)
            for track in tracks_data['tracks']:
                background_tasks.add_task(
                    analytics_controller.store_track_popularity_snapshot, track
                )
        
        # Calculate growth metrics in background if requested
        if request.calculate_growth:
            analytics_controller = SpotifyAnalyticsController(db)
            for track in tracks_data['tracks']:
                background_tasks.add_task(
                    analytics_controller.calculate_and_store_growth_metrics, 'track', track['track_id']
                )
        
        return {
            "success": True,
            "data": tracks_data,
            "snapshots_stored": request.store_snapshot,
            "growth_calculated": request.calculate_growth
        }
        
    except Exception as e:
        logger.error(f"Error getting tracks popularity: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/tracks/{track_id}/trend")
async def get_track_popularity_trend(
    track_id: str,
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get popularity trend for a specific track over time."""
    try:
        analytics_controller = SpotifyAnalyticsController(db)
        trend_data = analytics_controller.get_track_popularity_trend(track_id, days)
        
        if 'error' in trend_data:
            raise HTTPException(status_code=404, detail=trend_data['error'])
        
        return trend_data
        
    except Exception as e:
        logger.error(f"Error getting track popularity trend: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/tracks/{track_id}/audio-features")
async def get_track_audio_features(
    track_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get audio features for a specific track."""
    try:
        spotify_ops = SpotifyAnalyticsOps()
        features_data = spotify_ops.get_track_audio_features(track_id)
        
        return features_data
        
    except Exception as e:
        logger.error(f"Error getting track audio features: {e}")
        raise HTTPException(status_code=400, detail=str(e))

# ===== ARTIST ANALYTICS ENDPOINTS =====

@router.post("/artists/analytics")
async def get_artists_analytics(
    request: ArtistAnalyticsRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get analytics data for multiple artists and optionally store snapshots."""
    try:
        spotify_ops = SpotifyAnalyticsOps()
        artists_data = spotify_ops.get_multiple_artists_analytics(request.artist_ids)
        
        # Store snapshots in background if requested
        if request.store_snapshot:
            analytics_controller = SpotifyAnalyticsController(db)
            for artist in artists_data['artists']:
                background_tasks.add_task(
                    analytics_controller.store_artist_analytics_snapshot, artist
                )
        
        # Calculate growth metrics in background if requested
        if request.calculate_growth:
            analytics_controller = SpotifyAnalyticsController(db)
            for artist in artists_data['artists']:
                background_tasks.add_task(
                    analytics_controller.calculate_and_store_growth_metrics, 'artist', artist['artist_id']
                )
        
        return {
            "success": True,
            "data": artists_data,
            "snapshots_stored": request.store_snapshot,
            "growth_calculated": request.calculate_growth
        }
        
    except Exception as e:
        logger.error(f"Error getting artists analytics: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/artists/{artist_id}/growth-report")
async def get_artist_growth_report(
    artist_id: str,
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get comprehensive growth report for an artist."""
    try:
        analytics_controller = SpotifyAnalyticsController(db)
        growth_report = analytics_controller.get_artist_growth_report(artist_id, days)
        
        if 'error' in growth_report:
            raise HTTPException(status_code=404, detail=growth_report['error'])
        
        return growth_report
        
    except Exception as e:
        logger.error(f"Error getting artist growth report: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/artists/{artist_id}/top-tracks")
async def get_artist_top_tracks(
    artist_id: str,
    market: str = Query("US", regex="^[A-Z]{2}$"),
    current_user: User = Depends(get_current_user)
):
    """Get top tracks for an artist by market."""
    try:
        spotify_ops = SpotifyAnalyticsOps()
        top_tracks = spotify_ops.get_artist_top_tracks(artist_id, market)
        
        return top_tracks
        
    except Exception as e:
        logger.error(f"Error getting artist top tracks: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/artists/{artist_id}/related")
async def get_related_artists(
    artist_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get related artists for discovery and growth opportunities."""
    try:
        spotify_ops = SpotifyAnalyticsOps()
        related_artists = spotify_ops.get_related_artists(artist_id)
        
        return related_artists
        
    except Exception as e:
        logger.error(f"Error getting related artists: {e}")
        raise HTTPException(status_code=400, detail=str(e))

# ===== PLAYLIST ANALYTICS ENDPOINTS =====

@router.post("/playlists/analytics")
async def get_playlists_analytics(
    request: PlaylistAnalyticsRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get analytics data for multiple playlists and optionally store snapshots."""
    try:
        spotify_ops = SpotifyAnalyticsOps()
        playlists_data = []
        
        for playlist_id in request.playlist_ids:
            playlist_data = spotify_ops.get_playlist_analytics(playlist_id)
            playlists_data.append(playlist_data)
        
        # Store snapshots in background if requested
        if request.store_snapshot:
            analytics_controller = SpotifyAnalyticsController(db)
            for playlist_data in playlists_data:
                background_tasks.add_task(
                    analytics_controller.store_playlist_analytics_snapshot, playlist_data
                )
        
        # Calculate growth metrics in background if requested
        if request.calculate_growth:
            analytics_controller = SpotifyAnalyticsController(db)
            for playlist_data in playlists_data:
                background_tasks.add_task(
                    analytics_controller.calculate_and_store_growth_metrics, 'playlist', playlist_data['playlist_id']
                )
        
        return {
            "success": True,
            "data": playlists_data,
            "snapshots_stored": request.store_snapshot,
            "growth_calculated": request.calculate_growth
        }
        
    except Exception as e:
        logger.error(f"Error getting playlists analytics: {e}")
        raise HTTPException(status_code=400, detail=str(e))

# ===== AUDIO FEATURES ENDPOINTS =====

@router.post("/audio-features/batch")
async def get_multiple_tracks_audio_features(
    request: AudioFeaturesRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get audio features for multiple tracks and optionally store them."""
    try:
        spotify_ops = SpotifyAnalyticsOps()
        features_data = spotify_ops.get_multiple_tracks_audio_features(request.track_ids)
        
        # Store features in background if requested
        if request.store_features:
            analytics_controller = SpotifyAnalyticsController(db)
            for track_features in features_data['tracks_features']:
                background_tasks.add_task(
                    analytics_controller.store_track_audio_features, track_features
                )
        
        return {
            "success": True,
            "data": features_data,
            "features_stored": request.store_features
        }
        
    except Exception as e:
        logger.error(f"Error getting multiple tracks audio features: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/audio-features/{track_id}/analysis")
async def get_track_audio_analysis(
    track_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get detailed audio analysis for a track."""
    try:
        spotify_ops = SpotifyAnalyticsOps()
        analysis_data = spotify_ops.get_track_audio_analysis(track_id)
        
        return analysis_data
        
    except Exception as e:
        logger.error(f"Error getting track audio analysis: {e}")
        raise HTTPException(status_code=400, detail=str(e))

# ===== SEARCH & DISCOVERY ENDPOINTS =====

@router.post("/search")
async def search_spotify_content(
    request: SearchRequest,
    current_user: User = Depends(get_current_user)
):
    """Search for tracks, artists, albums, or playlists."""
    try:
        spotify_ops = SpotifyAnalyticsOps()
        
        if request.search_type == "track":
            search_results = spotify_ops.search_tracks_by_name(
                request.query, market=request.market, limit=request.limit
            )
        else:
            # For other types, use generic search
            search_results = spotify_ops.search_tracks_by_name(
                request.query, market=request.market, limit=request.limit
            )
        
        return search_results
        
    except Exception as e:
        logger.error(f"Error searching Spotify content: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/search/isrc/{isrc}")
async def search_by_isrc(
    isrc: str,
    market: str = Query("US", regex="^[A-Z]{2}$"),
    current_user: User = Depends(get_current_user)
):
    """Search for tracks by ISRC code."""
    try:
        spotify_ops = SpotifyAnalyticsOps()
        search_results = spotify_ops.search_tracks_by_isrc(isrc, market)
        
        return search_results
        
    except Exception as e:
        logger.error(f"Error searching by ISRC: {e}")
        raise HTTPException(status_code=400, detail=str(e))

# ===== GROWTH METRICS ENDPOINTS =====

@router.post("/growth-metrics/calculate")
async def calculate_growth_metrics(
    request: GrowthMetricsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Calculate and store growth metrics for an entity."""
    try:
        analytics_controller = SpotifyAnalyticsController(db)
        growth_metrics = analytics_controller.calculate_and_store_growth_metrics(
            request.entity_type, request.entity_id
        )
        
        return growth_metrics
        
    except Exception as e:
        logger.error(f"Error calculating growth metrics: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/growth-metrics/{entity_type}/{entity_id}")
async def get_growth_metrics(
    entity_type: str,
    entity_id: str,
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get growth metrics for an entity over time."""
    try:
        # Get growth metrics from database
        metrics = db.execute(text("""
            SELECT metric_type, current_value, previous_value, change_amount, change_percentage, analysis_date
            FROM spotify_growth_metrics
            WHERE entity_type = :entity_type 
            AND entity_id = :entity_id
            AND analysis_date >= CURRENT_DATE - INTERVAL ':days days'
            ORDER BY analysis_date DESC
        """), {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "days": days
        }).fetchall()
        
        if not metrics:
            raise HTTPException(status_code=404, detail="No growth metrics found")
        
        return {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "analysis_period_days": days,
            "metrics": [
                {
                    "metric_type": m.metric_type,
                    "current_value": float(m.current_value) if m.current_value else 0,
                    "previous_value": float(m.previous_value) if m.previous_value else 0,
                    "change_amount": float(m.change_amount) if m.change_amount else 0,
                    "change_percentage": float(m.change_percentage) if m.change_percentage else 0,
                    "analysis_date": m.analysis_date.isoformat()
                } for m in metrics
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting growth metrics: {e}")
        raise HTTPException(status_code=400, detail=str(e))

# ===== DASHBOARD ENDPOINTS =====

@router.get("/dashboard/summary")
async def get_analytics_dashboard_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get summary data for analytics dashboard."""
    try:
        analytics_controller = SpotifyAnalyticsController(db)
        dashboard_summary = analytics_controller.get_dashboard_summary()
        
        return dashboard_summary
        
    except Exception as e:
        logger.error(f"Error getting dashboard summary: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/dashboard/top-performers")
async def get_top_performers(
    entity_type: str = Query("track", regex="^(track|artist|playlist)$"),
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get top performing entities for dashboard."""
    try:
        if entity_type == "track":
            # Get top tracks by popularity
            top_entities = db.execute(text("""
                SELECT t.name, a.name as artist_name, ts.popularity
                FROM spotify_current_track_popularity ts
                JOIN spotify_tracks t ON ts.track_id = t.id
                JOIN spotify_artists a ON t.artist_id = a.id
                ORDER BY ts.popularity DESC
                LIMIT :limit
            """), {"limit": limit}).fetchall()
            
            entities = [
                {
                    "name": row.name,
                    "artist": row.artist_name,
                    "popularity": row.popularity
                } for row in top_entities
            ]
            
        elif entity_type == "artist":
            # Get top artists by followers
            top_entities = db.execute(text("""
                SELECT a.name, s.followers_total
                FROM spotify_current_artist_analytics s
                JOIN spotify_artists a ON s.artist_id = a.id
                ORDER BY s.followers_total DESC
                LIMIT :limit
            """), {"limit": limit}).fetchall()
            
            entities = [
                {
                    "name": row.name,
                    "followers": row.followers_total
                } for row in top_entities
            ]
            
        else:  # playlist
            # Get top playlists by followers
            top_entities = db.execute(text("""
                SELECT p.name, s.followers_total
                FROM spotify_current_playlist_analytics s
                JOIN spotify_playlists p ON s.playlist_id = p.id
                ORDER BY s.followers_total DESC
                LIMIT :limit
            """), {"limit": limit}).fetchall()
            
            entities = [
                {
                    "name": row.name,
                    "followers": row.followers_total
                } for row in top_entities
            ]
        
        return {
            "entity_type": entity_type,
            "top_entities": entities,
            "limit": limit
        }
        
    except Exception as e:
        logger.error(f"Error getting top performers: {e}")
        raise HTTPException(status_code=400, detail=str(e))

# ===== HEALTH CHECK =====

@router.get("/health")
async def spotify_analytics_health():
    """Health check for Spotify analytics endpoints."""
    return {
        "status": "healthy",
        "service": "spotify-analytics",
        "features": [
            "Track popularity tracking",
            "Artist growth analytics",
            "Playlist engagement metrics",
            "Audio features analysis",
            "Growth metrics calculation",
            "Automated insights",
            "Dashboard data aggregation"
        ]
    }
