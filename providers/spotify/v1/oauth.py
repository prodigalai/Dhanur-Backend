#!/usr/bin/env python3
"""
Spotify OAuth Provider for Content Crew Prodigal
"""

import os
import secrets
import base64
import requests
from typing import Dict, Optional
from urllib.parse import urlencode
from dotenv import load_dotenv
import hashlib

# Load environment variables
load_dotenv()

# Spotify OAuth Configuration
SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_ME = "https://api.spotify.com/v1/me"

# Get environment variables
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
SPOTIFY_REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI", "http://localhost:8080/oauth/spotify/callback")
SPOTIFY_SCOPES = os.getenv("SPOTIFY_SCOPES", "user-read-email user-read-private user-read-playback-state user-modify-playback-state playlist-read-private playlist-modify-public playlist-modify-private user-top-read user-read-recently-played")

def _reload_env_vars():
    """Force reload environment variables from .env file."""
    from dotenv import load_dotenv
    import os
    
    # Clear any cached environment variables
    if hasattr(os, 'environ'):
        # Reload from .env file
        load_dotenv(override=True)
    
    return {
        'client_id': os.getenv("SPOTIFY_CLIENT_ID"),
        'client_secret': os.getenv("SPOTIFY_CLIENT_SECRET"),
        'redirect_uri': os.getenv("SPOTIFY_REDIRECT_URI", "http://localhost:8080/oauth/spotify/callback"),
        'scopes': os.getenv("SPOTIFY_SCOPES", "user-read-email user-read-private user-read-playback-state user-modify-playback-state")
    }

def get_authorization_url(state: Optional[str] = None, code_verifier: Optional[str] = None) -> Dict[str, str]:
    """
    Generate Spotify authorization URL with PKCE.
    
    Args:
        state: Optional state parameter for CSRF protection
        code_verifier: Optional PKCE code verifier (if not provided, generates new one)
        
    Returns:
        Dict containing authorization URL, state, and code_verifier
    """
    # Force reload environment variables
    env_vars = _reload_env_vars()
    
    if not all([env_vars['client_id'], env_vars['redirect_uri']]):
        raise ValueError("Missing required Spotify OAuth environment variables")
    
    # Generate state if not provided
    if not state:
        state = secrets.token_urlsafe(16)
    
    # Use provided code_verifier or generate new one
    if not code_verifier:
        code_verifier = secrets.token_urlsafe(64)
    
    # Generate PKCE code challenge from the code_verifier
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).decode().rstrip('=')
    
    params = {
        "client_id": env_vars['client_id'],
        "response_type": "code",
        "redirect_uri": env_vars['redirect_uri'],
        "scope": env_vars['scopes'],
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "show_dialog": "false",
    }
    
    auth_url = f"{SPOTIFY_AUTH_URL}?{urlencode(params)}"
    
    return {
        "authorization_url": auth_url,
        "state": state,
        "code_verifier": code_verifier
    }

def _basic_auth_header(client_id: str, client_secret: str) -> str:
    """Generate Basic Auth header for token requests."""
    token = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    return f"Basic {token}"

