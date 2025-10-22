from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from bson import ObjectId

class MediaItem(BaseModel):
    """Media item model for MongoDB."""
    file_name: str = Field(..., alias="fileName")
    file_data: str = Field(..., alias="fileData")
    
    class Config:
        allow_population_by_field_name = True

class Post(BaseModel):
    """Post model for MongoDB."""
    id: Optional[ObjectId] = Field(None, alias="_id")
    entity_id: Optional[ObjectId] = Field(None, alias="entity_id")
    sql_entity_id: int = Field(..., alias="sql_entity_id")
    title: str
    content: str
    scheduled_for: Optional[datetime] = Field(None, alias="scheduled_for")
    published: bool = False
    media: Optional[List[MediaItem]] = None
    meta: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow, alias="created_at")
    updated_at: datetime = Field(default_factory=datetime.utcnow, alias="updated_at")
    
    class Config:
        allow_population_by_field_name = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: v.isoformat()
        }

class PostCreate(BaseModel):
    """Model for creating a new post."""
    entity_id: Optional[ObjectId] = None
    sql_entity_id: int
    title: str
    content: str
    scheduled_for: Optional[datetime] = None
    published: bool = False
    media: Optional[List[MediaItem]] = None
    meta: Optional[Dict[str, Any]] = None

class PostUpdate(BaseModel):
    """Model for updating an existing post."""
    title: Optional[str] = None
    content: Optional[str] = None
    scheduled_for: Optional[datetime] = None
    published: Optional[bool] = None
    media: Optional[List[MediaItem]] = None
    meta: Optional[Dict[str, Any]] = None
