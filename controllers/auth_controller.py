#!/usr/bin/env python3
"""
Authentication controller for Content Crew Prodigal
"""

import os
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from fastapi import HTTPException, status
from passlib.context import CryptContext
import hashlib
from bson import ObjectId

from services.jwt_service import generate_jwt, verify_jwt_token, get_jwt_secret
from services.mongodb_service import mongodb_service
from utils.error_handler import (
    ContentCrewException, ValidationException, AuthenticationException, 
    AuthorizationException, ResourceNotFoundException, ConflictException,
    DatabaseException, ExternalServiceException
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Password context for bcrypt with error handling
try:
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
except Exception as e:
    logger.warning(f"Bcrypt context failed, using fallback: {e}")
    pwd_context = None

def hash_password(password: str) -> str:
    """Hash a password using bcrypt or SHA-256 fallback."""
    if pwd_context:
        try:
            return pwd_context.hash(password)
        except Exception as e:
            logger.warning(f"Bcrypt hashing failed, using SHA-256: {e}")
    
    # Fallback to SHA-256
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash. Supports bcrypt ($2b$...) and SHA-256."""
    try:
        # Bcrypt hash
        if isinstance(hashed_password, str) and hashed_password.startswith('$2b$'):
            try:
                import bcrypt as _bcrypt
                return _bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
            except Exception as bcrypt_error:
                logger.error(f"bcrypt.checkpw failed: {bcrypt_error}")
                return False

        # SHA-256 hash fallback (legacy/plain hash storage)
        sha256_hash = hashlib.sha256(plain_password.encode('utf-8')).hexdigest()
        return sha256_hash == hashed_password

    except Exception as e:
        logger.error(f"Password verification failed: {e}")
        return False

def create_user(email: str, password: str, full_name: str) -> Dict[str, Any]:
    """Create a new user in the database."""
    try:
        # Validate input
        if not email or not password or not full_name:
            raise ValidationException("Email, password, and full_name are required")
        
        if len(password) < 8:
            raise ValidationException("Password must be at least 8 characters long", "password")
        
        if len(full_name) < 2:
            raise ValidationException("Full name must be at least 2 characters long", "full_name")
        
        # Check if user already exists in MongoDB
        existing_user = mongodb_service.get_collection('users').find_one({"email": email})
        if existing_user:
            raise ConflictException(f"User with email '{email}' already exists")

        # Create new user data
        from datetime import datetime
        from bson import ObjectId

        user_id = str(ObjectId())
        hashed_password = hash_password(password)

        user_data = {
            "user_id": user_id,
            "email": email,
            "password": hashed_password,
            "name": full_name,
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "last_login": None,
            "profile_picture": None,
            "phone": None,
            "country": None,
            "timezone": None
        }

        # Insert user into MongoDB
        result = mongodb_service.get_collection('users').insert_one(user_data)
        if not result.inserted_id:
            raise DatabaseException("Failed to create user in database", "user_creation")

        # Create user credits
        credits_data = {
            "user_id": user_id,
            "credits": 100,  # Default credits for new users
            "total_earned": 100,
            "total_spent": 0,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "credit_history": [
                {
                    "type": "initial_bonus",
                    "amount": 100,
                    "description": "Welcome bonus credits",
                    "timestamp": datetime.utcnow()
                }
            ]
        }

        credits_result = mongodb_service.get_collection('user_credits').insert_one(credits_data)
        if not credits_result.inserted_id:
            # If credits creation fails, we should ideally rollback user creation
            # But for now, log the error and continue
            logger.warning(f"Failed to create credits for user {user_id}")

        logger.info(f"User created successfully: {email} (ID: {user_id})")

        # Return user data in the expected format
        return {
            "id": user_id,
            "email": email,
            "name": full_name,
            "is_verified": False,
            "is_active": True,
            "created_at": user_data["created_at"],
            "updated_at": user_data["updated_at"],
            "profile_picture": None,
            "phone": None,
            "timezone": None
        }
        
    except (ValidationException, ConflictException):
        # Re-raise validation and conflict exceptions
        raise
    except Exception as e:
        logger.error(f"Unexpected error creating user: {e}")
        raise ContentCrewException("An unexpected error occurred while creating user", "USER_CREATION_ERROR")

def authenticate_user(email: str, password: str) -> Optional[Dict[str, Any]]:
    """Authenticate a user with email and password."""
    try:
        if not email or not password:
            return None

        # Find user by email in MongoDB
        user_data = mongodb_service.get_collection('users').find_one({"email": email})
        if not user_data:
            return None

        # Verify password
        if not verify_password(password, user_data.get("password", "")):
            return None

        # Check if user is active
        if not user_data.get("is_active", True):
            return None

        # Update last login time
        mongodb_service.get_collection('users').update_one(
            {"email": email},
            {"$set": {"last_login": datetime.utcnow()}}
        )

        logger.info(f"User authenticated successfully: {email}")
        return user_data

    except Exception as e:
        logger.error(f"Authentication error for {email}: {e}")
        return None

def register(email: str, password: str, full_name: str, organization_name: str) -> Dict[str, Any]:
    """User registration with organization creation."""
    try:
        # Create user
        user = create_user(email, password, full_name)

        # Create organization (simplified for now)
        organization = {
            "id": str(ObjectId()),
            "name": organization_name,
            "owner_id": user["id"]  # Changed from user["user_id"] to user["id"]
        }

        # Generate JWT tokens for auto-login
        access_token = generate_jwt(
            entity_id=user["id"],
            email=user["email"],
            user_id=user["id"],
            entity_type="user"
        )

        refresh_token = generate_jwt(
            entity_id=user["id"],
            email=user["email"],
            user_id=user["id"],
            entity_type="user",
            purpose="refresh"
        )

        logger.info(f"User registered successfully with organization: {email} (User ID: {user['id']}, Org ID: {organization['id']})")

        return {
            "success": True,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": 86400,
            "message": "Registration successful",
            "user": {
                "id": user["id"],
                "email": user["email"],
                "full_name": user["name"] or "",
                "is_verified": user.get("is_verified", False),
                "is_active": user["is_active"],
                "profile_picture": user.get("profile_picture"),
                "phone": user.get("phone"),
                "timezone": user.get("timezone"),
                "created_at": user["created_at"].isoformat() if user["created_at"] else None,
                "updated_at": user["updated_at"].isoformat() if user["updated_at"] else None
            }
        }
        
    except (ValidationException, ConflictException, DatabaseException, ContentCrewException):
        # Re-raise known exceptions
        raise
    except Exception as e:
        logger.error(f"Unexpected error during registration: {e}")
        raise ContentCrewException("An unexpected error occurred during registration", "REGISTRATION_ERROR")

def login(email: str, password: str) -> Dict[str, Any]:
    """User login with database authentication."""
    try:
        # Validate input
        if not email or not password:
            raise ValidationException("Email and password are required")
        
        # Authenticate user
        user = authenticate_user(email, password)
        if not user:
            raise AuthenticationException("Invalid email or password")

        # Generate JWT tokens
        access_token = generate_jwt(
            entity_id=user["user_id"],
            email=user["email"],
            user_id=user["user_id"],
            entity_type="user"
        )

        refresh_token = generate_jwt(
            entity_id=user["user_id"],
            email=user["email"],
            user_id=user["user_id"],
            entity_type="user",
            purpose="refresh"
        )

        logger.info(f"User logged in successfully: {email} (ID: {user['user_id']})")

        # Simplified response for debugging
        return {
            "success": True,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": 86400,
            "message": "Login successful",
            "user": {
                "id": user["user_id"],
                "email": user["email"],
                "name": user.get("name", ""),
                "is_active": user.get("is_active", True)
            }
        }
        
    except (ValidationException, AuthenticationException):
        # Re-raise known exceptions
        raise
    except Exception as e:
        logger.error(f"Unexpected error during login: {e}")
        raise ContentCrewException("An unexpected error occurred during login", "LOGIN_ERROR")

def refresh_token(refresh_token: str) -> Dict[str, Any]:
    """Refresh access token using refresh token."""
    try:
        if not refresh_token:
            raise ValidationException("Refresh token is required", "refresh_token")
        
        # Verify refresh token
        payload = verify_jwt_token(refresh_token, get_jwt_secret())
        if not payload or payload.get("purpose") != "refresh":
            raise AuthenticationException("Invalid refresh token")
        
        user_id = payload.get("user_id")
        if not user_id:
            raise AuthenticationException("Invalid token payload")
        
        # Get user from MongoDB
        user = mongodb_service.get_collection('users').find_one({"user_id": user_id})
        if not user or not user.get("is_active", True):
            raise ResourceNotFoundException("User", user_id)

        # Generate new tokens
        new_access_token = generate_jwt(
            entity_id=user["user_id"],
            email=user["email"],
            user_id=user["user_id"],
            entity_type="user"
        )

        new_refresh_token = generate_jwt(
            entity_id=user["user_id"],
            email=user["email"],
            user_id=user["user_id"],
            entity_type="user",
            purpose="refresh"
        )
        
        logger.info(f"Token refreshed for user: {user['email']} (ID: {user['user_id']})")
        
        return {
            "success": True,
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
            "expires_in": 86400,
            "message": "Token refreshed successfully",
            "user": {
                "id": user["user_id"],
                "email": user["email"],
                "full_name": user["name"] or "",
                "is_verified": user.get("is_verified", False),
                "is_active": user["is_active"],
                "profile_picture": user.get("profile_picture"),
                "phone": user.get("phone"),
                "timezone": user.get("timezone", None),
                "created_at": user["created_at"].isoformat() if user["created_at"] else None,
                "updated_at": user["updated_at"].isoformat() if user["updated_at"] else None,
                "last_login": user.get("last_login").isoformat() if user.get("last_login") else None
            }
        }
        
    except (ValidationException, AuthenticationException, ResourceNotFoundException):
        # Re-raise known exceptions
        raise
    except Exception as e:
        logger.error(f"Unexpected error during token refresh: {e}")
        raise ContentCrewException("An unexpected error occurred during token refresh", "TOKEN_REFRESH_ERROR")

def get_user_profile(user_id: str) -> Dict[str, Any]:
    """Get user profile from database."""
    try:
        if not user_id:
            raise ValidationException("User ID is required", "user_id")
        
        user = mongodb_service.get_collection('users').find_one({"user_id": user_id})
        if not user:
            raise ResourceNotFoundException("User", user_id)

        return {
            "id": user["user_id"],
            "email": user["email"],
            "full_name": user["name"] or "",
            "is_verified": user.get("is_verified", False),
            "is_active": user["is_active"],
            "profile_picture": user.get("profile_picture"),
            "phone": user.get("phone"),
            "timezone": user.get("timezone", None),
            "created_at": user["created_at"].isoformat() if user["created_at"] else None,
            "updated_at": user["updated_at"].isoformat() if user["updated_at"] else None,
            "last_login": user.get("last_login").isoformat() if user.get("last_login") else None
        }
        
    except (ValidationException, ResourceNotFoundException):
        # Re-raise known exceptions
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting user profile: {e}")
        raise ContentCrewException("An unexpected error occurred getting user profile", "PROFILE_RETRIEVAL_ERROR")

def update_user_profile(user_id: str, profile_data: Dict[str, Any]) -> Dict[str, Any]:
    """Update user profile in database."""
    try:
        if not user_id:
            raise ValidationException("User ID is required", "user_id")
        
        user = mongodb_service.get_collection('users').find_one({"user_id": user_id})
        if not user:
            raise ResourceNotFoundException("User", user_id)

        # Update allowed fields
        allowed_fields = ["name", "profile_picture", "phone", "timezone"]
        update_data = {}
        for field in allowed_fields:
            if field in profile_data:
                if field == "name" and "full_name" in profile_data:
                    update_data[field] = profile_data["full_name"]
                else:
                    update_data[field] = profile_data[field]

        if update_data:
            update_data["updated_at"] = datetime.utcnow()
            mongodb_service.get_collection('users').update_one(
                {"user_id": user_id},
                {"$set": update_data}
            )

        logger.info(f"User profile updated: {user['email']} (ID: {user['user_id']})")

        return get_user_profile(user_id)
        
    except (ValidationException, ResourceNotFoundException):
        # Re-raise known exceptions
        raise
    except Exception as e:
        logger.error(f"Unexpected error updating user profile: {e}")
        raise ContentCrewException("An unexpected error occurred updating user profile", "PROFILE_UPDATE_ERROR")
