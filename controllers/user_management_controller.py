#!/usr/bin/env python3
"""
User Management Controller for Content Crew Prodigal
Production-ready user registration, login, and OAuth account management
"""

import logging
import os
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from models.sqlalchemy_models import User, OAuthAccount
from utils.error_handler import (
    ValidationException, AuthenticationException, 
    DatabaseException, ContentCrewException
)
from services.jwt_service import JWTService
from services.password_validation import validate_password_strength

logger = logging.getLogger(__name__)

class UserManagementController:
    """Controller for user management operations."""
    
    @staticmethod
    def register_user(
        db_session: Session,
        email: str,
        password: str,
        full_name: str,
        organization_name: Optional[str] = None,
        phone: Optional[str] = None,
        timezone: str = "UTC"
    ) -> Dict[str, Any]:
        """
        Register a new user with comprehensive validation.
        
        Args:
            db_session: Database session
            email: User email address
            password: User password
            full_name: User's full name
            organization_name: Optional organization name
            phone: Optional phone number
            timezone: User's timezone (default: UTC)
            
        Returns:
            Dict containing user info and access token
        """
        try:
            # Input validation
            if not email or not email.strip():
                raise ValidationException("Email is required")
            
            if not password or not password.strip():
                raise ValidationException("Password is required")
            
            if not full_name or not full_name.strip():
                raise ValidationException("Full name is required")
            
            # Email format validation
            if "@" not in email or "." not in email:
                raise ValidationException("Invalid email format")
            
            # Password strength validation
            password_validation = validate_password_strength(password)
            if not password_validation["is_valid"]:
                raise ValidationException(f"Password too weak: {password_validation['message']}")
            
            # Check if user already exists
            existing_user = db_session.query(User).filter(
                User.email == email.lower().strip()
            ).first()
            
            if existing_user:
                raise ValidationException("User with this email already exists")
            
            # Create new user
            new_user = User(
                email=email.lower().strip(),
                password_hash=hashlib.sha256(password.encode()).hexdigest(),  # In production, use bcrypt
                name=full_name.strip(),
                is_verified=False,
                is_active=True,
                phone=phone.strip() if phone else None,
                timezone=None  # TODO: Add timezone parameter if needed
            )
            
            db_session.add(new_user)
            db_session.commit()
            db_session.refresh(new_user)
            
            # Generate JWT token
            jwt_service = JWTService()
            access_token = jwt_service.create_access_token(
                data={"sub": str(new_user.id), "email": new_user.email}
            )
            
            logger.info(f"User registered successfully: {new_user.email} (ID: {new_user.id})")
            
            return {
                "success": True,
                "message": "User registered successfully",
                "user": {
                    "id": str(new_user.id),
                    "email": new_user.email,
                    "name": new_user.name,
                    "is_verified": new_user.is_verified,
                    "created_at": new_user.created_at.isoformat() if new_user.created_at else None
                },
                "access_token": access_token,
                "token_type": "bearer"
            }
            
        except IntegrityError as e:
            db_session.rollback()
            logger.error(f"Database integrity error during user registration: {e}")
            raise DatabaseException("User registration failed due to database constraint")
            
        except Exception as e:
            db_session.rollback()
            logger.error(f"Error during user registration: {e}")
            if isinstance(e, (ValidationException, AuthenticationException)):
                raise
            raise ContentCrewException(f"Failed to register user: {str(e)}")
    
    @staticmethod
    def login_user(
        db_session: Session,
        email: str,
        password: str
    ) -> Dict[str, Any]:
        """
        Authenticate user login with comprehensive validation.
        
        Args:
            db_session: Database session
            email: User email address
            password: User password
            
        Returns:
            Dict containing user info and access token
        """
        try:
            # Input validation
            if not email or not email.strip():
                raise ValidationException("Email is required")
            
            if not password or not password.strip():
                raise ValidationException("Password is required")
            
            # Find user by email
            user = db_session.query(User).filter(
                User.email == email.lower().strip(),
                User.is_active == True
            ).first()
            
            if not user:
                logger.warning(f"Login attempt with non-existent email: {email}")
                raise AuthenticationException("Invalid email or password")
            
            # Verify password
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            if user.password_hash != password_hash:
                logger.warning(f"Failed login attempt for user: {user.email}")
                raise AuthenticationException("Invalid email or password")
            
            # Check if user is verified (optional for demo)
            if not user.is_verified:
                logger.info(f"Unverified user logged in: {user.email}")
            
            # Generate JWT token
            jwt_service = JWTService()
            access_token = jwt_service.create_access_token(
                data={"sub": str(user.id), "email": user.email}
            )
            
            # Update last login
            user.last_login = datetime.utcnow()
            db_session.commit()
            
            logger.info(f"User logged in successfully: {user.email} (ID: {user.id})")
            
            return {
                "success": True,
                "message": "Login successful",
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "name": user.name,
                    "is_verified": user.is_verified,
                    "last_login": user.last_login.isoformat() if user.last_login else None
                },
                "access_token": access_token,
                "token_type": "bearer"
            }
            
        except Exception as e:
            logger.error(f"Error during user login: {e}")
            if isinstance(e, (ValidationException, AuthenticationException)):
                raise
            raise ContentCrewException(f"Failed to authenticate user: {str(e)}")
    
    @staticmethod
    def link_oauth_account(
        db_session: Session,
        user_id: str,
        provider: str,
        provider_user_id: str,
        access_token: str,
        refresh_token: Optional[str] = None,
        expires_in: int = 3600,
        profile_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Link an OAuth account to an existing user.
        
        Args:
            db_session: Database session
            user_id: User ID to link the OAuth account to
            provider: OAuth provider (spotify, linkedin, youtube, etc.)
            provider_user_id: Provider's user ID
            access_token: OAuth access token
            refresh_token: OAuth refresh token (optional)
            expires_in: Token expiration time in seconds
            profile_data: Provider profile data
            
        Returns:
            Dict containing linked OAuth account info
        """
        try:
            # Validate inputs
            if not user_id or not provider or not provider_user_id or not access_token:
                raise ValidationException("Missing required OAuth account information")
            
            # Check if user exists
            user = db_session.query(User).filter(
                User.id == user_id,
                User.is_active == True
            ).first()
            
            if not user:
                raise ValidationException("User not found or inactive")
            
            # Check if OAuth account already exists for this provider + user
            existing_account = db_session.query(OAuthAccount).filter(
                OAuthAccount.user_id == user_id,
                OAuthAccount.provider == provider
            ).first()
            
            if existing_account:
                # Update existing account
                existing_account.access_token = access_token
                if refresh_token:
                    existing_account.refresh_token = refresh_token
                existing_account.expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                existing_account.profile_data = profile_data or {}
                existing_account.is_active = True
                existing_account.updated_at = datetime.utcnow()
                existing_account.last_token_refresh = datetime.utcnow()
                
                db_session.commit()
                db_session.refresh(existing_account)
                
                logger.info(f"Updated existing OAuth account for user {user.email}: {provider}")
                
                return {
                    "success": True,
                    "message": f"Updated existing {provider} OAuth account",
                    "oauth_account": {
                        "id": str(existing_account.id),
                        "provider": existing_account.provider,
                        "provider_user_id": existing_account.provider_user_id,
                        "is_active": existing_account.is_active,
                        "updated_at": existing_account.updated_at.isoformat() if existing_account.updated_at else None
                    }
                }
            else:
                # Create new OAuth account
                new_oauth_account = OAuthAccount(
                    user_id=user_id,
                    provider=provider,
                    provider_user_id=provider_user_id,
                    access_token=access_token,
                    refresh_token=refresh_token,
                    expires_at=datetime.utcnow() + timedelta(seconds=expires_in),
                    scope=os.getenv(f"{provider.upper()}_SCOPES", ""),
                    profile_data=profile_data or {},
                    is_active=True,
                    access_token_expires_at=datetime.utcnow() + timedelta(seconds=expires_in),
                    last_token_refresh=datetime.utcnow()
                )
                
                db_session.add(new_oauth_account)
                db_session.commit()
                db_session.refresh(new_oauth_account)
                
                logger.info(f"Created new OAuth account for user {user.email}: {provider}")
                
                return {
                    "success": True,
                    "message": f"Created new {provider} OAuth account",
                    "oauth_account": {
                        "id": str(new_oauth_account.id),
                        "provider": new_oauth_account.provider,
                        "provider_user_id": new_oauth_account.provider_user_id,
                        "is_active": new_oauth_account.is_active,
                        "created_at": new_oauth_account.created_at.isoformat() if new_oauth_account.created_at else None
                    }
                }
                
        except Exception as e:
            db_session.rollback()
            logger.error(f"Error linking OAuth account: {e}")
            if isinstance(e, ValidationException):
                raise
            raise ContentCrewException(f"Failed to link OAuth account: {str(e)}")
    
    @staticmethod
    def get_user_oauth_accounts(
        db_session: Session,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Get all OAuth accounts for a user.
        
        Args:
            db_session: Database session
            user_id: User ID
            
        Returns:
            Dict containing user's OAuth accounts
        """
        try:
            # Check if user exists
            user = db_session.query(User).filter(
                User.id == user_id,
                User.is_active == True
            ).first()
            
            if not user:
                raise ValidationException("User not found or inactive")
            
            # Get OAuth accounts
            oauth_accounts = db_session.query(OAuthAccount).filter(
                OAuthAccount.user_id == user_id,
                OAuthAccount.is_active == True
            ).all()
            
            accounts_info = []
            for account in oauth_accounts:
                # Check if token is expired
                is_expired = account.expires_at and account.expires_at < datetime.utcnow()
                
                accounts_info.append({
                    "id": str(account.id),
                    "provider": account.provider,
                    "provider_user_id": account.provider_user_id,
                    "is_expired": is_expired,
                    "expires_at": account.expires_at.isoformat() if account.expires_at else None,
                    "profile_data": account.profile_data,
                    "created_at": account.created_at.isoformat() if account.created_at else None,
                    "updated_at": account.updated_at.isoformat() if account.updated_at else None
                })
            
            logger.info(f"Retrieved {len(accounts_info)} OAuth accounts for user {user.email}")
            
            return {
                "success": True,
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "name": user.name
                },
                "oauth_accounts": accounts_info,
                "total_accounts": len(accounts_info)
            }
            
        except Exception as e:
            logger.error(f"Error getting user OAuth accounts: {e}")
            if isinstance(e, ValidationException):
                raise
            raise ContentCrewException(f"Failed to get user OAuth accounts: {str(e)}")
    
    @staticmethod
    def disconnect_oauth_account(
        db_session: Session,
        user_id: str,
        oauth_account_id: str
    ) -> Dict[str, Any]:
        """
        Disconnect an OAuth account from a user.
        
        Args:
            db_session: Database session
            user_id: User ID
            oauth_account_id: OAuth account ID to disconnect
            
        Returns:
            Dict containing operation result
        """
        try:
            # Check if user exists
            user = db_session.query(User).filter(
                User.id == user_id,
                User.is_active == True
            ).first()
            
            if not user:
                raise ValidationException("User not found or inactive")
            
            # Find OAuth account
            oauth_account = db_session.query(OAuthAccount).filter(
                OAuthAccount.id == oauth_account_id,
                OAuthAccount.user_id == user_id,
                OAuthAccount.is_active == True
            ).first()
            
            if not oauth_account:
                raise ValidationException("OAuth account not found or not linked to user")
            
            # Deactivate the account
            oauth_account.is_active = False
            oauth_account.updated_at = datetime.utcnow()
            
            db_session.commit()
            
            logger.info(f"Disconnected OAuth account {oauth_account.provider} for user {user.email}")
            
            return {
                "success": True,
                "message": f"Disconnected {oauth_account.provider} OAuth account",
                "disconnected_account": {
                    "id": str(oauth_account.id),
                    "provider": oauth_account.provider,
                    "provider_user_id": oauth_account.provider_user_id
                }
            }
            
        except Exception as e:
            db_session.rollback()
            logger.error(f"Error disconnecting OAuth account: {e}")
            if isinstance(e, ValidationException):
                raise
            raise ContentCrewException(f"Failed to disconnect OAuth account: {str(e)}")
