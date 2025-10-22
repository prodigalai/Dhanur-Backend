#!/usr/bin/env python3
"""
Spotify Content Creation Controller
Handles audio content creation, playlist management, and analytics
"""

import logging
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from providers.spotify.v1.content_ops import SpotifyContentOps
from models.sqlalchemy_models import User, OAuthAccount
from utils.error_handler import (
    ValidationException, AuthenticationException, 
    DatabaseException, ContentCrewException
)

logger = logging.getLogger(__name__)

class SpotifyContentController:
    """Controller for Spotify content creation and management."""
    
    @staticmethod
    def get_spotify_ops(user_id: str, db_session: Session) -> SpotifyContentOps:
        """Get Spotify operations instance for a user."""
        try:
            # Get user's Spotify OAuth account
            oauth_account = db_session.query(OAuthAccount).filter(
                OAuthAccount.user_id == user_id,
                OAuthAccount.provider == "spotify"
            ).first()
            
            if not oauth_account:
                raise AuthenticationException("User not connected to Spotify")
            
            if not oauth_account.access_token:
                raise AuthenticationException("Spotify access token not available")
            
            return SpotifyContentOps(oauth_account.access_token)
            
        except Exception as e:
            logger.error(f"Error getting Spotify ops for user {user_id}: {e}")
            raise
    
    @staticmethod
    def create_mood_playlist(
        user_id: str, 
        mood: str, 
        db_session: Session,
        custom_energy: Optional[float] = None,
        custom_tempo: Optional[float] = None
    ) -> Dict[str, Any]:
        """Create a mood-based playlist for the user."""
        try:
            spotify_ops = SpotifyContentController.get_spotify_ops(user_id, db_session)
            
            # Get user profile for user ID
            user_profile = spotify_ops.get_user_profile()
            spotify_user_id = user_profile['id']
            
            # Create mood playlist
            result = spotify_ops.create_audio_mood_playlist(
                user_id=spotify_user_id,
                mood=mood,
                target_energy=custom_energy,
                target_tempo=custom_tempo
            )
            
            logger.info(f"Created mood playlist for user {user_id}: {mood}")
            return result
            
        except Exception as e:
            logger.error(f"Error creating mood playlist for user {user_id}: {e}")
            raise ContentCrewException(f"Failed to create mood playlist: {str(e)}")
    
    @staticmethod
    def get_user_audio_insights(
        user_id: str, 
        db_session: Session,
        time_range: str = "short_term"
    ) -> Dict[str, Any]:
        """Get comprehensive audio insights for the user."""
        try:
            spotify_ops = SpotifyContentController.get_spotify_ops(user_id, db_session)
            
            insights = spotify_ops.get_user_audio_insights(time_range=time_range)
            
            logger.info(f"Retrieved audio insights for user {user_id}: {time_range}")
            return insights
            
        except Exception as e:
            logger.error(f"Error getting audio insights for user {user_id}: {e}")
            raise ContentCrewException(f"Failed to get audio insights: {str(e)}")
    
    @staticmethod
    def generate_audio_report(
        user_id: str, 
        db_session: Session,
        time_range: str = "short_term"
    ) -> Dict[str, Any]:
        """Generate a comprehensive audio listening report."""
        try:
            spotify_ops = SpotifyContentController.get_spotify_ops(user_id, db_session)
            
            report = spotify_ops.generate_audio_report(time_range=time_range)
            
            logger.info(f"Generated audio report for user {user_id}: {time_range}")
            return report
            
        except Exception as e:
            logger.error(f"Error generating audio report for user {user_id}: {e}")
            raise ContentCrewException(f"Failed to generate audio report: {str(e)}")
    
    @staticmethod
    def create_custom_playlist(
        user_id: str,
        db_session: Session,
        name: str,
        description: str = "",
        track_queries: List[str] = None,
        mood: str = None,
        public: bool = False
    ) -> Dict[str, Any]:
        """Create a custom playlist with optional mood-based recommendations."""
        try:
            spotify_ops = SpotifyContentController.get_spotify_ops(user_id, db_session)
            
            # Get user profile for user ID
            user_profile = spotify_ops.get_user_profile()
            spotify_user_id = user_profile['id']
            
            # Create playlist
            playlist = spotify_ops.create_playlist(
                user_id=spotify_user_id,
                name=name,
                description=description,
                public=public
            )
            
            track_uris = []
            
            # Add tracks from queries if provided
            if track_queries:
                for query in track_queries:
                    search_results = spotify_ops.search_tracks(query, limit=1)
                    if search_results.get('tracks', {}).get('items'):
                        track_uris.append(search_results['tracks']['items'][0]['uri'])
            
            # Add mood-based recommendations if specified
            if mood and not track_queries:
                recommendations = spotify_ops.get_recommendations(limit=20)
                if recommendations.get('tracks'):
                    track_uris = [track['uri'] for track in recommendations['tracks']]
            
            # Add tracks to playlist
            if track_uris:
                spotify_ops.add_tracks_to_playlist(playlist['id'], track_uris)
            
            result = {
                'success': True,
                'playlist': playlist,
                'tracks_added': len(track_uris),
                'creation_method': 'custom'
            }
            
            if mood:
                result['mood_influence'] = mood
            
            logger.info(f"Created custom playlist for user {user_id}: {name}")
            return result
            
        except Exception as e:
            logger.error(f"Error creating custom playlist for user {user_id}: {e}")
            raise ContentCrewException(f"Failed to create custom playlist: {str(e)}")
    
    @staticmethod
    def get_user_playlists(
        user_id: str,
        db_session: Session,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Get user's Spotify playlists."""
        try:
            spotify_ops = SpotifyContentController.get_spotify_ops(user_id, db_session)
            
            playlists = spotify_ops.get_user_playlists(limit=limit, offset=offset)
            
            logger.info(f"Retrieved playlists for user {user_id}")
            return playlists
            
        except Exception as e:
            logger.error(f"Error getting playlists for user {user_id}: {e}")
            raise ContentCrewException(f"Failed to get playlists: {str(e)}")
    
    @staticmethod
    def search_and_add_to_playlist(
        user_id: str,
        db_session: Session,
        playlist_id: str,
        search_query: str,
        limit: int = 5
    ) -> Dict[str, Any]:
        """Search for tracks and add them to a playlist."""
        try:
            spotify_ops = SpotifyContentController.get_spotify_ops(user_id, db_session)
            
            # Search for tracks
            search_results = spotify_ops.search_tracks(search_query, limit=limit)
            
            if not search_results.get('tracks', {}).get('items'):
                return {
                    'success': False,
                    'message': f'No tracks found for query: {search_query}'
                }
            
            # Get track URIs
            track_uris = [track['uri'] for track in search_results['tracks']['items']]
            
            # Add to playlist
            result = spotify_ops.add_tracks_to_playlist(playlist_id, track_uris)
            
            logger.info(f"Added {len(track_uris)} tracks to playlist {playlist_id} for user {user_id}")
            
            return {
                'success': True,
                'tracks_added': len(track_uris),
                'search_query': search_query,
                'playlist_id': playlist_id
            }
            
        except Exception as e:
            logger.error(f"Error searching and adding tracks for user {user_id}: {e}")
            raise ContentCrewException(f"Failed to search and add tracks: {str(e)}")
    
    @staticmethod
    def get_audio_recommendations(
        user_id: str,
        db_session: Session,
        seed_tracks: List[str] = None,
        seed_artists: List[str] = None,
        mood: str = None,
        limit: int = 20
    ) -> Dict[str, Any]:
        """Get personalized audio recommendations."""
        try:
            spotify_ops = SpotifyContentController.get_spotify_ops(user_id, db_session)
            
            # Set default mood parameters if specified
            target_energy = None
            target_tempo = None
            target_danceability = None
            
            if mood:
                mood_params = {
                    'energetic': {'target_energy': 0.8, 'target_tempo': 140, 'target_danceability': 0.8},
                    'chill': {'target_energy': 0.3, 'target_tempo': 80, 'target_danceability': 0.4},
                    'happy': {'target_energy': 0.7, 'target_tempo': 120, 'target_danceability': 0.7},
                    'sad': {'target_energy': 0.2, 'target_tempo': 70, 'target_danceability': 0.3},
                    'focused': {'target_energy': 0.4, 'target_tempo': 90, 'target_danceability': 0.2}
                }
                
                mood_config = mood_params.get(mood.lower(), {})
                target_energy = mood_config.get('target_energy')
                target_tempo = mood_config.get('target_tempo')
                target_danceability = mood_config.get('target_danceability')
            
            recommendations = spotify_ops.get_recommendations(
                seed_tracks=seed_tracks,
                seed_artists=seed_artists,
                target_energy=target_energy,
                target_tempo=target_tempo,
                target_danceability=target_danceability,
                limit=limit
            )
            
            logger.info(f"Generated recommendations for user {user_id}")
            return recommendations
            
        except Exception as e:
            logger.error(f"Error getting recommendations for user {user_id}: {e}")
            raise ContentCrewException(f"Failed to get recommendations: {str(e)}")
    
    @staticmethod
    def analyze_track_audio_features(
        user_id: str,
        db_session: Session,
        track_ids: List[str]
    ) -> Dict[str, Any]:
        """Analyze audio features of specific tracks."""
        try:
            spotify_ops = SpotifyContentController.get_spotify_ops(user_id, db_session)
            
            audio_features = spotify_ops.get_track_audio_features(track_ids)
            
            # Calculate averages for analysis
            if audio_features.get('audio_features'):
                features = audio_features['audio_features']
                avg_features = {
                    'energy': sum(f['energy'] for f in features if f) / len(features),
                    'tempo': sum(f['tempo'] for f in features if f) / len(features),
                    'danceability': sum(f['danceability'] for f in features if f) / len(features),
                    'valence': sum(f['valence'] for f in features if f) / len(features),
                    'acousticness': sum(f['acousticness'] for f in features if f) / len(features)
                }
                
                audio_features['analysis'] = {
                    'average_features': avg_features,
                    'total_tracks': len(features),
                    'mood_analysis': {
                        'energy_level': 'High' if avg_features['energy'] > 0.6 else 'Low',
                        'tempo_category': 'Fast' if avg_features['tempo'] > 120 else 'Slow',
                        'mood_tendency': 'Energetic' if avg_features['valence'] > 0.6 else 'Mellow'
                    }
                }
            
            logger.info(f"Analyzed audio features for {len(track_ids)} tracks for user {user_id}")
            return audio_features
            
        except Exception as e:
            logger.error(f"Error analyzing audio features for user {user_id}: {e}")
            raise ContentCrewException(f"Failed to analyze audio features: {str(e)}")
