from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, Text, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Mapped
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid

from enums.entity_type import EntityType
from enums.payment_status import PaymentStatus
from enums.project_status import ProjectStatus
from enums.role_type import RoleType

Base = declarative_base()

class ProdigalEntity(Base):
    """Prodigal entity model (user or organization)."""
    __tablename__ = "prodigal_entities"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    name = Column(String)
    entity_type = Column(String(20), nullable=False)  # "user" or "organization"
    avatar_link = Column(String)
    is_active = Column(Boolean, default=True)
    is_email_verified = Column(Boolean, default=False)
    email_verification_token = Column(String)
    email_verification_token_expiry = Column(DateTime)
    reset_token = Column(String)
    reset_token_expiry = Column(DateTime)
    referral_token = Column(String)
    prodigal_credits = Column(Integer, default=0)
    dhanur_credits = Column(Integer, default=0)
    meta = Column(JSONB)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    payment_histories: Mapped[List["PaymentHistory"]] = relationship("PaymentHistory", back_populates="entity")

class Brand(Base):
    """Brand model."""
    __tablename__ = "brands"
    
    id = Column(Integer, primary_key=True, index=True)
    entity_id = Column(Integer, ForeignKey("prodigal_entities.id"), index=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    identifier = Column(String, unique=True, index=True)
    cover_resource_url = Column(String)
    shareable_link = Column(String, unique=True, index=True)
    deleted_status = Column(Boolean, default=False)
    can_view = Column(Boolean, default=False)
    can_comment = Column(Boolean, default=False)
    can_edit = Column(Boolean, default=False)
    meta = Column(JSONB)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Project(Base):
    """Project model."""
    __tablename__ = "projects"
    
    id = Column(Integer, primary_key=True, index=True)
    brand_id = Column(Integer, ForeignKey("brands.id"), index=True)
    name = Column(String, nullable=False)
    status = Column(String(20), default="ongoing")
    meta = Column(JSONB)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Resource(Base):
    """Resource model."""
    __tablename__ = "resources"
    
    id = Column(Integer, primary_key=True, index=True)
    brand_id = Column(Integer, ForeignKey("brands.id"), index=True)
    file_url = Column(String)  # S3 URL
    meta = Column(JSONB)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class UserOrganizationRole(Base):
    """User organization role model."""
    __tablename__ = "user_organization_roles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("prodigal_entities.id"), index=True)
    organization_id = Column(Integer, ForeignKey("prodigal_entities.id"), index=True)
    role = Column(String(20), nullable=False)  # "admin", "member", etc.
    meta = Column(JSONB)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class EntityActivity(Base):
    """Entity activity model."""
    __tablename__ = "entity_activities"
    
    id = Column(Integer, primary_key=True, index=True)
    entity_id = Column(Integer, ForeignKey("prodigal_entities.id"), index=True, nullable=False)
    action = Column(String, nullable=False)
    meta = Column(JSONB)
    created_at = Column(DateTime, default=datetime.utcnow)

class EntityReferral(Base):
    """Entity referral model."""
    __tablename__ = "entity_referrals"
    
    id = Column(Integer, primary_key=True, index=True)
    referrer_id = Column(Integer, ForeignKey("prodigal_entities.id"), index=True, nullable=False)
    referred_id = Column(Integer, ForeignKey("prodigal_entities.id"), index=True)
    email = Column(String, nullable=False)
    meta = Column(JSONB)
    accepted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Invitation(Base):
    """Invitation model."""
    __tablename__ = "invitations"
    
    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("prodigal_entities.id"), index=True, nullable=False)
    receiver_email = Column(String, nullable=False)
    organization_id = Column(Integer, ForeignKey("prodigal_entities.id"), index=True, nullable=False)
    role = Column(String(20))
    token = Column(String, unique=True, index=True, nullable=False)
    accepted = Column(Boolean, default=False)
    meta = Column(JSONB)
    created_at = Column(DateTime, default=datetime.utcnow)
    accepted_at = Column(DateTime)
    purpose = Column(String)  # "invite" or "refer"

