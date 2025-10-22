import requests
import base64
import time
from spotify_config import SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_TOKEN_URL, SPOTIFY_API_BASE

class SpotifyService:
    def __init__(self):
        self.client_id = SPOTIFY_CLIENT_ID
        self.client_secret = SPOTIFY_CLIENT_SECRET
        self.access_token = None
        self.token_expires_at = 0
        
    def _get_client_credentials_token(self):
        """Get access token using client credentials flow"""
        if self.access_token and time.time() < self.token_expires_at:
            return self.access_token
            
        # Encode client credentials
        credentials = f"{self.client_id}:{self.client_secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        
        # Request token
        headers = {
            'Authorization': f'Basic {encoded_credentials}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        data = {
            'grant_type': 'client_credentials'
        }
        
        try:
            response = requests.post(SPOTIFY_TOKEN_URL, headers=headers, data=data)
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data['access_token']
            self.token_expires_at = time.time() + token_data['expires_in'] - 60  # Buffer of 60 seconds
            
            return self.access_token
            
        except requests.exceptions.RequestException as e:
            print(f"Error getting Spotify token: {e}")
            return None
    
    def _make_api_call(self, endpoint, params=None):
        """Make authenticated API call to Spotify"""
        token = self._get_client_credentials_token()
        if not token:
            return None
            
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.get(f"{SPOTIFY_API_BASE}{endpoint}", headers=headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Spotify API error: {e}")
            return None
    
    # Track Methods
    def get_track(self, track_id):
        """Get track details"""
        return self._make_api_call(f'/tracks/{track_id}')
    
    def get_track_features(self, track_id):
        """Get track audio features"""
        return self._make_api_call(f'/audio-features/{track_id}')
    
    def get_track_analysis(self, track_id):
        """Get track audio analysis"""
        return self._make_api_call(f'/audio-analysis/{track_id}')
    
    def search_tracks(self, query, limit=20, market='US'):
        """Search for tracks"""
        params = {
            'q': query,
            'type': 'track',
            'limit': limit,
            'market': market
        }
        return self._make_api_call('/search', params)
    
    def get_multiple_tracks(self, track_ids):
        """Get multiple tracks by IDs"""
        params = {'ids': ','.join(track_ids)}
        return self._make_api_call('/tracks', params)
    
    def get_multiple_track_features(self, track_ids):
        """Get audio features for multiple tracks"""
        params = {'ids': ','.join(track_ids)}
        return self._make_api_call('/audio-features', params)
    
    # Artist Methods
    def get_artist(self, artist_id):
        """Get artist details"""
        return self._make_api_call(f'/artists/{artist_id}')
    
    def get_artist_top_tracks(self, artist_id, market='US'):
        """Get artist's top tracks"""
        params = {'market': market}
        return self._make_api_call(f'/artists/{artist_id}/top-tracks', params)
    
    def get_related_artists(self, artist_id):
        """Get related artists"""
        return self._make_api_call(f'/artists/{artist_id}/related-artists')
    
    def get_artist_albums(self, artist_id, limit=20):
        """Get artist's albums"""
        params = {'limit': limit}
        return self._make_api_call(f'/artists/{artist_id}/albums', params)
    
    # Playlist Methods
    def get_playlist(self, playlist_id, market='US'):
        """Get playlist details"""
        params = {'market': market}
        return self._make_api_call(f'/playlists/{playlist_id}', params)
    
    def get_playlist_tracks(self, playlist_id, limit=100, offset=0):
        """Get playlist tracks"""
        params = {'limit': limit, 'offset': offset}
        return self._make_api_call(f'/playlists/{playlist_id}/tracks', params)
    
    # Search & Discovery
    def search_artists(self, query, limit=20):
        """Search for artists"""
        params = {
            'q': query,
            'type': 'artist',
            'limit': limit
        }
        return self._make_api_call('/search', params)
    
    def search_playlists(self, query, limit=20):
        """Search for playlists"""
        params = {
            'q': query,
            'type': 'playlist',
            'limit': limit
        }
        return self._make_api_call('/search', params)
    
    def get_recommendations(self, seed_tracks=None, seed_artists=None, seed_genres=None, limit=20):
        """Get track recommendations"""
        params = {'limit': limit}
        
        if seed_tracks:
            params['seed_tracks'] = ','.join(seed_tracks[:5])  # Max 5 seed tracks
        if seed_artists:
            params['seed_artists'] = ','.join(seed_artists[:5])  # Max 5 seed artists
        if seed_genres:
            params['seed_genres'] = ','.join(seed_genres[:5])  # Max 5 seed genres
            
        return self._make_api_call('/recommendations', params)
    
    def get_available_genres(self):
        """Get available genre seeds"""
        return self._make_api_call('/recommendations/available-genre-seeds')
    
    # Market & Availability
    def get_track_markets(self, track_id):
        """Get markets where track is available"""
        track_data = self.get_track(track_id)
        if track_data and 'available_markets' in track_data:
            return track_data['available_markets']
        return []
    
    def get_playlist_markets(self, playlist_id):
        """Get markets where playlist is available"""
        playlist_data = self.get_playlist(playlist_id)
        if playlist_data and 'available_markets' in playlist_data:
            return playlist_data['available_markets']
        return []

# Create global instance
spotify_service = SpotifyService()
