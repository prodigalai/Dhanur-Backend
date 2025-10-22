#!/usr/bin/env python3
"""
Enhanced Spotify OAuth Controller for Content Crew Prodigal
Production-ready with user management integration and comprehensive logging
"""

import logging
import os
import secrets
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from providers.spotify.v1.oauth import (
    get_authorization_url, get_user_profile
)
from controllers.user_management_controller import UserManagementController
from models.sqlalchemy_models import User, OAuthAccount
from utils.error_handler import (
    ValidationException, AuthenticationException, 
    DatabaseException, ContentCrewException
)

logger = logging.getLogger(__name__)

class EnhancedSpotifyController:
    """Enhanced controller for Spotify OAuth with user management."""
    
    @staticmethod
    def initiate_oauth_flow(
        user_id: Optional[str] = None,
        email: Optional[str] = None,
        create_account: bool = False
    ) -> Dict[str, Any]:
        """
        Initiate Spotify OAuth flow with optional user account creation.
        
        Args:
            user_id: Existing user ID (if linking to existing account)
            email: User email (if creating new account)
            create_account: Whether to create a new user account
            
        Returns:
            Dict containing authorization URL and flow metadata
        """
        try:
            # Generate PKCE values
            code_verifier = secrets.token_urlsafe(64)
            state = secrets.token_urlsafe(32)
            
            # Create state payload with user context
            state_payload = {
                "state": state,
                "code_verifier": code_verifier,
                "user_id": user_id,
                "email": email,
                "create_account": create_account,
                "timestamp": datetime.utcnow().isoformat(),
                "flow_type": "enhanced_spotify_oauth"
            }
            
            # Store state payload (in production, use Redis/database)
            from routes.route import store_oauth_state
            store_oauth_state(state, state_payload)
            
            # Generate authorization URL
            auth_data = get_authorization_url(state, code_verifier)
            
            logger.info(f"Initiated Spotify OAuth flow: state={state[:10]}..., user_id={user_id}, create_account={create_account}")
            
            return {
                "success": True,
                "authorization_url": auth_data["authorization_url"],
                "state": state,
                "flow_metadata": {
                    "user_id": user_id,
                    "email": email,
                    "create_account": create_account,
                    "flow_type": "enhanced_spotify_oauth"
                },
                "message": "Redirect to authorization_url to complete OAuth"
            }
            
        except Exception as e:
            logger.error(f"Error initiating Spotify OAuth flow: {e}")
            raise ContentCrewException(f"Failed to initiate OAuth flow: {str(e)}")
    
    @staticmethod
    async def handle_oauth_callback(
        db_session: Session,
        code: str,
        state: str
    ) -> Dict[str, Any]:
        """
        Handle Spotify OAuth callback with enhanced user management.
        
        Args:
            db_session: Database session
            code: Authorization code from Spotify
            state: State parameter for CSRF protection
            
        Returns:
            Dict containing OAuth result and user management info
        """
        try:
            logger.info(f"Processing Spotify OAuth callback: code={code[:10]}..., state={state[:10]}...")
            
            # Retrieve stored state payload
            from routes.route import get_stored_oauth_state
            state_payload = get_stored_oauth_state(state)
            
            if not state_payload:
                logger.error(f"Invalid or expired state: {state[:10]}...")
                raise ValidationException("Invalid or expired OAuth state")
            
            # Extract flow information
            user_id = state_payload.get("user_id")
            email = state_payload.get("email")
            create_account = state_payload.get("create_account", False)
            code_verifier = state_payload.get("code_verifier")
            
            if not code_verifier:
                logger.error(f"Missing code_verifier in state payload: {state[:10]}...")
                raise ValidationException("Missing OAuth code verifier")
            
            # Exchange code for tokens
            from routes.route import exchange_spotify_code_for_tokens
            token_data = await exchange_spotify_code_for_tokens(code, code_verifier)
            
            if not token_data.get("access_token"):
                logger.error("Failed to exchange authorization code for tokens")
                raise AuthenticationException("Failed to exchange authorization code for tokens")
            
            # Get user profile from Spotify
            profile_data = get_user_profile(token_data["access_token"])
            
            # Handle user account creation/linking
            user_result = await EnhancedSpotifyController._handle_user_account(
                db_session, user_id, email, create_account, profile_data
            )
            
            # Link OAuth account to user
            oauth_result = UserManagementController.link_oauth_account(
                db_session=db_session,
                user_id=user_result["user"]["id"],
                provider="spotify",
                provider_user_id=profile_data.get("spotify_id"),
                access_token=token_data["access_token"],
                refresh_token=token_data.get("refresh_token"),
                expires_in=token_data.get("expires_in", 3600),
                profile_data=profile_data
            )
            
            logger.info(f"Spotify OAuth completed successfully for user: {user_result['user']['email']}")
            
            return {
                "success": True,
                "message": "Spotify OAuth completed successfully",
                "user": user_result["user"],
                "oauth_account": oauth_result["oauth_account"],
                "profile": profile_data,
                "tokens": {
                    "access_token": token_data.get("access_token"),
                    "refresh_token": token_data.get("refresh_token"),
                    "expires_in": token_data.get("expires_in"),
                    "expires_at": (datetime.utcnow() + timedelta(seconds=token_data.get("expires_in", 3600))).isoformat()
                },
                "flow_metadata": {
                    "flow_type": "enhanced_spotify_oauth",
                    "account_created": user_result.get("account_created", False),
                    "account_linked": True
                }
            }
            
        except Exception as e:
            logger.error(f"Error handling Spotify OAuth callback: {e}")
            raise ContentCrewException(f"Failed to handle OAuth callback: {str(e)}")
    
    @staticmethod
    async def _handle_user_account(
        db_session: Session,
        user_id: Optional[str],
        email: Optional[str],
        create_account: bool,
        profile_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle user account creation or linking based on OAuth flow.
        
        Args:
            db_session: Database session
            user_id: Existing user ID (if linking to existing account)
            email: User email (if creating new account)
            create_account: Whether to create a new user account
            profile_data: Spotify profile data
            
        Returns:
            Dict containing user info and account status
        """
        try:
            # If user_id provided, link to existing account
            if user_id:
                user = db_session.query(User).filter(
                    User.id == user_id,
                    User.is_active == True
                ).first()
                
                if not user:
                    raise ValidationException("User not found or inactive")
                
                logger.info(f"Linking Spotify OAuth to existing user: {user.email}")
                
                return {
                    "user": {
                        "id": str(user.id),
                        "email": user.email,
                        "name": user.name,
                        "is_verified": user.is_verified
                    },
                    "account_created": False,
                    "account_linked": True
                }
            
            # If create_account is True, create new user account
            if create_account and email:
                # Check if user already exists with this email
                existing_user = db_session.query(User).filter(
                    User.email == email.lower().strip()
                ).first()
                
                if existing_user:
                    logger.info(f"Linking Spotify OAuth to existing user: {existing_user.email}")
                    return {
                        "user": {
                            "id": str(existing_user.id),
                            "email": existing_user.email,
                            "name": existing_user.name,
                            "is_verified": existing_user.is_verified
                        },
                        "account_created": False,
                        "account_linked": True
                    }
                
                # Create new user account
                spotify_name = profile_data.get("display_name", "Spotify User")
                spotify_email = profile_data.get("email", email)
                
                # Generate secure password for OAuth users
                oauth_password = secrets.token_urlsafe(32)
                
                user_result = UserManagementController.register_user(
                    db_session=db_session,
                    email=spotify_email,
                    password=oauth_password,
                    full_name=spotify_name,
                    organization_name=None,
                    phone=None,
                    timezone="UTC"
                )
                
                logger.info(f"Created new user account via Spotify OAuth: {spotify_email}")
                
                return {
                    "user": user_result["user"],
                    "account_created": True,
                    "account_linked": True,
                    "oauth_password": oauth_password  # For user notification
                }
            
            # Anonymous OAuth flow (no user account)
            logger.info("Spotify OAuth completed in anonymous mode")
            
            return {
                "user": {
                    "id": None,
                    "email": profile_data.get("email"),
                    "name": profile_data.get("display_name"),
                    "is_verified": False
                },
                "account_created": False,
                "account_linked": False
            }
            
        except Exception as e:
            logger.error(f"Error handling user account: {e}")
            raise ContentCrewException(f"Failed to handle user account: {str(e)}")
    
    @staticmethod
    def refresh_spotify_tokens(
        db_session: Session,
        user_id: str,
        oauth_account_id: str
    ) -> Dict[str, Any]:
        """
        Refresh Spotify access tokens for a user.
        
        Args:
            db_session: Database session
            user_id: User ID
            oauth_account_id: OAuth account ID
            
        Returns:
            Dict containing refreshed token info
        """
        try:
            # Get OAuth account
            oauth_account = db_session.query(OAuthAccount).filter(
                OAuthAccount.id == oauth_account_id,
                OAuthAccount.user_id == user_id,
                OAuthAccount.provider == "spotify",
                OAuthAccount.is_active == True
            ).first()
            
            if not oauth_account:
                raise ValidationException("Spotify OAuth account not found")
            
            if not oauth_account.refresh_token:
                raise ValidationException("No refresh token available")
            
            # Refresh tokens using Spotify API
            from providers.spotify.v1.oauth import refresh_access_token
            refresh_result = refresh_access_token(oauth_account.refresh_token)
            
            # Update OAuth account with new tokens
            oauth_account.access_token = refresh_result["access_token"]
            if refresh_result.get("refresh_token"):
                oauth_account.refresh_token = refresh_result["refresh_token"]
            
            oauth_account.expires_at = datetime.utcnow() + timedelta(seconds=refresh_result.get("expires_in", 3600))
            oauth_account.access_token_expires_at = oauth_account.expires_at
            oauth_account.last_token_refresh = datetime.utcnow()
            oauth_account.token_refresh_count += 1
            oauth_account.updated_at = datetime.utcnow()
            
            db_session.commit()
            
            logger.info(f"Refreshed Spotify tokens for user: {user_id}")
            
            return {
                "success": True,
                "message": "Spotify tokens refreshed successfully",
                "tokens": {
                    "access_token": refresh_result["access_token"],
                    "refresh_token": refresh_result.get("refresh_token"),
                    "expires_in": refresh_result.get("expires_in"),
                    "expires_at": oauth_account.expires_at.isoformat() if oauth_account.expires_at else None
                },
                "oauth_account": {
                    "id": str(oauth_account.id),
                    "provider": oauth_account.provider,
                    "provider_user_id": oauth_account.provider_user_id,
                    "token_refresh_count": oauth_account.token_refresh_count,
                    "last_token_refresh": oauth_account.last_token_refresh.isoformat() if oauth_account.last_token_refresh else None
                }
            }
            
        except Exception as e:
            logger.error(f"Error refreshing Spotify tokens: {e}")
            if isinstance(e, ValidationException):
                raise
            raise ContentCrewException(f"Failed to refresh Spotify tokens: {str(e)}")
    
    @staticmethod
    def get_spotify_account_status(
        db_session: Session,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Get comprehensive Spotify account status for a user.
        
        Args:
            db_session: Database session
            user_id: User ID
            
        Returns:
            Dict containing Spotify account status and metadata
        """
        try:
            # Get user info
            user = db_session.query(User).filter(
                User.id == user_id,
                User.is_active == True
            ).first()
            
            if not user:
                raise ValidationException("User not found or inactive")
            
            # Get Spotify OAuth account
            spotify_account = db_session.query(OAuthAccount).filter(
                OAuthAccount.user_id == user_id,
                OAuthAccount.provider == "spotify",
                OAuthAccount.is_active == True
            ).first()
            
            if not spotify_account:
                return {
                    "success": True,
                    "connected": False,
                    "message": "No Spotify account connected",
                    "user": {
                        "id": str(user.id),
                        "email": user.email,
                        "name": user.name
                    }
                }
            
            # Check token status
            is_expired = spotify_account.expires_at and spotify_account.expires_at < datetime.utcnow()
            needs_refresh = spotify_account.expires_at and (
                spotify_account.expires_at - datetime.utcnow()
            ).total_seconds() < 300  # 5 minutes
            
            return {
                "success": True,
                "connected": True,
                "is_expired": is_expired,
                "needs_refresh": needs_refresh,
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "name": user.name
                },
                "spotify_account": {
                    "id": str(spotify_account.id),
                    "provider_user_id": spotify_account.provider_user_id,
                    "is_expired": is_expired,
                    "expires_at": spotify_account.expires_at.isoformat() if spotify_account.expires_at else None,
                    "token_refresh_count": spotify_account.token_refresh_count,
                    "last_token_refresh": spotify_account.last_token_refresh.isoformat() if spotify_account.last_token_refresh else None,
                    "profile_data": spotify_account.profile_data,
                    "created_at": spotify_account.created_at.isoformat() if spotify_account.created_at else None,
                    "updated_at": spotify_account.updated_at.isoformat() if spotify_account.updated_at else None
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting Spotify account status: {e}")
            if isinstance(e, ValidationException):
                raise
            raise ContentCrewException(f"Failed to get Spotify account status: {str(e)}")
