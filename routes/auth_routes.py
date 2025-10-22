#!/usr/bin/env python3
"""
User Authentication Routes for Content Crew Prodigal
MongoDB-based authentication with credit system
"""

from fastapi import APIRouter, HTTPException, Depends, Request, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import logging
from datetime import datetime, timedelta, timezone
import hashlib
import os
import string
import random
import secrets
import jwt
from passlib.context import CryptContext

from services.mongodb_service import mongodb_service
from services.user_credits_service import user_credits_service
# from core.config import settings  # Not needed - using environment variables directly
from middleware.auth import get_current_user

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(tags=["Authentication"])

# Password hashing with bcrypt compatibility fix
try:
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
except Exception as e:
    logger.warning(f"Bcrypt context failed, using fallback: {e}")
    # Fallback to SHA-256 if bcrypt fails
    pwd_context = None

# Pydantic models
class UserLoginRequest(BaseModel):
    """Request model for user login."""
    email: str = Field(..., description="User email")
    password: str = Field(..., description="User password")

class UserRegistrationRequest(BaseModel):
    """Request model for user registration."""
    email: str = Field(..., description="User email")
    password: str = Field(..., description="User password")
    name: Optional[str] = Field(None, description="User name")

class AuthResponse(BaseModel):
    """Response model for authentication."""
    success: bool
    message: str
    user_id: Optional[str] = None
    email: Optional[str] = None
    name: Optional[str] = None
    credits: Optional[int] = None
    token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_at: Optional[str] = None

class UserProfileResponse(BaseModel):
    """Response model for user profile."""
    success: bool
    user_id: str
    email: str
    name: str
    credits: int
    total_earned: int
    total_spent: int
    created_at: str
    updated_at: str
    account_type: str
    status: str
    email_verified: bool
    days_active: int
    referral_code: Optional[str] = None
    last_login: Optional[str] = None

class ForgotPasswordRequest(BaseModel):
    """Request model for forgot password."""
    email: str = Field(..., description="User email address")

class ResetPasswordRequest(BaseModel):
    """Request model for reset password."""
    token: str = Field(..., description="Password reset token")
    new_password: str = Field(..., min_length=8, description="New password (minimum 8 characters)")

class ForgotPasswordResponse(BaseModel):
    """Response model for forgot password."""
    success: bool
    message: str
    reset_url: Optional[str] = None  # For development only
    token: Optional[str] = None      # For development only

class ResetPasswordResponse(BaseModel):
    """Response model for reset password."""
    success: bool
    message: str

