from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid

Base = declarative_base()

class APIKey(Base):
    """API key model for authentication."""
    __tablename__ = "api_keys"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(Integer, ForeignKey("prodigal_entities.id"), nullable=False, index=True)
    created_by_user_id = Column(Integer, ForeignKey("prodigal_entities.id"), nullable=False, index=True)
    name = Column(String)
    key_hash = Column(String, unique=True, nullable=False, index=True)
    allowed_methods = Column(JSONB)  # e.g. ["GET", "POST"]
    usage_limit = Column(Integer)
    usage_count = Column(Integer, default=0)
    expires_at = Column(DateTime)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class APIRouteRegistry(Base):
    """API route registry model."""
    __tablename__ = "api_route_registries"
    
    id = Column(Integer, primary_key=True, index=True)
    path = Column(String, nullable=False)
    method = Column(String(10), nullable=False)
    description = Column(String)
    
    # Create composite unique index for path and method
    __table_args__ = (
        Index('idx_path_method', 'path', 'method', unique=True),
    )

class APIKeyRoute(Base):
    """API key route join table."""
    __tablename__ = "api_key_routes"
    
    api_key_id = Column(UUID(as_uuid=True), ForeignKey("api_keys.id"), primary_key=True)
    route_id = Column(Integer, ForeignKey("api_route_registries.id"), primary_key=True, index=True)
