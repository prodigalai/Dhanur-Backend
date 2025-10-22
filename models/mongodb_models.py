#!/usr/bin/env python3
"""
MongoDB Models for Content Crew Prodigal
Comprehensive data models for all collections
"""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from bson import ObjectId
import json

class UserModel(BaseModel):
    """User model for MongoDB."""
    user_id: str
    email: str
    password: str
    name: str
    is_active: bool = True
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None
    profile_picture: Optional[str] = None
    phone: Optional[str] = None
    country: Optional[str] = None
    timezone: Optional[str] = None

class UserCreditsModel(BaseModel):
    """User credits model for MongoDB."""
    user_id: str
    credits: int
    total_earned: int
    total_spent: int
    created_at: datetime
    updated_at: datetime
    credit_history: List[Dict[str, Any]]

class AudioFileModel(BaseModel):
    """Audio file model for MongoDB."""
    user_id: str
    audio_url: str
    text: str
    text_length: int
    language: str
    gender: str
    model_used: str
    processing_time: float
    status: str
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any]

class OrganizationModel(BaseModel):
    """Organization model for MongoDB."""
    org_id: str
    name: str
    description: Optional[str] = None
    owner_id: str
    members: List[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime
    is_active: bool = True
    settings: Dict[str, Any] = {}

class ProjectModel(BaseModel):
    """Project model for MongoDB."""
    project_id: str
    name: str
    description: Optional[str] = None
    org_id: str
    owner_id: str
    members: List[Dict[str, Any]]
    status: str = "active"
    created_at: datetime
    updated_at: datetime
    deadline: Optional[datetime] = None
    tags: List[str] = []

class BrandModel(BaseModel):
    """Brand model for MongoDB."""
    brand_id: str
    name: str
    description: Optional[str] = None
    org_id: str
    owner_id: str
    members: List[Dict[str, Any]]
    logo_url: Optional[str] = None
    website: Optional[str] = None
    social_links: Dict[str, str] = {}
    created_at: datetime
    updated_at: datetime
    is_active: bool = True

class ScheduledPostModel(BaseModel):
    """Scheduled post model for MongoDB."""
    post_id: str
    user_id: str
    platform: str  # linkedin, youtube, twitter, etc.
    content: str
    media_urls: List[str] = []
    scheduled_time: datetime
    status: str = "scheduled"  # scheduled, posted, failed, cancelled
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any] = {}

class OAuthAccountModel(BaseModel):
    """OAuth account model for MongoDB."""
    oauth_id: str
    user_id: str
    platform: str  # spotify, linkedin, youtube, etc.
    access_token: str
    refresh_token: Optional[str] = None
    token_expires_at: Optional[datetime] = None
    scope: List[str] = []
    platform_user_id: str
    platform_username: str
    created_at: datetime
    updated_at: datetime
    is_active: bool = True

class APIModel(BaseModel):
    """API key model for MongoDB."""
    api_key_id: str
    user_id: str
    name: str
    key_hash: str
    permissions: List[str] = []
    usage_count: int = 0
    last_used: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    is_active: bool = True

class NotificationModel(BaseModel):
    """Notification model for MongoDB."""
    notification_id: str
    user_id: str
    title: str
    message: str
    type: str  # info, warning, error, success
    is_read: bool = False
    action_url: Optional[str] = None
    created_at: datetime
    metadata: Dict[str, Any] = {}

class AnalyticsModel(BaseModel):
    """Analytics model for MongoDB."""
    analytics_id: str
    user_id: str
    metric_type: str  # tts_usage, audio_generation, credits_spent, etc.
    metric_value: float
    metadata: Dict[str, Any] = {}
    timestamp: datetime
    date: str  # YYYY-MM-DD for easy querying

class AudioCampaignAssignmentModel(BaseModel):
    """Audio-Campaign assignment model for MongoDB."""
    assignment_id: str
    audio_id: str
    campaign_id: str
    brand_id: str
    user_id: str
    assigned_by: str
    assigned_at: datetime
    status: str = "active"  # active, inactive, removed
    notes: Optional[str] = None
    metadata: Dict[str, Any] = {}

class SystemLogModel(BaseModel):
    """System log model for MongoDB."""
    log_id: str
    level: str  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    message: str
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    endpoint: Optional[str] = None
    method: Optional[str] = None
    status_code: Optional[int] = None
    response_time: Optional[float] = None
    created_at: datetime
    metadata: Dict[str, Any] = {}

