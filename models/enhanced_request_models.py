#!/usr/bin/env python3
"""
Enhanced Request Models for Content Crew Prodigal OAuth System
Production-ready models with comprehensive validation
"""

from pydantic import BaseModel, EmailStr, validator, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

# =====================================================
# OAUTH REQUEST MODELS
# =====================================================

class OAuthCreateAccountRequest(BaseModel):
    """Request model for initiating OAuth flow with account creation."""
    email: EmailStr = Field(..., description="User email address")
    user_id: Optional[str] = Field(None, description="Existing user ID (if linking to existing account)")
    create_account: bool = Field(True, description="Whether to create a new user account")
    
    @validator('email')
    def validate_email(cls, v):
        if not v or not v.strip():
            raise ValueError('Email cannot be empty')
        return v.lower().strip()

class OAuthLinkRequest(BaseModel):
    """Request model for linking OAuth account to existing user."""
    user_id: str = Field(..., description="User ID to link OAuth account to")
    oauth_provider: str = Field(..., description="OAuth provider (e.g., 'spotify')")
    
    @validator('oauth_provider')
    def validate_provider(cls, v):
        allowed_providers = ['spotify', 'linkedin', 'youtube']
        if v.lower() not in allowed_providers:
            raise ValueError(f'Unsupported OAuth provider. Allowed: {", ".join(allowed_providers)}')
        return v.lower()

class OAuthRefreshRequest(BaseModel):
    """Request model for refreshing OAuth tokens."""
    oauth_account_id: str = Field(..., description="OAuth account ID to refresh tokens for")
    
    @validator('oauth_account_id')
    def validate_uuid(cls, v):
        if not v or len(v) != 36:
            raise ValueError('Invalid OAuth account ID format')
        return v

class OAuthDisconnectRequest(BaseModel):
    """Request model for disconnecting OAuth account."""
    oauth_account_id: str = Field(..., description="OAuth account ID to disconnect")
    
    @validator('oauth_account_id')
    def validate_uuid(cls, v):
        if not v or len(v) != 36:
            raise ValueError('Invalid OAuth account ID format')
        return v

# =====================================================
# USER MANAGEMENT REQUEST MODELS
# =====================================================

class EnhancedUserRegistrationRequest(BaseModel):
    """Enhanced user registration request with comprehensive validation."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, max_length=128, description="User password")
    full_name: str = Field(..., min_length=2, max_length=100, description="User full name")
    organization_name: Optional[str] = Field(None, min_length=2, max_length=100, description="Organization name")
    phone: Optional[str] = Field(None, max_length=20, description="Phone number")
    timezone: str = Field("UTC", max_length=50, description="User timezone")
    
    @validator('password')
    def validate_password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v
    
    @validator('phone')
    def validate_phone(cls, v):
        if v and not v.replace('+', '').replace('-', '').replace(' ', '').replace('(', '').replace(')', '').isdigit():
            raise ValueError('Invalid phone number format')
        return v

class EnhancedUserLoginRequest(BaseModel):
    """Enhanced user login request."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")
    
    @validator('email')
    def validate_email(cls, v):
        if not v or not v.strip():
            raise ValueError('Email cannot be empty')
        return v.lower().strip()

class UserProfileUpdateRequest(BaseModel):
    """Request model for updating user profile."""
    full_name: Optional[str] = Field(None, min_length=2, max_length=100, description="User full name")
    profile_picture: Optional[str] = Field(None, description="URL to profile picture")
    phone: Optional[str] = Field(None, max_length=20, description="Phone number")
    timezone: Optional[str] = Field(None, max_length=50, description="User timezone")
    organization_name: Optional[str] = Field(None, min_length=2, max_length=100, description="Organization name")

class PasswordChangeRequest(BaseModel):
    """Request model for changing user password."""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, max_length=128, description="New password")
    
    @validator('new_password')
    def validate_new_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v

# =====================================================
# RESPONSE MODELS
# =====================================================

class OAuthAccountInfo(BaseModel):
    """OAuth account information."""
    id: str
    provider: str
    provider_user_id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_token_refresh: Optional[datetime] = None
    token_refresh_count: int = 0

class UserProfileResponse(BaseModel):
    """Enhanced user profile response."""
    id: str
    email: str
    name: str
    is_verified: bool
    is_active: bool
    profile_picture: Optional[str]
    phone: Optional[str]
    timezone: str
    organization_name: Optional[str]
    created_at: datetime
    updated_at: datetime
    oauth_accounts: List[OAuthAccountInfo] = []

class OAuthFlowResponse(BaseModel):
    """Response for OAuth flow initiation."""
    success: bool
    authorization_url: str
    state: str
    flow_metadata: Dict[str, Any]
    message: str

class OAuthCallbackResponse(BaseModel):
    """Response for OAuth callback completion."""
    success: bool
    message: str
    user: Optional[UserProfileResponse]
    oauth_account: Optional[OAuthAccountInfo]
    profile: Optional[Dict[str, Any]]
    tokens: Optional[Dict[str, Any]]
    flow_metadata: Optional[Dict[str, Any]]

class AuthResponse(BaseModel):
    """Authentication response."""
    success: bool
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    message: str
    user: UserProfileResponse

class HealthCheckResponse(BaseModel):
    """Health check response."""
    status: str
    message: str
    timestamp: str
    version: Optional[str] = Field(None, description="Service version")
    uptime: Optional[float] = Field(None, description="Service uptime in seconds")
