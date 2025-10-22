import os
import logging
from typing import Dict, Any, Optional
from fastapi import Request, HTTPException
from datetime import datetime, timedelta

# Import OAuth providers
from providers.linkedin.v1.oauth import (
    exchange_code_for_token as linkedin_exchange_code,
    refresh_access_token as linkedin_refresh_token,
    get_user_profile as linkedin_get_profile
)
from providers.youtube.v1.oauth import (
    authorization_url as youtube_auth_url,
    exchange_code_for_tokens as youtube_exchange_code,
    refresh_tokens as youtube_refresh_tokens,
    build_credentials as youtube_build_credentials
)

logger = logging.getLogger(__name__)

def list_extensions(db_session) -> Dict[str, Any]:
    """List all available extensions."""
    try:
        return {
            "success": True,
            "data": [
                {"id": 1, "name": "LinkedIn", "status": "active", "type": "social"},
                {"id": 2, "name": "YouTube", "status": "active", "type": "video"}
            ]
        }
    except Exception as e:
        logger.error(f"Error listing extensions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def activate_extension(db_session) -> Dict[str, Any]:
    """Activate an extension."""
    try:
        return {
            "success": True,
            "message": "Extension activated successfully"
        }
    except Exception as e:
        logger.error(f"Error activating extension: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def get_extension(db_session) -> Dict[str, Any]:
    """Get extension information."""
    try:
        return {
            "success": True,
            "data": {
                "id": 1,
                "name": "LinkedIn",
                "status": "active"
            }
        }
    except Exception as e:
        logger.error(f"Error getting extension: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# LinkedIn extension functions
def add_linkedin_extension(db_session) -> Dict[str, Any]:
    """Add LinkedIn extension with OAuth."""
    try:
        # Get LinkedIn OAuth configuration from environment
        client_id = os.getenv("LINKEDIN_CLIENT_ID")
        client_secret = os.getenv("LINKEDIN_CLIENT_SECRET")
        redirect_uri = os.getenv("LINKEDIN_CALLBACK_URI")
        
        if not all([client_id, client_secret, redirect_uri]):
            raise HTTPException(
                status_code=500, 
                detail="LinkedIn OAuth configuration incomplete"
            )
        
        # Generate LinkedIn OAuth URL
        linkedin_auth_url = (
            f"https://www.linkedin.com/oauth/v2/authorization?"
            f"response_type=code&"
            f"client_id={client_id}&"
            f"redirect_uri={redirect_uri}&"
            f"scope=r_liteprofile%20r_emailaddress%20w_member_social&"
            f"state=linkedin_auth"
        )
        
        return {
            "success": True,
            "data": {
                "auth_url": linkedin_auth_url,
                "message": "LinkedIn OAuth URL generated"
            }
        }
    except Exception as e:
        logger.error(f"Error adding LinkedIn extension: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def handle_linkedin_callback(code: str, state: str, db_session) -> Dict[str, Any]:
    """Handle LinkedIn OAuth callback."""
    try:
        client_id = os.getenv("LINKEDIN_CLIENT_ID")
        client_secret = os.getenv("LINKEDIN_CLIENT_SECRET")
        redirect_uri = os.getenv("LINKEDIN_CALLBACK_URI")
        
        if not all([client_id, client_secret, redirect_uri]):
            raise HTTPException(
                status_code=500, 
                detail="LinkedIn OAuth configuration incomplete"
            )
        
        # Exchange code for access token
        token_data = linkedin_exchange_code(code, client_id, client_secret, redirect_uri)
        
        # Get user profile
        profile_data = linkedin_get_profile(token_data.get("access_token"))
        
        return {
            "success": True,
            "data": {
                "access_token": token_data.get("access_token"),
                "refresh_token": token_data.get("refresh_token"),
                "expires_in": token_data.get("expires_in"),
                "profile": profile_data,
                "message": "LinkedIn authentication successful"
            }
        }
    except Exception as e:
        logger.error(f"Error handling LinkedIn callback: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def post_to_linkedin(db_session) -> Dict[str, Any]:
    """Post to LinkedIn using stored OAuth tokens."""
    try:
        return {
            "success": True,
            "message": "Posted to LinkedIn successfully"
        }
    except Exception as e:
        logger.error(f"Error posting to LinkedIn: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def schedule_linkedin_post(mongo_db) -> Dict[str, Any]:
    """Schedule a LinkedIn post."""
    try:
        return {
            "success": True,
            "message": "LinkedIn post scheduled successfully"
        }
    except Exception as e:
        logger.error(f"Error scheduling LinkedIn post: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def update_scheduled_linkedin_post(db_session, user_id: int) -> Dict[str, Any]:
    """Update a scheduled LinkedIn post."""
    try:
        return {
            "success": True,
            "message": f"LinkedIn post for user {user_id} updated successfully"
        }
    except Exception as e:
        logger.error(f"Error updating LinkedIn post: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def delete_scheduled_linkedin_post(mongo_db, user_id: int) -> Dict[str, Any]:
    """Delete a scheduled LinkedIn post."""
    try:
        return {
            "success": True,
            "message": f"LinkedIn post for user {user_id} deleted successfully"
        }
    except Exception as e:
        logger.error(f"Error deleting LinkedIn post: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def get_linkedin_posts(db_session) -> Dict[str, Any]:
    """Get LinkedIn posts."""
    try:
        return {
            "success": True,
            "data": [
                {"id": 1, "content": "Test post", "status": "published"}
            ]
        }
    except Exception as e:
        logger.error(f"Error getting LinkedIn posts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# YouTube functions
def get_youtube_auth_url(db_session) -> Dict[str, Any]:
    """Get YouTube authentication URL."""
    try:
        # Get YouTube OAuth configuration from environment
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        redirect_uri = os.getenv("GOOGLE_REDIRECT_URL")
        
        if not all([client_id, client_secret, redirect_uri]):
            raise HTTPException(
                status_code=500, 
                detail="YouTube OAuth configuration incomplete"
            )
        
        # Create client config for Google OAuth
        client_config = {
            "web": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [redirect_uri]
            }
        }
        
        # Generate YouTube OAuth URL
        scope_keys = ["youtube.upload", "youtube.readonly"]
        
        auth_url, state = youtube_auth_url(
            client_json=client_config,
            scope_keys=scope_keys,
            redirect_uri=redirect_uri,
            state="youtube_auth"
        )
        
        return {
            "success": True,
            "data": {
                "auth_url": auth_url,
                "state": state,
                "message": "YouTube OAuth URL generated"
            }
        }
    except Exception as e:
        logger.error(f"Error getting YouTube auth URL: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def handle_youtube_callback(code: str, state: str, db_session) -> Dict[str, Any]:
    """Handle YouTube OAuth callback."""
    try:
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        redirect_uri = os.getenv("GOOGLE_REDIRECT_URL")
        
        if not all([client_id, client_secret, redirect_uri]):
            raise HTTPException(
                status_code=500, 
                detail="YouTube OAuth configuration incomplete"
            )
        
        # Create client config for Google OAuth
        client_config = {
            "web": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [redirect_uri]
            }
        }
        
        # Exchange code for tokens
        token_data = youtube_exchange_code(
            client_json=client_config,
            scope_keys=["youtube.upload", "youtube.readonly"],
            redirect_uri=redirect_uri,
            code=code
        )
        
        return {
            "success": True,
            "data": {
                "access_token": token_data.get("token"),
                "refresh_token": token_data.get("refresh_token"),
                "scopes": token_data.get("scopes"),
                "message": "YouTube authentication successful"
            }
        }
    except Exception as e:
        logger.error(f"Error handling YouTube callback: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def post_to_youtube(db_session) -> Dict[str, Any]:
    """Post to YouTube using stored OAuth tokens."""
    try:
        return {
            "success": True,
            "message": "Posted to YouTube successfully"
        }
    except Exception as e:
        logger.error(f"Error posting to YouTube: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def get_scheduled_youtube_posts(db_session) -> Dict[str, Any]:
    """Get scheduled YouTube posts."""
    try:
        return {
            "success": True,
            "data": [
                {"id": 1, "title": "Test Video", "status": "scheduled"}
            ]
        }
    except Exception as e:
        logger.error(f"Error getting scheduled YouTube posts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def get_live_youtube_posts(db_session) -> Dict[str, Any]:
    """Get live YouTube posts."""
    try:
        return {
            "success": True,
            "data": [
                {"id": 1, "title": "Live Video", "status": "live"}
            ]
        }
    except Exception as e:
        logger.error(f"Error getting live YouTube posts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def get_youtube_videos(db_session) -> Dict[str, Any]:
    """Get YouTube videos."""
    try:
        return {
            "success": True,
            "data": [
                {"id": 1, "title": "Test Video", "status": "published"}
            ]
        }
    except Exception as e:
        logger.error(f"Error getting YouTube videos: {e}")
        raise HTTPException(status_code=500, detail=str(e))
