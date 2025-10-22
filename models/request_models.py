#!/usr/bin/env python3
"""
Request models for Content Crew Prodigal API
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, Any

# =====================================================
# AUTHENTICATION REQUEST MODELS
# =====================================================

class UserRegistrationRequest(BaseModel):
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password (min 8 characters)")
    full_name: str = Field(..., min_length=2, max_length=100, description="User full name")
    organization_name: str = Field(..., min_length=2, max_length=100, description="Organization name")

class UserLoginRequest(BaseModel):
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")

class TokenRefreshRequest(BaseModel):
    refresh_token: str = Field(..., description="Refresh token for getting new access token")

class ProfileUpdateRequest(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=100, description="User full name")
    profile_picture: Optional[str] = Field(None, description="URL to profile picture")
    phone: Optional[str] = Field(None, max_length=20, description="Phone number")
    timezone: Optional[str] = Field(None, max_length=50, description="User timezone")

# =====================================================
# RESPONSE MODELS
# =====================================================

class UserProfileResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str]
    is_verified: bool
    is_active: bool
    profile_picture: Optional[str]
    phone: Optional[str]
    timezone: Optional[str]
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class AuthResponse(BaseModel):
    success: bool
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    message: str
    user: UserProfileResponse

class HealthResponse(BaseModel):
    status: str
    message: str
    timestamp: str

class DatabaseHealthResponse(BaseModel):
    status: str
    message: str
    timestamp: str
    version: Optional[str] = None
    host: Optional[str] = None
    port: Optional[str] = None
    database: Optional[str] = None
