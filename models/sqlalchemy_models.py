#!/usr/bin/env python3
"""
SQLAlchemy models for Content Crew Prodigal
"""

import uuid
from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, ForeignKey, DECIMAL, Date, JSON
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy import func, text
from datetime import datetime

Base = declarative_base()

def generate_uuid():
    """Generate a UUID for ID fields."""
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"
    
    # Updated to match your actual database structure
    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), nullable=True)  # Made nullable to match your DB
    full_name = Column(String(255))  # Changed from 'name' to 'full_name'
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    first_name = Column(String(100))
    last_name = Column(String(100))
    password_hash = Column(String(255))
    phone = Column(String(20))
    company = Column(String(255))
    avatar_url = Column(String(500))
    mime_type = Column(String(100))
    entity_type = Column(String(50), default='user')
    invitation_token = Column(String(255))
    referral_code = Column(String(100))
    verification_token = Column(String(255))
    reset_token = Column(String(255))
    reset_token_expires = Column(DateTime)
    organization_memberships = Column(Text)
    prodigal_credits = Column(Integer, default=0)
    dhanur_credits = Column(Integer, default=0)
    
    # Relationships
    user_credits = relationship("UserCredits", back_populates="user", uselist=False)

class UserCredits(Base):
    __tablename__ = "user_credits"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)  # Changed to String
    credits = Column(Integer, nullable=False, server_default=text("100"))
    used_credits = Column(Integer, nullable=False, server_default=text("0"))
    credit_type = Column(String(50), nullable=False, server_default=text("'basic'"))
    expires_at = Column(TIMESTAMP(timezone=True))
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="user_credits")

class Organization(Base):
    __tablename__ = "organizations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    logo_url = Column(Text)
    website_url = Column(Text)
    industry = Column(String(100))
    owner_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)  # Changed to String
    is_active = Column(Boolean, nullable=False, server_default=text("true"))
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

class OrganizationMember(Base):
    __tablename__ = "organization_members"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)  # Changed to String
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(50), nullable=False, server_default=text("'member'"))
    permissions = Column(JSON, server_default=text("'{}'"))
    is_active = Column(Boolean, nullable=False, server_default=text("true"))
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

# Additional models can be added here as needed

class OAuthAccount(Base):
    __tablename__ = "oauth_accounts"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)  # Changed from UUID to String(36)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    provider = Column(String(50), nullable=False, index=True)  # spotify, linkedin, youtube, etc.
    provider_user_id = Column(String(255), nullable=False, index=True)
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text)
    expires_at = Column(DateTime)  # Changed from TIMESTAMP to DateTime for consistency
    scope = Column(String(500))
    profile_data = Column(JSON, server_default=text("'{}'"))
    is_active = Column(Boolean, nullable=False, server_default=text("true"))
    created_at = Column(DateTime, default=datetime.utcnow)  # Changed from TIMESTAMP to DateTime
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # Changed from TIMESTAMP to DateTime
    
    # Relationships
    user = relationship("User", backref="oauth_accounts")
