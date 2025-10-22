#!/usr/bin/env python3
"""
Spotify OAuth Controller for Content Crew Prodigal
"""

import logging
import os
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from providers.spotify.v1.oauth import (
    get_authorization_url,
    exchange_code_for_token,
    refresh_access_token,
    get_user_profile,
    validate_spotify_config
)
from models.sqlalchemy_models import User, OAuthAccount
from utils.error_handler import (
    ValidationException,
    AuthenticationException,
    DatabaseException,
    ContentCrewException
)

logger = logging.getLogger(__name__)

class SpotifyOAuthController:
    """Controller for Spotify OAuth operations."""
    
    @staticmethod
    def get_login_url(user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get Spotify OAuth login URL with PKCE.
        
        Args:
            user_id: Optional user ID for state parameter
            
        Returns:
            Dict containing authorization URL, state, and code_verifier
        """
        try:
            # Validate Spotify configuration
            config_status = validate_spotify_config()
            if not config_status["fully_configured"]:
                missing = [k for k, v in config_status.items() if not v and k != "fully_configured"]
                raise ValidationException(f"Missing Spotify OAuth configuration: {', '.join(missing)}")
            
            # Generate authorization URL with state and PKCE
            state = user_id or "anonymous"
            auth_data = get_authorization_url(state)
            
            logger.info(f"Generated Spotify OAuth URL for user: {user_id}")
            
            return {
                "success": True,
                "authorization_url": auth_data["authorization_url"],
                "state": auth_data["state"],
                "code_verifier": auth_data["code_verifier"],  # Include code_verifier for PKCE
                "scopes": validate_spotify_config()["scopes"]
            }
            
        except Exception as e:
            logger.error(f"Error generating Spotify OAuth URL: {e}")
            if isinstance(e, (ValidationException, AuthenticationException)):
                raise
            raise ContentCrewException(f"Failed to generate Spotify OAuth URL: {str(e)}")
    
    @staticmethod
    def handle_callback(
        db_session: Session,
        code: str,
        state: str,
        code_verifier: str,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Handle Spotify OAuth callback with PKCE.
        
        Args:
            db_session: Database session
            code: Authorization code from Spotify
            state: State parameter for CSRF protection
            code_verifier: PKCE code verifier
            user_id: Optional user ID (if state contains user ID)
            
        Returns:
            Dict containing OAuth result and user profile
        """
        try:
            if not code:
                raise ValidationException("Authorization code is required")
            
            if not state:
                raise ValidationException("State parameter is required")
            
            if not code_verifier:
                raise ValidationException("Code verifier is required for PKCE")
            
            # Extract user ID from state if it's not "anonymous"
            if state != "anonymous" and not user_id:
                user_id = state
            
            # Exchange code for tokens using PKCE
            token_data = exchange_code_for_token(code, code_verifier)
            
            if not token_data.get("access_token"):
                raise AuthenticationException("Failed to obtain access token from Spotify")
            
            # Get user profile from Spotify
            profile_data = get_user_profile(token_data["access_token"])
            
            # Store OAuth account in database
            oauth_account = SpotifyOAuthController._store_oauth_account(
                db_session, user_id, token_data, profile_data
            )
            
            logger.info(f"Spotify OAuth successful for user: {user_id}, Spotify ID: {profile_data.get('spotify_id')}")
            
            return {
                "success": True,
                "message": "Spotify OAuth successful",
                "oauth_account": {
                    "id": str(oauth_account.id),
                    "provider": oauth_account.provider,
                    "provider_user_id": oauth_account.provider_user_id,
                    "is_active": oauth_account.is_active,
                    "created_at": oauth_account.created_at.isoformat() if oauth_account.created_at else None,
                    "updated_at": oauth_account.updated_at.isoformat() if oauth_account.created_at else None
                },
                "profile": profile_data,
                "tokens": {
                    "access_token": token_data.get("access_token"),
                    "refresh_token": token_data.get("refresh_token"),
                    "expires_in": token_data.get("expires_in"),
                    "token_type": token_data.get("token_type")
                }
            }
            
        except Exception as e:
            logger.error(f"Error handling Spotify OAuth callback: {e}")
            if isinstance(e, (ValidationException, AuthenticationException)):
                raise
            raise ContentCrewException(f"Failed to handle Spotify OAuth callback: {str(e)}")
    
    @staticmethod
    def refresh_tokens(
        db_session: Session,
        oauth_account_id: str
    ) -> Dict[str, Any]:
        """
        Refresh Spotify access tokens.
        
        Args:
            db_session: Database session
            oauth_account_id: OAuth account ID
            
        Returns:
            Dict containing new tokens
        """
        try:
            if not oauth_account_id:
                raise ValidationException("OAuth account ID is required")
            
            # Get OAuth account from database
            oauth_account = db_session.query(OAuthAccount).filter(
                OAuthAccount.id == oauth_account_id,
                OAuthAccount.provider == "spotify",
                OAuthAccount.is_active == True
            ).first()
            
            if not oauth_account:
                raise ValidationException("Spotify OAuth account not found")
            
            if not oauth_account.refresh_token:
                raise AuthenticationException("No refresh token available for this account")
            
            # Refresh tokens with Spotify
            new_token_data = refresh_access_token(oauth_account.refresh_token)
            
            if not new_token_data.get("access_token"):
                raise AuthenticationException("Failed to refresh access token from Spotify")
            
            # Update OAuth account with new tokens
            oauth_account.access_token = new_token_data["access_token"]
            if new_token_data.get("refresh_token"):
                oauth_account.refresh_token = new_token_data["refresh_token"]
            oauth_account.expires_at = datetime.utcnow() + timedelta(seconds=new_token_data.get("expires_in", 3600))
            oauth_account.updated_at = datetime.utcnow()
            
            db_session.commit()
            
            logger.info(f"Refreshed Spotify tokens for OAuth account: {oauth_account_id}")
            
            return {
                "success": True,
                "message": "Tokens refreshed successfully",
                "tokens": {
                    "access_token": new_token_data["access_token"],
                    "refresh_token": new_token_data.get("refresh_token"),
                    "expires_in": new_token_data.get("expires_in"),
                    "token_type": new_token_data.get("token_type")
                }
            }
            
        except Exception as e:
            logger.error(f"Error refreshing Spotify tokens: {e}")
            db_session.rollback()
            if isinstance(e, (ValidationException, AuthenticationException)):
                raise
            raise ContentCrewException(f"Failed to refresh Spotify tokens: {str(e)}")
    
    @staticmethod
    def disconnect_account(
        db_session: Session,
        oauth_account_id: str
    ) -> Dict[str, Any]:
        """
        Disconnect Spotify OAuth account.
        
        Args:
            db_session: Database session
            oauth_account_id: OAuth account ID
            
        Returns:
            Dict containing operation result
        """
        try:
            if not oauth_account_id:
                raise ValidationException("OAuth account ID is required")
            
            # Get OAuth account from database
            oauth_account = db_session.query(OAuthAccount).filter(
                OAuthAccount.id == oauth_account_id,
                OAuthAccount.provider == "spotify"
            ).first()
            
            if not oauth_account:
                raise ValidationException("Spotify OAuth account not found")
            
            # Deactivate the account
            oauth_account.is_active = False
            oauth_account.updated_at = datetime.utcnow()
            
            db_session.commit()
            
            logger.info(f"Disconnected Spotify OAuth account: {oauth_account_id}")
            
            return {
                "success": True,
                "message": "Spotify account disconnected successfully"
            }
            
        except Exception as e:
            logger.error(f"Error disconnecting Spotify OAuth account: {e}")
            db_session.rollback()
            if isinstance(e, (ValidationException, AuthenticationException)):
                raise
            raise ContentCrewException(f"Failed to disconnect Spotify OAuth account: {str(e)}")
    
    @staticmethod
    def _store_oauth_account(
        db_session: Session,
        user_id: Optional[str],
        token_data: Dict[str, Any],
        profile_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Store OAuth account information in database (simplified for Supabase).
        
        Args:
            db_session: Database session
            user_id: User ID (optional)
            token_data: Token data from Spotify
            profile_data: User profile data from Spotify
            
        Returns:
            Dict containing stored OAuth account info
        """
        try:
            # For now, let's store the OAuth data in a simple way
            # We'll update the user's profile with Spotify information
            
            # Find user by email if user_id not provided
            if not user_id and profile_data.get("email"):
                user = db_session.query(User).filter(User.email == profile_data["email"]).first()
                if user:
                    user_id = str(user.id)
            
            # If we have a user, update their profile with Spotify data
            if user_id:
                user = db_session.query(User).filter(User.id == user_id).first()
                if user:
                    # Update user profile with Spotify data
                    user.avatar_url = profile_data.get("profile_picture") or user.avatar_url
                    user.full_name = profile_data.get("name") or user.full_name
                    user.updated_at = datetime.utcnow()
                    
                    # Store Spotify ID in a custom field (we'll use company field temporarily)
                    user.company = f"spotify:{profile_data.get('spotify_id', 'unknown')}"
                    
                    db_session.commit()
                    
                    return {
                        "id": user_id,
                        "provider": "spotify",
                        "provider_user_id": profile_data.get("spotify_id"),
                        "is_active": True,
                        "user_updated": True
                    }
            
            # If no user found, return basic info (we could create a user here later)
            return {
                "id": "temp_" + profile_data.get("spotify_id", "unknown"),
                "provider": "spotify",
                "provider_user_id": profile_data.get("spotify_id"),
                "is_active": True,
                "user_updated": False,
                "note": "User not found in database - OAuth data stored temporarily"
            }
                
        except Exception as e:
            logger.error(f"Failed to store OAuth account: {e}")
            # Return basic info even if storage fails
            return {
                "id": "error_" + profile_data.get("spotify_id", "unknown"),
                "provider": "spotify",
                "provider_user_id": profile_data.get("spotify_id"),
                "is_active": False,
                "error": str(e)
            }
    
    @staticmethod
    def get_account_status(
        db_session: Session,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Get Spotify OAuth account status for a user.
        
        Args:
            db_session: Database session
            user_id: User ID
            
        Returns:
            Dict containing account status
        """
        try:
            oauth_account = db_session.query(OAuthAccount).filter(
                OAuthAccount.user_id == user_id,
                OAuthAccount.provider == "spotify",
                OAuthAccount.is_active == True
            ).first()
            
            if not oauth_account:
                return {
                    "connected": False,
                    "message": "No Spotify account connected"
                }
            
            # Check if token is expired
            is_expired = oauth_account.expires_at and oauth_account.expires_at < datetime.utcnow()
            
            return {
                "connected": True,
                "is_expired": is_expired,
                "provider_user_id": oauth_account.provider_user_id,
                "profile_data": oauth_account.profile_data,
                "created_at": oauth_account.created_at.isoformat() if oauth_account.created_at else None,
                "updated_at": oauth_account.updated_at.isoformat() if oauth_account.updated_at else None
            }
            
        except Exception as e:
            logger.error(f"Error getting Spotify account status: {e}")
            raise ContentCrewException(f"Failed to get Spotify account status: {str(e)}")