def exchange_code_for_token(
    code: str,
    code_verifier: str,
    client_id: Optional[str] = None,
    redirect_uri: Optional[str] = None
) -> Dict:
    """
    Exchange authorization code for access token using PKCE.
    
    Args:
        code: Authorization code from Spotify
        code_verifier: PKCE code verifier used in authorization
        client_id: Spotify client ID (uses env var if not provided)
        redirect_uri: Redirect URI (uses env var if not provided)
        
    Returns:
        Dict containing access token, refresh token, and other OAuth data
    """
    # Force reload environment variables
    env_vars = _reload_env_vars()
    
    # Use provided values or fall back to fresh environment variables
    client_id = client_id or env_vars['client_id']
    redirect_uri = redirect_uri or env_vars['redirect_uri']
    
    if not all([client_id, redirect_uri, code_verifier]):
        raise ValueError("Missing required OAuth credentials or code_verifier")
    
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": client_id,
        "code_verifier": code_verifier,
    }
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
    }
    
    try:
        response = requests.post(SPOTIFY_TOKEN_URL, data=data, headers=headers, timeout=15)
        
        # Log the response for debugging
        print(f"Token response status: {response.status_code}")
        print(f"Token response text: {response.text}")
        
        if response.status_code != 200:
            error_msg = f"Token exchange failed with status {response.status_code}: {response.text}"
            print(f"ERROR: {error_msg}")
            raise Exception(error_msg)
            
        return response.json()
        
    except requests.exceptions.RequestException as e:
        error_msg = f"Failed to exchange code for token: {str(e)}"
        print(f"ERROR: {error_msg}")
        raise Exception(error_msg)

def refresh_access_token(
    refresh_token: str,
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None
) -> Dict:
    """
    Refresh access token using refresh token.
    
    Args:
        refresh_token: Refresh token from previous OAuth flow
        client_id: Spotify client ID (uses env var if not provided)
        client_secret: Spotify client secret (uses env var if not provided)
        
    Returns:
        Dict containing new access token and other OAuth data
    """
    # Force reload environment variables
    env_vars = _reload_env_vars()
    
    # Use provided values or fall back to environment variables
    client_id = client_id or env_vars['client_id']
    client_secret = client_secret or env_vars['client_secret']
    
    if not all([client_id, client_secret]):
        raise ValueError("Missing required OAuth credentials")
    
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    
    headers = {
        "Authorization": _basic_auth_header(client_id, client_secret),
        "Content-Type": "application/x-www-form-urlencoded",
    }
    
    try:
        response = requests.post(SPOTIFY_TOKEN_URL, data=data, headers=headers, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to refresh access token: {str(e)}")

def get_user_profile(access_token: str) -> Dict:
    """
    Get Spotify user profile using access token.
    
    Args:
        access_token: Valid Spotify access token
        
    Returns:
        Dict containing user profile information
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(SPOTIFY_API_ME, headers=headers, timeout=15)
        response.raise_for_status()
        profile_data = response.json()
        
        # Map Spotify profile fields to our expected format
        mapped_data = {
            'id': profile_data.get('id'),
            'email': profile_data.get('email'),
            'display_name': profile_data.get('display_name'),
            'country': profile_data.get('country'),
            'followers': profile_data.get('followers', {}).get('total', 0),
            'images': profile_data.get('images', []),
            'product': profile_data.get('product'),  # premium, free, etc.
            'uri': profile_data.get('uri'),
            'external_urls': profile_data.get('external_urls', {}),
            'profile_picture': profile_data.get('images', [{}])[0].get('url') if profile_data.get('images') else None,
            'name': profile_data.get('display_name'),
            'spotify_id': profile_data.get('id'),
            'spotify_uri': profile_data.get('uri')
        }
        
        return mapped_data
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            raise Exception("Invalid or expired access token")
        elif e.response.status_code == 403:
            raise Exception("Insufficient permissions to access user profile")
        else:
            raise Exception(f"Failed to get user profile: {str(e)}")
    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to get user profile: {str(e)}")

def validate_spotify_config() -> Dict[str, bool]:
    """
    Validate Spotify OAuth configuration.
    
    Returns:
        Dict indicating which configuration elements are present
    """
    # Force reload environment variables
    env_vars = _reload_env_vars()
    
    return {
        "client_id": bool(env_vars['client_id']),
        "client_secret": bool(env_vars['client_secret']),
        "redirect_uri": bool(env_vars['redirect_uri']),
        "scopes": bool(env_vars['scopes']),
        "fully_configured": all([
            env_vars['client_id'],
            env_vars['client_secret'],
            env_vars['redirect_uri'],
            env_vars['scopes']
        ])
    }