# Collection schemas for MongoDB
COLLECTION_SCHEMAS = {
    "users": {
        "indexes": [
            {"email": 1},
            {"user_id": 1},
            {"created_at": 1},
            {"is_active": 1}
        ],
        "validation": {
            "required_fields": ["user_id", "email", "password", "name"],
            "unique_fields": ["email", "user_id"]
        }
    },
    "user_credits": {
        "indexes": [
            {"user_id": 1},
            {"created_at": 1},
            {"updated_at": 1}
        ],
        "validation": {
            "required_fields": ["user_id", "credits", "total_earned", "total_spent"],
            "unique_fields": ["user_id"]
        }
    },
    "audio_files": {
        "indexes": [
            {"user_id": 1},
            {"created_at": 1},
            {"language": 1},
            {"status": 1},
            {"text_length": 1}
        ],
        "validation": {
            "required_fields": ["user_id", "audio_url", "text", "language"],
            "unique_fields": []
        }
    },
    "organizations": {
        "indexes": [
            {"org_id": 1},
            {"owner_id": 1},
            {"created_at": 1},
            {"is_active": 1}
        ],
        "validation": {
            "required_fields": ["org_id", "name", "owner_id"],
            "unique_fields": ["org_id"]
        }
    },
    "projects": {
        "indexes": [
            {"project_id": 1},
            {"org_id": 1},
            {"owner_id": 1},
            {"status": 1},
            {"created_at": 1}
        ],
        "validation": {
            "required_fields": ["project_id", "name", "org_id", "owner_id"],
            "unique_fields": ["project_id"]
        }
    },
    "brands": {
        "indexes": [
            {"brand_id": 1},
            {"org_id": 1},
            {"owner_id": 1},
            {"created_at": 1},
            {"is_active": 1}
        ],
        "validation": {
            "required_fields": ["brand_id", "name", "org_id", "owner_id"],
            "unique_fields": ["brand_id"]
        }
    },
    "scheduled_posts": {
        "indexes": [
            {"post_id": 1},
            {"user_id": 1},
            {"platform": 1},
            {"scheduled_time": 1},
            {"status": 1}
        ],
        "validation": {
            "required_fields": ["post_id", "user_id", "platform", "content", "scheduled_time"],
            "unique_fields": ["post_id"]
        }
    },
    "oauth_accounts": {
        "indexes": [
            {"oauth_id": 1},
            {"user_id": 1},
            {"platform": 1},
            {"platform_user_id": 1},
            {"is_active": 1}
        ],
        "validation": {
            "required_fields": ["oauth_id", "user_id", "platform", "access_token"],
            "unique_fields": ["oauth_id"]
        }
    },
    "api_keys": {
        "indexes": [
            {"api_key_id": 1},
            {"user_id": 1},
            {"key_hash": 1},
            {"created_at": 1},
            {"is_active": 1}
        ],
        "validation": {
            "required_fields": ["api_key_id", "user_id", "name", "key_hash"],
            "unique_fields": ["api_key_id", "key_hash"]
        }
    },
    "notifications": {
        "indexes": [
            {"notification_id": 1},
            {"user_id": 1},
            {"is_read": 1},
            {"created_at": 1},
            {"type": 1}
        ],
        "validation": {
            "required_fields": ["notification_id", "user_id", "title", "message"],
            "unique_fields": ["notification_id"]
        }
    },
    "analytics": {
        "indexes": [
            {"analytics_id": 1},
            {"user_id": 1},
            {"metric_type": 1},
            {"timestamp": 1},
            {"date": 1}
        ],
        "validation": {
            "required_fields": ["analytics_id", "user_id", "metric_type", "metric_value"],
            "unique_fields": ["analytics_id"]
        }
    },
    "system_logs": {
        "indexes": [
            {"log_id": 1},
            {"level": 1},
            {"user_id": 1},
            {"created_at": 1},
            {"endpoint": 1}
        ],
        "validation": {
            "required_fields": ["log_id", "level", "message"],
            "unique_fields": ["log_id"]
        }
    },
    "audio_campaign_assignments": {
        "indexes": [
            {"assignment_id": 1},
            {"audio_id": 1},
            {"campaign_id": 1},
            {"brand_id": 1},
            {"user_id": 1},
            {"assigned_at": 1},
            {"status": 1}
        ],
        "validation": {
            "required_fields": ["assignment_id", "audio_id", "campaign_id", "brand_id", "user_id", "assigned_by"],
            "unique_fields": ["assignment_id"]
        }
    }
}

def get_collection_schema(collection_name: str) -> Dict[str, Any]:
    """Get schema for a specific collection."""
    return COLLECTION_SCHEMAS.get(collection_name, {})

def get_all_collection_names() -> List[str]:
    """Get all collection names."""
    return list(COLLECTION_SCHEMAS.keys())