def hash_password(password: str) -> str:
    """Hash a password using bcrypt or SHA-256 fallback."""
    if pwd_context:
        try:
            return pwd_context.hash(password)
        except Exception as e:
            logger.warning(f"Bcrypt hashing failed, using SHA-256: {e}")
    
    # Fallback to SHA-256
    import hashlib
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash. Supports bcrypt ($2b$...) and SHA-256."""
    try:
        if isinstance(hashed_password, str) and hashed_password.startswith('$2b$'):
            try:
                import bcrypt as _bcrypt
                return _bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
            except Exception as bcrypt_error:
                logger.error(f"bcrypt.checkpw failed: {bcrypt_error}")
                return False

        # SHA-256 legacy support
        import hashlib
        sha256_hash = hashlib.sha256(plain_password.encode('utf-8')).hexdigest()
        return sha256_hash == hashed_password
    except Exception as e:
        logger.error(f"Password verification failed: {e}")
        return False

def create_jwt_token(user_id: str, email: str) -> str:
    """Create a JWT access token for the user."""
    payload = {
        "user_id": user_id,
        "email": email,
        "purpose": "access",
        "exp": datetime.now(timezone.utc) + timedelta(hours=24),
        "iat": datetime.now(timezone.utc)
    }
    return jwt.encode(payload, os.getenv("JWT_SECRET_KEY", "your-secret-key-here"), algorithm="HS256")

def create_refresh_token(user_id: str, email: str) -> str:
    """Create a JWT refresh token for the user."""
    payload = {
        "user_id": user_id,
        "email": email,
        "purpose": "refresh",
        "exp": datetime.now(timezone.utc) + timedelta(days=30),  # 30 days for refresh token
        "iat": datetime.now(timezone.utc)
    }
    return jwt.encode(payload, os.getenv("JWT_SECRET_KEY", "your-secret-key-here"), algorithm="HS256")

def _generate_referral_code(length: int = 8) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return ''.join(random.choices(alphabet, k=length))

def _ensure_unique_referral_code() -> str:
    """Generate a unique referral code not present in users collection."""
    from services.mongodb_service import mongodb_service
    users = mongodb_service.get_collection("users")
    for _ in range(20):
        code = _generate_referral_code(8)
        if not users.find_one({"referral_code": code}):
            return code
    # As a last resort, add entropy
    return _generate_referral_code(10)

@router.post("/register", response_model=AuthResponse)
async def register_user(request: UserRegistrationRequest):
    """
    Register a new user.
    
    Creates a new user account and initializes with 100 credits.
    """
    try:
        if not mongodb_service.is_connected():
            raise HTTPException(status_code=503, detail="Database not available")
        
        users_collection = mongodb_service.get_collection("users")
        
        # Check if user already exists
        existing_user = users_collection.find_one({"email": request.email})
        if existing_user:
            raise HTTPException(
                status_code=400,
                detail="User with this email already exists"
            )
        
        # Create new user
        user_id = str(secrets.token_hex(16))
        hashed_password = hash_password(request.password)
        
        user_doc = {
            "user_id": user_id,
            "email": request.email,
            "password": hashed_password,
            "name": request.name or request.email.split("@")[0],
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "is_active": True,
            "last_login": None
        }
        
        # Insert user
        users_collection.insert_one(user_doc)
        
        # Initialize user credits (100 credits)
        credits_result = await user_credits_service.initialize_user_credits(user_id, 100)
        
        if not credits_result["success"]:
            logger.error(f"Failed to initialize credits for user {user_id}: {credits_result['error']}")
        
        # Create JWT tokens
        token = create_jwt_token(user_id, request.email)
        refresh_token = create_refresh_token(user_id, request.email)
        
        logger.info(f"User registered successfully: {request.email}")
        
        return AuthResponse(
            success=True,
            message="User registered successfully",
            user_id=user_id,
            email=request.email,
            name=user_doc["name"],
            credits=100,
            token=token,
            refresh_token=refresh_token,
            expires_at=(datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Registration failed: {str(e)}"
        )

@router.post("/create-entity", response_model=AuthResponse)
async def create_entity_compat(request: UserRegistrationRequest):
    """Compat alias for legacy /auth/create-entity -> uses same register flow."""
    return await register_user(request)

@router.post("/login", response_model=AuthResponse)
async def login_user(request: UserLoginRequest):
    """
    Login user and add 100 credits.
    
    Authenticates user and adds 100 credits on each login.
    """
    try:
        if not mongodb_service.is_connected():
            raise HTTPException(status_code=503, detail="Database not available")
        
        users_collection = mongodb_service.get_collection("users")
        
        # Find user
        user = users_collection.find_one({"email": request.email})
        if not user:
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password"
            )
        
        # Verify password
        if not verify_password(request.password, user["password"]):
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password"
            )
        
        # Check if user is active
        if not user.get("is_active", True):
            raise HTTPException(
                status_code=403,
                detail="Account is deactivated"
            )
        
        # Update last login
        users_collection.update_one(
            {"user_id": user["user_id"]},
            {"$set": {"last_login": datetime.now(timezone.utc)}}
        )
        
        # Check if this is first login and add 100 credits only once
        credits_info = await user_credits_service.get_user_credits(user["user_id"])
        credits_added = False
        
        if credits_info["success"]:
            # Check if user has any credit history (indicating they've logged in before)
            credit_history = await user_credits_service.get_credit_history(user["user_id"], limit=1)
            if credit_history["success"] and len(credit_history["history"]) == 1:
                # Only one entry means this is first login (initial bonus)
                credits_added = True
                logger.info(f"First login detected for user {user['user_id']} - credits already given")
            elif not credit_history["success"] or len(credit_history["history"]) == 0:
                # No history means first time - add credits
                credits_result = await user_credits_service.add_credits(
                    user["user_id"], 
                    100, 
                    "First login bonus - 100 credits"
                )
                credits_added = True
                if not credits_result["success"]:
                    logger.error(f"Failed to add first login credits for user {user['user_id']}: {credits_result['error']}")
        else:
            # User doesn't have credits yet - initialize with 100
            credits_result = await user_credits_service.initialize_user_credits(user["user_id"], 100)
            credits_added = True
            if not credits_result["success"]:
                logger.error(f"Failed to initialize credits for user {user['user_id']}: {credits_result['error']}")
        
        if not credits_added:
            logger.info(f"User {user['user_id']} has already received login bonus - no credits added")
        
        # Get current credits
        current_credits = await user_credits_service.get_user_credits(user["user_id"])
        credits_balance = current_credits.get("credits", 0) if current_credits["success"] else 0
        
        # Create JWT tokens
        token = create_jwt_token(user["user_id"], user["email"])
        refresh_token = create_refresh_token(user["user_id"], user["email"])
        
        logger.info(f"User logged in successfully: {request.email}, Credits: {credits_balance}")
        
        return AuthResponse(
            success=True,
            message="Login successful",
            user_id=user["user_id"],
            email=user["email"],
            name=user["name"],
            credits=credits_balance,
            token=token,
            refresh_token=refresh_token,
            expires_at=(datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Login failed: {str(e)}"
        )

@router.get("/profile", response_model=UserProfileResponse)
async def get_user_profile(current_user: dict = Depends(get_current_user)):
    """
    Get user profile with credits information.
    """
    try:
        if not mongodb_service.is_connected():
            raise HTTPException(status_code=503, detail="Database not available")

        users_collection = mongodb_service.get_collection("users")
        # Robustly resolve user_id from JWT payload
        user_id = (
            current_user.get("user_id")
            or current_user.get("id")
            or current_user.get("sub")
            or current_user.get("entity_id")
        )
        
        # Get user info
        user = users_collection.find_one({"user_id": user_id})
        if not user:
            # Try alternative lookups
            user = users_collection.find_one({"_id": user_id})
        if not user:
            user = users_collection.find_one({"email": current_user.get("email")})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Ensure referral code exists for this user
        referral_code = user.get("referral_code")
        if not referral_code:
            referral_code = _ensure_unique_referral_code()
            users_collection.update_one(
                {"user_id": user_id},
                {"$set": {"referral_code": referral_code, "updated_at": datetime.now(timezone.utc)}}
            )
            user["referral_code"] = referral_code

        # Get credits info
        try:
            credits_info = await user_credits_service.get_user_credits(user_id)
        except Exception as e:
            logger.error(f"Credits service error: {e}")
            credits_info = {"success": False, "credits": 0, "total_earned": 0, "total_spent": 0}
        
        # Calculate days active
        created_dt = user.get("created_at")
        if created_dt:
            # Handle both timezone-aware and naive datetimes
            if hasattr(created_dt, 'tzinfo') and created_dt.tzinfo is not None:
                # Timezone-aware datetime
                created_dt = created_dt
            else:
                # Naive datetime, assume UTC
                created_dt = created_dt.replace(tzinfo=timezone.utc)
        else:
            created_dt = datetime.now(timezone.utc)
        
        days_active = max(0, (datetime.now(timezone.utc) - created_dt).days)

        return UserProfileResponse(
            success=True,
            user_id=user.get("user_id", "unknown"),
            email=user.get("email", "unknown"),
            name=user.get("name", "unknown"),
            credits=credits_info.get("credits", 0) if credits_info.get("success") else 0,
            total_earned=credits_info.get("total_earned", 0) if credits_info.get("success") else 0,
            total_spent=credits_info.get("total_spent", 0) if credits_info.get("success") else 0,
            created_at=created_dt.isoformat(),
            updated_at=user.get("updated_at").isoformat() if user.get("updated_at") else created_dt.isoformat(),
            account_type="user",
            status="Active" if user.get("is_active", True) else "Inactive",
            email_verified=bool(user.get("is_verified", False)),
            days_active=days_active,
            referral_code=referral_code,
            last_login=user.get("last_login").isoformat() if user.get("last_login") and hasattr(user.get("last_login"), 'isoformat') else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Profile error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get profile: {str(e)}"
        )

@router.get("/referral-code")
async def get_or_create_referral_code(current_user: dict = Depends(get_current_user)):
    """Return the current user's referral code, creating and saving one if missing."""
    try:
        if not mongodb_service.is_connected():
            raise HTTPException(status_code=503, detail="Database not available")

        users = mongodb_service.get_collection("users")
        user_id = current_user.get("user_id") or current_user.get("id")
        if not user_id:
            raise HTTPException(status_code=400, detail="Invalid user context")

        user = users.find_one({"user_id": user_id})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        code = user.get("referral_code")
        if not code:
            code = _ensure_unique_referral_code()
            users.update_one({"user_id": user_id}, {"$set": {"referral_code": code}})

        return {"success": True, "referral_code": code}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Referral code error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get referral code: {str(e)}")

