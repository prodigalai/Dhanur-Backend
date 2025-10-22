#!/usr/bin/env python3
"""
Spotify Content Creation Operations
Audio file uploads, playlist management, and audio analytics
"""

import requests
import json
import base64
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class SpotifyContentOps:
    """Spotify content creation and management operations."""
    
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.base_url = "https://api.spotify.com/v1"
        self.headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
    
    # ===== USER PROFILE & ANALYTICS =====
    
    def get_user_profile(self) -> Dict[str, Any]:
        """Get current user profile information."""
        try:
            response = requests.get(f"{self.base_url}/me", headers=self.headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting user profile: {e}")
            raise
    
    def get_user_top_tracks(self, time_range: str = "short_term", limit: int = 20) -> Dict[str, Any]:
        """Get user's top tracks with analytics."""
        try:
            params = {
                'time_range': time_range,  # short_term, medium_term, long_term
                'limit': limit
            }
            response = requests.get(f"{self.base_url}/me/top/tracks", 
                                 headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting top tracks: {e}")
            raise
    
    def get_user_top_artists(self, time_range: str = "short_term", limit: int = 20) -> Dict[str, Any]:
        """Get user's top artists with analytics."""
        try:
            params = {
                'time_range': time_range,
                'limit': limit
            }
            response = requests.get(f"{self.base_url}/me/top/artists", 
                                 headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting top artists: {e}")
            raise
    
    def get_user_recently_played(self, limit: int = 20) -> Dict[str, Any]:
        """Get user's recently played tracks."""
        try:
            params = {'limit': limit}
            response = requests.get(f"{self.base_url}/me/player/recently-played", 
                                 headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting recently played: {e}")
            raise
    
    # ===== PLAYLIST MANAGEMENT =====
    
    def create_playlist(self, user_id: str, name: str, description: str = "", 
                       public: bool = False, collaborative: bool = False) -> Dict[str, Any]:
        """Create a new playlist for the user."""
        try:
            playlist_data = {
                'name': name,
                'description': description,
                'public': public,
                'collaborative': collaborative
            }
            
            response = requests.post(f"{self.base_url}/users/{user_id}/playlists", 
                                  headers=self.headers, json=playlist_data)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error creating playlist: {e}")
            raise
    
    def add_tracks_to_playlist(self, playlist_id: str, track_uris: List[str]) -> Dict[str, Any]:
        """Add tracks to an existing playlist."""
        try:
            data = {'uris': track_uris}
            response = requests.post(f"{self.base_url}/playlists/{playlist_id}/tracks", 
                                  headers=self.headers, json=data)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error adding tracks to playlist: {e}")
            raise
    
    def get_user_playlists(self, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """Get user's playlists."""
        try:
            params = {'limit': limit, 'offset': offset}
            response = requests.get(f"{self.base_url}/me/playlists", 
                                 headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting user playlists: {e}")
            raise
    
    def update_playlist(self, playlist_id: str, name: str = None, 
                       description: str = None, public: bool = None) -> Dict[str, Any]:
        """Update playlist details."""
        try:
            update_data = {}
            if name is not None:
                update_data['name'] = name
            if description is not None:
                update_data['description'] = description
            if public is not None:
                update_data['public'] = public
            
            response = requests.put(f"{self.base_url}/playlists/{playlist_id}", 
                                 headers=self.headers, json=update_data)
            response.raise_for_status()
            return {'success': True, 'message': 'Playlist updated successfully'}
        except Exception as e:
            logger.error(f"Error updating playlist: {e}")
            raise
    
    # ===== AUDIO CONTENT SEARCH & DISCOVERY =====
    
    def search_tracks(self, query: str, market: str = "US", limit: int = 20, 
                     offset: int = 0, type: str = "track") -> Dict[str, Any]:
        """Search for tracks, albums, artists, or playlists."""
        try:
            params = {
                'q': query,
                'type': type,
                'market': market,
                'limit': limit,
                'offset': offset
            }
            response = requests.get(f"{self.base_url}/search", 
                                 headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error searching tracks: {e}")
            raise
    
    def get_track_audio_features(self, track_ids: List[str]) -> Dict[str, Any]:
        """Get audio features for multiple tracks (tempo, energy, danceability, etc.)."""
        try:
            track_ids_str = ','.join(track_ids)
            response = requests.get(f"{self.base_url}/audio-features", 
                                 headers=self.headers, params={'ids': track_ids_str})
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting audio features: {e}")
            raise
    
    def get_track_analysis(self, track_id: str) -> Dict[str, Any]:
        """Get detailed audio analysis for a track."""
        try:
            response = requests.get(f"{self.base_url}/audio-analysis/{track_id}", 
                                 headers=self.headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting track analysis: {e}")
            raise
    
    # ===== RECOMMENDATIONS & DISCOVERY =====
    
    def get_recommendations(self, seed_tracks: List[str] = None, seed_artists: List[str] = None,
                          seed_genres: List[str] = None, target_energy: float = None,
                          target_tempo: float = None, target_danceability: float = None,
                          limit: int = 20) -> Dict[str, Any]:
        """Get track recommendations based on seeds and audio features."""
        try:
            params = {'limit': limit}
            
            if seed_tracks:
                params['seed_tracks'] = ','.join(seed_tracks[:5])  # Max 5 seed tracks
            if seed_artists:
                params['seed_artists'] = ','.join(seed_artists[:5])  # Max 5 seed artists
            if seed_genres:
                params['seed_genres'] = ','.join(seed_genres[:5])  # Max 5 seed genres
            
            # Audio feature targets
            if target_energy is not None:
                params['target_energy'] = target_energy
            if target_tempo is not None:
                params['target_tempo'] = target_tempo
            if target_danceability is not None:
                params['target_danceability'] = target_danceability
            
            response = requests.get(f"{self.base_url}/recommendations", 
                                 headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting recommendations: {e}")
            raise
    
    # ===== AUDIO CONTENT CURATION =====
    
    def create_audio_mood_playlist(self, user_id: str, mood: str, 
                                  target_energy: float = 0.7, target_tempo: float = 120) -> Dict[str, Any]:
        """Create a mood-based playlist using audio features."""
        try:
            # Define mood-based parameters
            mood_params = {
                'energetic': {'target_energy': 0.8, 'target_tempo': 140, 'target_danceability': 0.8},
                'chill': {'target_energy': 0.3, 'target_tempo': 80, 'target_danceability': 0.4},
                'happy': {'target_energy': 0.7, 'target_tempo': 120, 'target_danceability': 0.7},
                'sad': {'target_energy': 0.2, 'target_tempo': 70, 'target_danceability': 0.3},
                'focused': {'target_energy': 0.4, 'target_tempo': 90, 'target_danceability': 0.2}
            }
            
            # Get mood parameters
            mood_config = mood_params.get(mood.lower(), {})
            target_energy = mood_config.get('target_energy', target_energy)
            target_tempo = mood_config.get('target_tempo', target_tempo)
            target_danceability = mood_config.get('target_danceability', 0.5)
            
            # Get recommendations based on mood
            recommendations = self.get_recommendations(
                target_energy=target_energy,
                target_tempo=target_tempo,
                target_danceability=target_danceability,
                limit=30
            )
            
            if not recommendations.get('tracks'):
                raise Exception("No recommendations found for this mood")
            
            # Create playlist
            playlist_name = f"{mood.title()} Vibes - {datetime.now().strftime('%B %Y')}"
            playlist = self.create_playlist(
                user_id=user_id,
                name=playlist_name,
                description=f"AI-curated {mood} mood playlist with optimal audio features",
                public=False
            )
            
            # Add tracks to playlist
            track_uris = [track['uri'] for track in recommendations['tracks']]
            self.add_tracks_to_playlist(playlist['id'], track_uris)
            
            return {
                'success': True,
                'playlist': playlist,
                'mood': mood,
                'tracks_added': len(track_uris),
                'audio_features': {
                    'target_energy': target_energy,
                    'target_tempo': target_tempo,
                    'target_danceability': target_danceability
                }
            }
            
        except Exception as e:
            logger.error(f"Error creating mood playlist: {e}")
            raise
    
    # ===== AUDIO ANALYTICS & INSIGHTS =====
    
    def get_user_audio_insights(self, time_range: str = "short_term") -> Dict[str, Any]:
        """Get comprehensive audio insights for the user."""
        try:
            insights = {}
            
            # Get top tracks
            top_tracks = self.get_user_top_tracks(time_range=time_range, limit=50)
            insights['top_tracks'] = top_tracks
            
            # Get audio features for top tracks
            if top_tracks.get('items'):
                track_ids = [track['id'] for track in top_tracks['items']]
                audio_features = self.get_track_audio_features(track_ids)
                insights['audio_features'] = audio_features
                
                # Calculate average audio features
                if audio_features.get('audio_features'):
                    features = audio_features['audio_features']
                    avg_features = {
                        'energy': sum(f['energy'] for f in features if f) / len(features),
                        'tempo': sum(f['tempo'] for f in features if f) / len(features),
                        'danceability': sum(f['danceability'] for f in features if f) / len(features),
                        'valence': sum(f['valence'] for f in features if f) / len(features),
                        'acousticness': sum(f['acousticness'] for f in features if f) / len(features)
                    }
                    insights['average_features'] = avg_features
            
            # Get top artists
            top_artists = self.get_user_top_artists(time_range=time_range, limit=20)
            insights['top_artists'] = top_artists
            
            # Get recently played
            recently_played = self.get_user_recently_played(limit=20)
            insights['recently_played'] = recently_played
            
            return insights
            
        except Exception as e:
            logger.error(f"Error getting audio insights: {e}")
            raise
    
    def generate_audio_report(self, time_range: str = "short_term") -> Dict[str, Any]:
        """Generate a comprehensive audio listening report."""
        try:
            insights = self.get_user_audio_insights(time_range)
            
            # Generate insights summary
            report = {
                'time_range': time_range,
                'generated_at': datetime.now().isoformat(),
                'summary': {
                    'total_tracks_analyzed': len(insights.get('top_tracks', {}).get('items', [])),
                    'total_artists': len(insights.get('top_artists', {}).get('items', [])),
                    'recent_tracks': len(insights.get('recently_played', {}).get('items', []))
                },
                'audio_profile': insights.get('average_features', {}),
                'top_content': {
                    'tracks': insights.get('top_tracks', {}).get('items', [])[:10],
                    'artists': insights.get('top_artists', {}).get('items', [])[:10]
                },
                'recommendations': {
                    'energy_level': 'High' if insights.get('average_features', {}).get('energy', 0) > 0.6 else 'Low',
                    'tempo_preference': 'Fast' if insights.get('average_features', {}).get('tempo', 0) > 120 else 'Slow',
                    'mood_tendency': 'Energetic' if insights.get('average_features', {}).get('valence', 0) > 0.6 else 'Mellow'
                }
            }
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating audio report: {e}")
            raise
