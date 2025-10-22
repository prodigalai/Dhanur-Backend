#!/usr/bin/env python3
"""
Spotify Analytics & Growth Operations
Comprehensive analytics for tracks, artists, playlists, and user engagement
"""

import requests
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import time

logger = logging.getLogger(__name__)

class SpotifyAnalyticsOps:
    """Spotify analytics and growth tracking operations."""
    
    def __init__(self, access_token: str = None, client_credentials: bool = False):
        self.access_token = access_token
        self.client_credentials = client_credentials
        self.base_url = "https://api.spotify.com/v1"
        
        if access_token:
            self.headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
        else:
            self.headers = {'Content-Type': 'application/json'}
    
    # ===== CLIENT CREDENTIALS AUTHENTICATION =====
    
    def get_client_credentials_token(self, client_id: str, client_secret: str) -> str:
        """Get access token using client credentials (for public data)."""
        try:
            auth_url = "https://accounts.spotify.com/api/token"
            auth_data = {
                'grant_type': 'client_credentials'
            }
            auth_headers = {
                'Authorization': f'Basic {self._basic_auth_header(client_id, client_secret)}',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            response = requests.post(auth_url, data=auth_data, headers=auth_headers)
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data['access_token']
            self.headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            logger.info("Client credentials token obtained successfully")
            return self.access_token
            
        except Exception as e:
            logger.error(f"Error getting client credentials token: {e}")
            raise
    
    def _basic_auth_header(self, client_id: str, client_secret: str) -> str:
        """Generate Basic Auth header for client credentials."""
        import base64
        token = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
        return token
    
    # ===== TRACK ANALYTICS (Public Data) =====
    
    def get_track_popularity(self, track_id: str) -> Dict[str, Any]:
        """Get track popularity and basic info (public data)."""
        try:
            response = requests.get(f"{self.base_url}/tracks/{track_id}", headers=self.headers)
            response.raise_for_status()
            
            track_data = response.json()
            return {
                'track_id': track_id,
                'name': track_data['name'],
                'popularity': track_data['popularity'],
                'duration_ms': track_data['duration_ms'],
                'explicit': track_data['explicit'],
                'isrc': track_data.get('external_ids', {}).get('isrc'),
                'album': {
                    'id': track_data['album']['id'],
                    'name': track_data['album']['name'],
                    'release_date': track_data['album']['release_date']
                },
                'artists': [
                    {
                        'id': artist['id'],
                        'name': artist['name']
                    } for artist in track_data['artists']
                ],
                'retrieved_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting track popularity for {track_id}: {e}")
            raise
    
    def get_multiple_tracks_popularity(self, track_ids: List[str]) -> Dict[str, Any]:
        """Get popularity for multiple tracks in batch."""
        try:
            # Spotify allows max 50 tracks per request
            batch_size = 50
            all_tracks = []
            
            for i in range(0, len(track_ids), batch_size):
                batch = track_ids[i:i + batch_size]
                track_ids_str = ','.join(batch)
                
                response = requests.get(f"{self.base_url}/tracks", 
                                     headers=self.headers, 
                                     params={'ids': track_ids_str})
                response.raise_for_status()
                
                batch_data = response.json()
                if batch_data.get('tracks'):
                    all_tracks.extend(batch_data['tracks'])
                
                # Rate limiting: 100 requests per second
                time.sleep(0.01)
            
            # Process and format results
            tracks_data = []
            for track in all_tracks:
                if track:  # Skip None tracks
                    tracks_data.append({
                        'track_id': track['id'],
                        'name': track['name'],
                        'popularity': track['popularity'],
                        'duration_ms': track['duration_ms'],
                        'explicit': track['explicit'],
                        'isrc': track.get('external_ids', {}).get('isrc'),
                        'album': {
                            'id': track['album']['id'],
                            'name': track['album']['name'],
                            'release_date': track['album']['release_date']
                        },
                        'artists': [
                            {
                                'id': artist['id'],
                                'name': artist['name']
                            } for artist in track['artists']
                        ],
                        'retrieved_at': datetime.now().isoformat()
                    })
            
            return {
                'total_tracks': len(tracks_data),
                'tracks': tracks_data,
                'retrieved_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting multiple tracks popularity: {e}")
            raise
    
    # ===== ARTIST ANALYTICS (Public Data) =====
    
    def get_artist_analytics(self, artist_id: str) -> Dict[str, Any]:
        """Get artist followers, popularity, and growth metrics."""
        try:
            response = requests.get(f"{self.base_url}/artists/{artist_id}", headers=self.headers)
            response.raise_for_status()
            
            artist_data = response.json()
            return {
                'artist_id': artist_id,
                'name': artist_data['name'],
                'popularity': artist_data['popularity'],
                'followers': artist_data['followers']['total'],
                'genres': artist_data['genres'],
                'images': artist_data['images'],
                'retrieved_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting artist analytics for {artist_id}: {e}")
            raise
    
    def get_multiple_artists_analytics(self, artist_ids: List[str]) -> Dict[str, Any]:
        """Get analytics for multiple artists in batch."""
        try:
            batch_size = 50
            all_artists = []
            
            for i in range(0, len(artist_ids), batch_size):
                batch = artist_ids[i:i + batch_size]
                artist_ids_str = ','.join(batch)
                
                response = requests.get(f"{self.base_url}/artists", 
                                     headers=self.headers, 
                                     params={'ids': artist_ids_str})
                response.raise_for_status()
                
                batch_data = response.json()
                if batch_data.get('artists'):
                    all_artists.extend(batch_data['artists'])
                
                time.sleep(0.01)
            
            artists_data = []
            for artist in all_artists:
                if artist:
                    artists_data.append({
                        'artist_id': artist['id'],
                        'name': artist['name'],
                        'popularity': artist['popularity'],
                        'followers': artist['followers']['total'],
                        'genres': artist['genres'],
                        'images': artist['images'],
                        'retrieved_at': datetime.now().isoformat()
                    })
            
            return {
                'total_artists': len(artists_data),
                'artists': artists_data,
                'retrieved_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting multiple artists analytics: {e}")
            raise
    
    def get_artist_top_tracks(self, artist_id: str, market: str = "US") -> Dict[str, Any]:
        """Get artist's top tracks by market."""
        try:
            response = requests.get(f"{self.base_url}/artists/{artist_id}/top-tracks", 
                                 headers=self.headers, 
                                 params={'market': market})
            response.raise_for_status()
            
            top_tracks = response.json()
            return {
                'artist_id': artist_id,
                'market': market,
                'tracks': [
                    {
                        'track_id': track['id'],
                        'name': track['name'],
                        'popularity': track['popularity'],
                        'duration_ms': track['duration_ms'],
                        'album': {
                            'id': track['album']['id'],
                            'name': track['album']['name']
                        }
                    } for track in top_tracks['tracks']
                ],
                'retrieved_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting artist top tracks for {artist_id}: {e}")
            raise
    
    def get_related_artists(self, artist_id: str) -> Dict[str, Any]:
        """Get related artists for discovery and growth opportunities."""
        try:
            response = requests.get(f"{self.base_url}/artists/{artist_id}/related-artists", 
                                 headers=self.headers)
            response.raise_for_status()
            
            related = response.json()
            return {
                'artist_id': artist_id,
                'related_artists': [
                    {
                        'artist_id': artist['id'],
                        'name': artist['name'],
                        'popularity': artist['popularity'],
                        'followers': artist['followers']['total'],
                        'genres': artist['genres']
                    } for artist in related['artists']
                ],
                'retrieved_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting related artists for {artist_id}: {e}")
            raise
    
    # ===== PLAYLIST ANALYTICS (Public Data) =====
    
    def get_playlist_analytics(self, playlist_id: str) -> Dict[str, Any]:
        """Get playlist followers, tracks, and growth metrics."""
        try:
            # Get playlist basic info
            playlist_response = requests.get(f"{self.base_url}/playlists/{playlist_id}", 
                                          headers=self.headers)
            playlist_response.raise_for_status()
            playlist_data = playlist_response.json()
            
            # Get playlist tracks
            tracks_response = requests.get(f"{self.base_url}/playlists/{playlist_id}/tracks", 
                                        headers=self.headers,
                                        params={'limit': 100, 'offset': 0})
            tracks_response.raise_for_status()
            tracks_data = tracks_response.json()
            
            return {
                'playlist_id': playlist_id,
                'name': playlist_data['name'],
                'description': playlist_data.get('description', ''),
                'followers': playlist_data['followers']['total'],
                'public': playlist_data['public'],
                'collaborative': playlist_data['collaborative'],
                'owner': {
                    'id': playlist_data['owner']['id'],
                    'display_name': playlist_data['owner']['display_name']
                },
                'tracks_count': tracks_data['total'],
                'tracks': [
                    {
                        'track_id': item['track']['id'] if item['track'] else None,
                        'name': item['track']['name'] if item['track'] else None,
                        'added_at': item['added_at'],
                        'added_by': item['added_by']['id'] if item['added_by'] else None
                    } for item in tracks_data['items'] if item['track']
                ],
                'retrieved_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting playlist analytics for {playlist_id}: {e}")
            raise
    
    # ===== AUDIO FEATURES & ANALYSIS =====
    
    def get_track_audio_features(self, track_id: str) -> Dict[str, Any]:
        """Get comprehensive audio features for a track."""
        try:
            response = requests.get(f"{self.base_url}/audio-features/{track_id}", 
                                 headers=self.headers)
            response.raise_for_status()
            
            features = response.json()
            return {
                'track_id': track_id,
                'audio_features': {
                    'danceability': features['danceability'],
                    'energy': features['energy'],
                    'key': features['key'],
                    'loudness': features['loudness'],
                    'mode': features['mode'],
                    'speechiness': features['speechiness'],
                    'acousticness': features['acousticness'],
                    'instrumentalness': features['instrumentalness'],
                    'liveness': features['liveness'],
                    'valence': features['valence'],
                    'tempo': features['tempo'],
                    'time_signature': features['time_signature']
                },
                'retrieved_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting audio features for {track_id}: {e}")
            raise
    
    def get_multiple_tracks_audio_features(self, track_ids: List[str]) -> Dict[str, Any]:
        """Get audio features for multiple tracks in batch."""
        try:
            batch_size = 100  # Spotify allows 100 tracks per request for audio features
            all_features = []
            
            for i in range(0, len(track_ids), batch_size):
                batch = track_ids[i:i + batch_size]
                track_ids_str = ','.join(batch)
                
                response = requests.get(f"{self.base_url}/audio-features", 
                                     headers=self.headers, 
                                     params={'ids': track_ids_str})
                response.raise_for_status()
                
                batch_data = response.json()
                if batch_data.get('audio_features'):
                    all_features.extend(batch_data['audio_features'])
                
                time.sleep(0.01)
            
            features_data = []
            for features in all_features:
                if features:
                    features_data.append({
                        'track_id': features['id'],
                        'audio_features': {
                            'danceability': features['danceability'],
                            'energy': features['energy'],
                            'key': features['key'],
                            'loudness': features['loudness'],
                            'mode': features['mode'],
                            'speechiness': features['speechiness'],
                            'acousticness': features['acousticness'],
                            'instrumentalness': features['instrumentalness'],
                            'liveness': features['liveness'],
                            'valence': features['valence'],
                            'tempo': features['tempo'],
                            'time_signature': features['time_signature']
                        },
                        'retrieved_at': datetime.now().isoformat()
                    })
            
            return {
                'total_tracks': len(features_data),
                'tracks_features': features_data,
                'retrieved_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting multiple tracks audio features: {e}")
            raise
    
    def get_track_audio_analysis(self, track_id: str) -> Dict[str, Any]:
        """Get detailed audio analysis including beats, sections, and segments."""
        try:
            response = requests.get(f"{self.base_url}/audio-analysis/{track_id}", 
                                 headers=self.headers)
            response.raise_for_status()
            
            analysis = response.json()
            return {
                'track_id': track_id,
                'audio_analysis': {
                    'bars': len(analysis.get('bars', [])),
                    'beats': len(analysis.get('beats', [])),
                    'sections': len(analysis.get('sections', [])),
                    'segments': len(analysis.get('segments', [])),
                    'tatums': len(analysis.get('tatums', [])),
                    'duration': analysis.get('track', {}).get('duration', 0),
                    'sample_rate': analysis.get('track', {}).get('sample_rate', 0)
                },
                'retrieved_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting audio analysis for {track_id}: {e}")
            raise
    
    # ===== SEARCH & DISCOVERY =====
    
    def search_tracks_by_isrc(self, isrc: str, market: str = "US") -> Dict[str, Any]:
        """Search for tracks by ISRC code."""
        try:
            response = requests.get(f"{self.base_url}/search", 
                                 headers=self.headers,
                                 params={
                                     'q': f'isrc:{isrc}',
                                     'type': 'track',
                                     'market': market,
                                     'limit': 50
                                 })
            response.raise_for_status()
            
            search_results = response.json()
            return {
                'isrc': isrc,
                'market': market,
                'total_results': search_results['tracks']['total'],
                'tracks': [
                    {
                        'track_id': track['id'],
                        'name': track['name'],
                        'popularity': track['popularity'],
                        'artists': [artist['name'] for artist in track['artists']],
                        'album': track['album']['name']
                    } for track in search_results['tracks']['items']
                ],
                'retrieved_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error searching tracks by ISRC {isrc}: {e}")
            raise
    
    def search_tracks_by_name(self, track_name: str, artist_name: str = None, 
                             market: str = "US", limit: int = 20) -> Dict[str, Any]:
        """Search for tracks by name and optionally artist."""
        try:
            query = f'track:{track_name}'
            if artist_name:
                query += f' artist:{artist_name}'
            
            response = requests.get(f"{self.base_url}/search", 
                                 headers=self.headers,
                                 params={
                                     'q': query,
                                     'type': 'track',
                                     'market': market,
                                     'limit': limit
                                 })
            response.raise_for_status()
            
            search_results = response.json()
            return {
                'query': query,
                'market': market,
                'total_results': search_results['tracks']['total'],
                'tracks': [
                    {
                        'track_id': track['id'],
                        'name': track['name'],
                        'popularity': track['popularity'],
                        'artists': [artist['name'] for artist in track['artists']],
                        'album': track['album']['name'],
                        'isrc': track.get('external_ids', {}).get('isrc')
                    } for track in search_results['tracks']['items']
                ],
                'retrieved_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error searching tracks by name: {e}")
            raise
    
    # ===== GROWTH METRICS CALCULATION =====
    
    def calculate_growth_metrics(self, current_data: Dict, previous_data: Dict) -> Dict[str, Any]:
        """Calculate growth metrics between two data points."""
        try:
            metrics = {}
            
            # Popularity change
            if 'popularity' in current_data and 'popularity' in previous_data:
                current_pop = current_data['popularity']
                previous_pop = previous_data['popularity']
                metrics['popularity_change'] = current_pop - previous_pop
                metrics['popularity_change_percent'] = ((current_pop - previous_pop) / previous_pop * 100) if previous_pop > 0 else 0
            
            # Followers change
            if 'followers' in current_data and 'followers' in previous_data:
                current_followers = current_data['followers']
                previous_followers = previous_data['followers']
                metrics['followers_change'] = current_followers - previous_followers
                metrics['followers_change_percent'] = ((current_followers - previous_followers) / previous_followers * 100) if previous_followers > 0 else 0
            
            # Tracks count change (for playlists)
            if 'tracks_count' in current_data and 'tracks_count' in previous_data:
                current_tracks = current_data['tracks_count']
                previous_tracks = previous_data['tracks_count']
                metrics['tracks_change'] = current_tracks - previous_tracks
                metrics['tracks_change_percent'] = ((current_tracks - previous_tracks) / previous_tracks * 100) if previous_tracks > 0 else 0
            
            metrics['analysis_date'] = datetime.now().isoformat()
            metrics['current_data_date'] = current_data.get('retrieved_at')
            metrics['previous_data_date'] = previous_data.get('retrieved_at')
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating growth metrics: {e}")
            raise
    
    def generate_growth_report(self, entity_id: str, entity_type: str, 
                              current_data: Dict, previous_data: Dict) -> Dict[str, Any]:
        """Generate comprehensive growth report for an entity."""
        try:
            growth_metrics = self.calculate_growth_metrics(current_data, previous_data)
            
            report = {
                'entity_id': entity_id,
                'entity_type': entity_type,
                'current_data': current_data,
                'previous_data': previous_data,
                'growth_metrics': growth_metrics,
                'summary': {
                    'status': 'growing' if growth_metrics.get('popularity_change', 0) > 0 else 'declining',
                    'key_insights': []
                },
                'recommendations': [],
                'generated_at': datetime.now().isoformat()
            }
            
            # Add insights based on metrics
            if growth_metrics.get('popularity_change_percent', 0) > 10:
                report['summary']['key_insights'].append("Strong popularity growth detected")
                report['recommendations'].append("Consider increasing marketing efforts to capitalize on momentum")
            
            if growth_metrics.get('followers_change_percent', 0) > 5:
                report['summary']['key_insights'].append("Growing follower base")
                report['recommendations'].append("Engage with new followers through content and interactions")
            
            if growth_metrics.get('popularity_change_percent', 0) < -5:
                report['summary']['key_insights'].append("Popularity declining")
                report['recommendations'].append("Review content strategy and consider promotional activities")
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating growth report: {e}")
            raise
