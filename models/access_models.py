from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

from enums.role_type import RoleType

Base = declarative_base()

class Permission(Base):
    """Permission model for access control."""
    __tablename__ = "permissions"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)
    description = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Team(Base):
    """Team model for grouping users."""
    __tablename__ = "teams"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    organization_id = Column(Integer, ForeignKey("prodigal_entities.id"), nullable=False, index=True)
    owner_id = Column(Integer, ForeignKey("prodigal_entities.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Create composite unique index for organization_id and name
    __table_args__ = (
        Index('idx_org_team_name', 'organization_id', 'name', unique=True),
    )

class UserTeam(Base):
    """User team membership model."""
    __tablename__ = "user_teams"
    
    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("prodigal_entities.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class TeamPermission(Base):
    """Team permission model."""
    __tablename__ = "team_permissions"
    
    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False, index=True)
    permission_id = Column(Integer, ForeignKey("permissions.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class UserPermission(Base):
    """User permission model."""
    __tablename__ = "user_permissions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("prodigal_entities.id"), nullable=False, index=True)
    permission_id = Column(Integer, ForeignKey("permissions.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class EmailInvitation(Base):
    """Email invitation model."""
    __tablename__ = "email_invitations"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, nullable=False, index=True)
    token = Column(String, unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("prodigal_entities.id"), nullable=False, index=True)
    created_by = Column(Integer, ForeignKey("prodigal_entities.id"), nullable=False)
    role = Column(String(20), nullable=False)  # "admin", "member", etc.
    created_at = Column(DateTime, default=datetime.utcnow)
    used = Column(Boolean, default=False, index=True)
    used_at = Column(DateTime)
    
    # Create composite index for email and organization_id
    __table_args__ = (
        Index('idx_email_org_invitation', 'email', 'organization_id'),
    )

class UserOrganizationRole(Base):
    """User organization role model."""
    __tablename__ = "user_organization_roles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("prodigal_entities.id"), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("prodigal_entities.id"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # "admin", "member", etc.
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Create composite unique index for user_id and organization_id
    __table_args__ = (
        Index('idx_user_org_role', 'user_id', 'organization_id', unique=True),
    )

class BrandPermissions(Base):
    """Brand permissions model."""
    __tablename__ = "brand_permissions"
    
    id = Column(Integer, primary_key=True, index=True)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=False, index=True)
    entity_id = Column(Integer, ForeignKey("prodigal_entities.id"), nullable=False, index=True)
    
    # Member level permissions
    view = Column(Boolean, default=False)
    view_resources = Column(Boolean, default=False)
    view_projects = Column(Boolean, default=False)
    add_resources = Column(Boolean, default=False)
    comment = Column(Boolean, default=False)
    
    # Manager level permissions
    create_project = Column(Boolean, default=False)
    edit_project = Column(Boolean, default=False)
    update_resource = Column(Boolean, default=False)
    delete_resources = Column(Boolean, default=False)
    update_brand = Column(Boolean, default=False)
    add_people = Column(Boolean, default=False)
    
    # Admin level permissions
    delete_project = Column(Boolean, default=False)
    delete_brand = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Create composite unique index for brand_id and entity_id
    __table_args__ = (
        Index('idx_brand_entity_permissions', 'brand_id', 'entity_id', unique=True),
    )