@router.post("/referral/backfill")
async def backfill_referral_codes(current_user: dict = Depends(get_current_user)):
    """Admin-only: generate referral codes for all users missing one."""
    try:
        if not mongodb_service.is_connected():
            raise HTTPException(status_code=503, detail="Database not available")

        # Simple guard: require explicit env flag to run backfill
        if os.getenv("REFERRAL_BACKFILL_ALLOWED", "false").lower() != "true":
            raise HTTPException(status_code=403, detail="Backfill not permitted")

        users = mongodb_service.get_collection("users")
        missing_cursor = users.find({"$or": [{"referral_code": {"$exists": False}}, {"referral_code": None}]})
        count = 0
        for u in missing_cursor:
            code = _ensure_unique_referral_code()
            users.update_one({"_id": u["_id"]}, {"$set": {"referral_code": code}})
            count += 1

        return {"success": True, "updated": count}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Referral backfill error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to backfill referral codes: {str(e)}")

@router.post("/admin/reset-password")
async def admin_reset_password(
    email: str = Body(..., description="User email"),
    new_password: str = Body(..., description="New password")
):
    """Admin function to reset user password."""
    try:
        if not mongodb_service.is_connected():
            raise HTTPException(status_code=503, detail="Database not available")
        
        # Find user by email
        users = mongodb_service.get_collection("users")
        user = users.find_one({"email": email})
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Hash the new password
        hashed_password = hash_password(new_password)
        
        # Update password
        result = users.update_one(
            {"email": email},
            {
                "$set": {
                    "password": hashed_password,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=400, detail="Failed to update password")
        
        logger.info(f"Password reset for user: {email}")
        
        return {
            "success": True,
            "message": "Password reset successfully",
            "email": email
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password reset error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to reset password: {str(e)}")

@router.get("/credits")
async def get_user_credits(current_user: dict = Depends(get_current_user)):
    """
    Get user's current credits.
    """
    try:
        user_id = current_user.get("id")
        credits_info = await user_credits_service.get_user_credits(user_id)
        
        if not credits_info["success"]:
            raise HTTPException(status_code=500, detail=credits_info["error"])
        
        return credits_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Credits error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get credits: {str(e)}"
        )

@router.get("/credits/history")
async def get_credit_history(
    current_user: dict = Depends(get_current_user),
    limit: int = 50
):
    """
    Get user's credit history.
    """
    try:
        user_id = current_user.get("id")
        history = await user_credits_service.get_credit_history(user_id, limit)
        
        if not history["success"]:
            raise HTTPException(status_code=500, detail=history["error"])
        
        return history
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Credit history error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get credit history: {str(e)}"
        )

