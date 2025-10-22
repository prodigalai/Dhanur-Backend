#!/usr/bin/env python3
"""
Enhanced OAuth Routes for Content Crew Prodigal
Production-ready OAuth endpoints with user management integration
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from typing import Dict, Any, Optional
from datetime import datetime
import logging

from services.mongodb_service import mongodb_service
from controllers.enhanced_spotify_controller import EnhancedSpotifyController
from controllers.auth_controller import authenticate_user, create_user
from middleware.auth import get_current_user
from models.enhanced_request_models import (
    OAuthLinkRequest, OAuthCreateAccountRequest
)
from models.request_models import UserRegistrationRequest, UserLoginRequest

logger = logging.getLogger(__name__)

router = APIRouter()

# =====================================================
# ENHANCED OAUTH ROUTES
# =====================================================

@router.post("/oauth/spotify/initiate")
async def initiate_spotify_oauth(
    request: OAuthCreateAccountRequest,
) -> Dict[str, Any]:
    """
    Initiate Spotify OAuth flow with optional user account creation.
    
    Args:
        request: OAuth initiation request with user details
        db_session: Database session
        
    Returns:
        Dict containing authorization URL and flow metadata
    """
    try:
        logger.info(f"Initiating Spotify OAuth flow for email: {request.email}")
        
        result = EnhancedSpotifyController.initiate_oauth_flow(
            user_id=request.user_id,
            email=request.email,
            create_account=request.create_account
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error initiating Spotify OAuth: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate OAuth flow: {str(e)}"
        )

@router.get("/oauth/spotify/callback")
async def spotify_oauth_callback(
    code: str,
    state: str,
) -> Dict[str, Any]:
    """
    Handle Spotify OAuth callback with enhanced user management.
    
    Args:
        code: Authorization code from Spotify
        state: State parameter for CSRF protection
        db_session: Database session
        
    Returns:
        Dict containing OAuth result and user management info
    """
    try:
        logger.info(f"Processing Spotify OAuth callback: state={state[:10]}...")
        
        result = await EnhancedSpotifyController.handle_oauth_callback(
            db_session, code, state
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error handling Spotify OAuth callback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to handle OAuth callback: {str(e)}"
        )

@router.post("/oauth/spotify/refresh")
async def refresh_spotify_tokens(
    oauth_account_id: str,
    current_user: Dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Refresh Spotify access tokens for authenticated user.
    
    Args:
        oauth_account_id: OAuth account ID to refresh
        current_user: Current authenticated user
        db_session: Database session
        
    Returns:
        Dict containing refreshed token info
    """
    try:
        user_id = current_user.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user token"
            )
        
        logger.info(f"Refreshing Spotify tokens for user: {user_id}")
        
        result = EnhancedSpotifyController.refresh_spotify_tokens(
            db_session, user_id, oauth_account_id
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error refreshing Spotify tokens: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refresh tokens: {str(e)}"
        )

@router.get("/oauth/spotify/status")
async def get_spotify_account_status(
    current_user: Dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get comprehensive Spotify account status for authenticated user.
    
    Args:
        current_user: Current authenticated user
        db_session: Database session
        
    Returns:
        Dict containing Spotify account status and metadata
    """
    try:
        user_id = current_user.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user token"
            )
        
        logger.info(f"Getting Spotify account status for user: {user_id}")
        
        result = EnhancedSpotifyController.get_spotify_account_status(
            db_session, user_id
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting Spotify account status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get account status: {str(e)}"
        )

@router.delete("/oauth/spotify/disconnect")
async def disconnect_spotify_account(
    oauth_account_id: str,
    current_user: Dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Disconnect Spotify OAuth account for authenticated user.
    
    Args:
        oauth_account_id: OAuth account ID to disconnect
        current_user: Current authenticated user
        db_session: Database session
        
    Returns:
        Dict containing operation result
    """
    try:
        user_id = current_user.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user token"
            )
        
        logger.info(f"Disconnecting Spotify account for user: {user_id}")
        
        result = UserManagementController.disconnect_oauth_account(
            db_session, user_id, oauth_account_id
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error disconnecting Spotify account: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to disconnect account: {str(e)}"
        )

# =====================================================
# USER MANAGEMENT ROUTES
# =====================================================

@router.post("/auth/register")
async def register_user(
    request: UserRegistrationRequest,
) -> Dict[str, Any]:
    """
    Register a new user with comprehensive validation.
    
    Args:
        request: User registration request
        db_session: Database session
        
    Returns:
        Dict containing user info and access token
    """
    try:
        logger.info(f"User registration attempt: {request.email}")
        
        result = UserManagementController.register_user(
            db_session=db_session,
            email=request.email,
            password=request.password,
            full_name=request.full_name,
            organization_name=request.organization_name,
            phone=request.phone,
            timezone=request.timezone or "UTC"
        )
        
        logger.info(f"User registered successfully: {request.email}")
        return result
        
    except Exception as e:
        logger.error(f"Error during user registration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register user: {str(e)}"
        )

@router.post("/auth/login")
async def login_user(
    request: UserLoginRequest
) -> Dict[str, Any]:
    """
    Authenticate user login with comprehensive validation.
    
    Args:
        request: User login request
        
    Returns:
        Dict containing user info and access token
    """
    try:
        logger.info(f"User login attempt: {request.email}")
        
        # Use MongoDB-based authentication
        user = authenticate_user(request.email, request.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Generate JWT token
        from services.jwt_service import generate_jwt
        access_token = generate_jwt(
            entity_id=user["user_id"],
            email=user["email"],
            user_id=user["user_id"],
            entity_type="user"
        )
        
        logger.info(f"User logged in successfully: {request.email}")
        
        return {
            "success": True,
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": 86400,
            "user": {
                "id": user["user_id"],
                "email": user["email"],
                "name": user.get("name", ""),
                "is_active": user.get("is_active", True)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during user login: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to authenticate user: {str(e)}"
        )

@router.get("/auth/profile")
async def get_user_profile(
    current_user: Dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get user profile and OAuth accounts for authenticated user.
    
    Args:
        current_user: Current authenticated user
        db_session: Database session
        
    Returns:
        Dict containing user profile and OAuth accounts
    """
    try:
        user_id = current_user.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user token"
            )
        
        logger.info(f"Getting user profile for user: {user_id}")
        
        result = UserManagementController.get_user_oauth_accounts(
            db_session, user_id
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting user profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user profile: {str(e)}"
        )

# =====================================================
# HEALTH AND STATUS ROUTES
# =====================================================

@router.get("/health/oauth")
async def oauth_health_check() -> Dict[str, Any]:
    """
    Health check for OAuth services.
    
    Returns:
        Dict containing OAuth service status
    """
    try:
        # Check Spotify OAuth configuration
        from providers.spotify.v1.oauth import validate_spotify_config
        spotify_config = validate_spotify_config()
        
        return {
            "success": True,
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "spotify": {
                    "configured": spotify_config["fully_configured"],
                    "client_id": bool(spotify_config["client_id"]),
                    "client_secret": bool(spotify_config["client_secret"]),
                    "redirect_uri": bool(spotify_config["redirect_uri"]),
                    "scopes": bool(spotify_config["scopes"])
                }
            },
            "status": "healthy" if spotify_config["fully_configured"] else "partially_configured"
        }
        
    except Exception as e:
        logger.error(f"OAuth health check failed: {e}")
        return {
            "success": False,
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
            "status": "unhealthy"
        }