class BrandPermissions(Base):
    """Brand permissions model."""
    __tablename__ = "brand_permissions"
    
    id = Column(Integer, primary_key=True, index=True)
    brand_id = Column(Integer, ForeignKey("brands.id"), index=True)
    entity_id = Column(Integer, ForeignKey("prodigal_entities.id"), index=True)
    view = Column(Boolean, default=False)
    view_resources = Column(Boolean, default=False)
    view_projects = Column(Boolean, default=False)
    add_resources = Column(Boolean, default=False)
    comment = Column(Boolean, default=False)
    create_project = Column(Boolean, default=False)
    edit_project = Column(Boolean, default=False)
    update_resource = Column(Boolean, default=False)
    delete_resources = Column(Boolean, default=False)
    update_brand = Column(Boolean, default=False)
    add_people = Column(Boolean, default=False)
    meta = Column(JSONB)
    delete_project = Column(Boolean, default=False)
    delete_brand = Column(Boolean, default=False)

class Extension(Base):
    """Extension model."""
    __tablename__ = "extensions"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    meta = Column(JSONB)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

class EntityExtension(Base):
    """Entity extension model."""
    __tablename__ = "entity_extensions"
    
    id = Column(Integer, primary_key=True, index=True)
    extension_id = Column(Integer, ForeignKey("extensions.id"), nullable=False, index=True)
    entity_id = Column(Integer, ForeignKey("prodigal_entities.id"), nullable=False, index=True)
    entity_type = Column(String(10), nullable=False)
    access_token = Column(String(1000))
    refresh_token = Column(String(1000))
    token_expiry = Column(DateTime, index=True)
    person_urn = Column(String(1000))
    meta = Column(JSONB)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # YouTube-specific fields
    youtube_person_urn = Column(String(1000), default="")
    youtube_access_token = Column(String(1000), default="")
    youtube_refresh_token = Column(String(1000), default="")
    youtube_token_expiry = Column(DateTime, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class PaymentHistory(Base):
    """Payment history model."""
    __tablename__ = "payment_histories"
    
    id = Column(Integer, primary_key=True, index=True)
    payment_method = Column(String(100))
    payment_provider = Column(String(100))
    transaction_id = Column(String(255))
    money_credited = Column(Float, default=0)
    currency_code = Column(String(10), default="USD")
    payment_status = Column(String(20), default="PENDING")
    description = Column(Text)
    billing_address = Column(Text)
    ip_address = Column(String(45))
    meta = Column(JSONB)
    entity_id = Column(Integer, ForeignKey("prodigal_entities.id"), index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    entity: Mapped["ProdigalEntity"] = relationship("ProdigalEntity", back_populates="payment_histories")

class SavedMediaItem(Base):
    """Saved media item model."""
    __tablename__ = "saved_media_items"
    
    id = Column(Integer, primary_key=True, index=True)
    file_name = Column(String, nullable=False)
    file_data = Column(String, nullable=False)

class LinkedInPost(Base):
    """LinkedIn post model."""
    __tablename__ = "linkedin_posts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, index=True)
    entity_id = Column(Integer, ForeignKey("prodigal_entities.id"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    media_items = Column(JSONB)  # List of SavedMediaItem
    scheduled_for = Column(DateTime, index=True)
    published = Column(Boolean, default=False, index=True)
    meta = Column(JSONB)
    published_at = Column(DateTime, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class YouTubePost(Base):
    """YouTube post model."""
    __tablename__ = "youtube_posts"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, index=True)
    entity_id = Column(Integer, ForeignKey("prodigal_entities.id"), nullable=False, index=True)
    video_id = Column(String(64), unique=True, index=True, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text)
    tags = Column(JSONB)
    is_short = Column(Boolean, default=False)
    published_at = Column(DateTime, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ScheduledYoutubePost(Base):
    """Scheduled YouTube post model."""
    __tablename__ = "scheduled_youtube_posts"
    
    id = Column(Integer, primary_key=True)
    entity_id = Column(Integer, ForeignKey("prodigal_entities.id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    tags = Column(JSONB)
    is_short = Column(Boolean, default=False)
    privacy_status = Column(String(20), default="public")
    media_url = Column(String, nullable=False)
    scheduled_for = Column(DateTime, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
