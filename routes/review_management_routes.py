#!/usr/bin/env python3
"""
Review Management Routes for Content Crew Prodigal
Handles content review, comments, team collaboration, and analytics
"""

from fastapi import APIRouter, HTTPException, Depends, Request, Query, UploadFile, File, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
import logging
from datetime import datetime, timedelta

# Set up logger
logger = logging.getLogger(__name__)
import uuid
import os

from services.database_service import mongodb_service
from services.audio_storage_service import audio_storage_service
from services.user_credits_service import user_credits_service
from middleware.auth import get_current_user

def to_iso_format(dt):
    """Safely convert datetime to ISO format string."""
    if dt is None:
        return ""
    if hasattr(dt, 'isoformat'):
        return dt.isoformat()
    return str(dt)

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/reviews", tags=["Review Management"])

# Helpers
def to_iso(value):
    try:
        if isinstance(value, datetime):
            return value.isoformat()
        if value is None:
            return ""
        return str(value)
    except Exception:
        return ""

# Pydantic models for request/response
class BrandResponse(BaseModel):
    """Brand response model."""
    id: str
    name: str
    description: Optional[str] = None
    logo: Optional[str] = None
    createdAt: str

class CampaignResponse(BaseModel):
    """Campaign response model."""
    id: str
    name: str
    description: Optional[str] = None
    brandId: str
    status: str
    createdAt: str

class ContentResponse(BaseModel):
    """Content response model."""
    id: str
    title: str
    description: Optional[str] = None
    type: str
    url: str
    thumbnail: Optional[str] = None
    duration: Optional[str] = None
    status: str
    brandId: str
    campaignId: str
    uploadedBy: str
    uploadedAt: str
    version: str
    views: int = 0
    likes: int = 0
    comments: int = 0

class CommentRequest(BaseModel):
    """Comment request model."""
    content: str = Field(..., min_length=1, max_length=1000)
    timestamp: Optional[str] = None
    timeInSeconds: Optional[float] = None
    type: str = Field(default="feedback", description="Type: feedback, suggestion, question, praise")
    parentId: Optional[str] = None
    
    @validator('type')
    def validate_type(cls, v):
        allowed_types = ['feedback', 'suggestion', 'question', 'praise']
        if v not in allowed_types:
            raise ValueError(f'Type must be one of: {", ".join(allowed_types)}')
        return v
    # Timeline selection features
    startTime: Optional[float] = Field(None, description="Start time in seconds for timeline selection")
    endTime: Optional[float] = Field(None, description="End time in seconds for timeline selection")
    selectionType: Optional[str] = Field("text", description="Selection type: text, drag_drop, marker")
    markerPosition: Optional[float] = Field(None, description="Marker position in seconds")
    version: Optional[str] = Field(None, description="Content version for versioning")

class CommentResponse(BaseModel):
    """Comment response model."""
    id: str
    content: str
    timestamp: Optional[str] = None
    timeInSeconds: Optional[float] = None
    type: str
    parentId: Optional[str] = None
    authorId: str
    authorName: str
    authorAvatar: Optional[str] = None
    likes: int = 0
    resolved: bool = False
    createdAt: str
    updatedAt: str
    # Timeline selection features
    startTime: Optional[float] = None
    endTime: Optional[float] = None
    selectionType: Optional[str] = None
    markerPosition: Optional[float] = None
    version: Optional[str] = None

class StatusUpdateRequest(BaseModel):
    """Status update request model."""
    status: str = Field(..., description="Status: pending, approved, needs_revision, rejected")
    notes: Optional[str] = None

# Chat system removed as per requirements - using comments only

class NotificationResponse(BaseModel):
    """Notification response model."""
    id: str
    title: str
    message: str
    type: str
    contentId: Optional[str] = None
    isRead: bool = False
    createdAt: str

# ============================================================================
# BRAND & CAMPAIGN SELECTION APIs
# ============================================================================

@router.get("/brands", response_model=Dict[str, Any])
async def get_all_brands(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Get all brands for the current user."""
    try:
        # Fetch real brands from the system using direct database access
        from services.mongodb_service import mongodb_service
        
        user_id = current_user.get('user_id', current_user.get('id', 'unknown'))
        
        # Get brands from database
        brands_collection = mongodb_service.get_collection('brands')
        brands = list(brands_collection.find({
            "$or": [
                {"owner_id": user_id},
                {"team_members.user_id": user_id}
            ],
            "status": {"$ne": "deleted"}
        }))
        
        # Format brands for review system
        formatted_brands = []
        for brand in brands:
            formatted_brands.append({
                "id": brand.get("brand_id", ""),
                "name": brand.get("name", ""),
                "description": brand.get("description", ""),
                "logo": None,  # Add logo field if available
                "createdAt": to_iso(brand.get("created_at"))
            })
        
        return {
            "success": True,
            "data": {
                "brands": formatted_brands
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting brands: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get brands: {str(e)}")

@router.get("/brands/{brand_id}/campaigns", response_model=Dict[str, Any])
async def get_campaigns_by_brand(
    brand_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Get campaigns for a specific brand."""
    try:
        # Fetch real campaigns from the system using direct database access
        from services.mongodb_service import mongodb_service
        
        user_id = current_user.get('user_id', current_user.get('id', 'unknown'))
        
        # Check if user has access to this brand
        brands_collection = mongodb_service.get_collection('brands')
        brand = brands_collection.find_one({
            "brand_id": brand_id,
            "$or": [
                {"owner_id": user_id},
                {"team_members.user_id": user_id}
            ]
        })
        
        if not brand:
            raise HTTPException(status_code=403, detail="Insufficient permissions or brand not found")
        
        # Get campaigns from database
        campaigns_collection = mongodb_service.get_collection('campaigns')
        campaigns = list(campaigns_collection.find({
            "brand_id": brand_id,
            "status": {"$ne": "deleted"}
        }).sort("created_at", -1))
        
        # Format campaigns for review system
        formatted_campaigns = []
        for campaign in campaigns:
            formatted_campaigns.append({
                "id": campaign.get("campaign_id", ""),
                "name": campaign.get("name", ""),
                "description": campaign.get("description", ""),
                "brandId": brand_id,
                "status": campaign.get("status", "active"),
                "createdAt": to_iso(campaign.get("created_at"))
            })
        
        return {
            "success": True,
            "data": {
                "campaigns": formatted_campaigns
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting campaigns: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get campaigns: {str(e)}")

# ============================================================================
# CONTENT REVIEW APIs
# ============================================================================

@router.get("/content", response_model=Dict[str, Any])
async def get_content_for_review(
    brand_id: Optional[str] = Query(None, description="Filter by brand ID"),
    campaign_id: Optional[str] = Query(None, description="Filter by campaign ID"),
    content_type: Optional[str] = Query(None, description="Filter by content type (video/audio/content)"),
    status: Optional[str] = Query(None, description="Filter by status (pending/approved/needs_revision)"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    request: Request = None,
    current_user: dict = Depends(get_current_user)
):
    """Get content for review with filtering and pagination."""
    try:
        logger.debug("[reviews/content] start")
        formatted_content = []
        
        if brand_id and campaign_id:
            logger.debug(f"[reviews/content] brand_id={brand_id} campaign_id={campaign_id}")
            # Fetch real assigned audios from campaign using direct database access
            from services.mongodb_service import mongodb_service
            
            user_id = current_user.get('user_id', current_user.get('id', 'unknown'))
            logger.debug(f"[reviews/content] user_id={user_id}")
            
            # Check if user has access to this brand
            brands_collection = mongodb_service.get_collection('brands')
            brand = brands_collection.find_one({
                "brand_id": brand_id,
                "$or": [
                    {"owner_id": user_id},
                    {"team_members.user_id": user_id}
                ]
            })
            logger.debug(f"[reviews/content] brand_found={bool(brand)}")
            
            if not brand:
                raise HTTPException(status_code=403, detail="Insufficient permissions or brand not found")
            
            # Get assigned audios from database
            assignments_collection = mongodb_service.get_collection('audio_campaign_assignments')
            assignments = list(assignments_collection.find({
                "brand_id": brand_id,
                "status": "active",
                "$or": [
                    {"campaign_id": campaign_id},
                    {"metadata.campaign_id": campaign_id}
                ]
            }))
            logger.info(f"[reviews/content] assignments_count={len(assignments)}")
            for i, assignment in enumerate(assignments):
                logger.info(f"[reviews/content] assignment_{i}: audio_id={assignment.get('audio_id')}, campaign_id={assignment.get('campaign_id')}, metadata_campaign_id={assignment.get('metadata', {}).get('campaign_id')}")
            
            # Use audio_storage_service to get audio data (same as campaign API)
            from services.audio_storage_service import audio_storage_service
            
            # Initialize content items list
            content_items = []
            
            # Format assigned audios for review system
            for i, assignment in enumerate(assignments):
                # Apply content type filter
                if content_type and content_type != "audio":
                    continue
                
                # Get audio details from the assignment
                audio_id = assignment.get("audio_id")
                assignment_user_id = assignment.get("user_id")
                
                # Use audio_storage_service.get_audio_by_id (same as campaign API)
                audio_result = await audio_storage_service.get_audio_by_id(
                    audio_id=audio_id,
                    user_id=assignment_user_id
                )
                
                logger.info(f"[reviews/content] audio_result success: {audio_result.get('success')}, source: {audio_result.get('source')}")
                
                if audio_result.get("success"):
                    audio_file = audio_result.get("audio_file", {})
                    logger.info(f"[reviews/content] audio_text={audio_file.get('text', 'N/A')[:50]}...")
                    logger.info(f"[reviews/content] audio_url={audio_file.get('audio_url', 'N/A')}")
                    
                    # Use the same format as campaign API
                    content_item = {
                        "id": audio_id,
                        "title": audio_file.get("text", "Untitled"),
                        "description": f"Audio generated using {audio_file.get('model_used', 'unknown')} model",
                        "type": "audio",
                        "url": audio_file.get("audio_url", ""),
                        "thumbnail": "",  # No thumbnail for audio
                        "duration": "0:00",  # Duration not available
                        "status": "pending",
                        "brandId": brand_id,
                        "campaignId": campaign_id,
                        "uploadedBy": assignment_user_id,
                        "uploadedAt": to_iso_format(audio_file.get("created_at")),
                        "version": "v1.0",
                        "views": 0,
                        "likes": 0,
                        "comments": 0,
                        "metadata": {
                            "audio_id": audio_id,
                            "text": audio_file.get("text", ""),
                            "text_length": audio_file.get("text_length", 0),
                            "language": audio_file.get("language", "english"),
                            "gender": audio_file.get("gender", "unknown"),
                            "model_used": audio_file.get("model_used", "unknown"),
                            "processing_time": audio_file.get("processing_time", 0.0),
                            "source": audio_result.get("source", "unknown"),
                            "assignment_info": {
                                "assignment_id": assignment.get("assignment_id"),
                                "campaign_id": assignment.get("metadata", {}).get("campaign_id"),
                                "assignment_type": assignment.get("metadata", {}).get("assignment_type", "campaign")
                            }
                        }
                    }
                    
                    content_items.append(content_item)
                else:
                    logger.info(f"[reviews/content] Audio not found for audio_id={audio_id}")
                    # Fallback if audio not found
                    content_item = {
                        "id": audio_id,
                        "title": "Audio not found",
                        "description": "Audio file not found or access denied",
                        "type": "audio",
                        "url": "",
                        "thumbnail": "",
                        "duration": "0:00",
                        "status": "error",
                        "brandId": brand_id,
                        "campaignId": campaign_id,
                        "uploadedBy": assignment_user_id,
                        "uploadedAt": "",
                        "version": "v1.0",
                        "views": 0,
                        "likes": 0,
                        "comments": 0,
                        "metadata": {
                            "audio_id": audio_id,
                            "error": "Audio not found or access denied"
                        }
                    }
                    content_items.append(content_item)
        
        logger.debug("[reviews/content] done, returning response")
        return {
            "success": True,
            "data": {
                "content": content_items,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": len(content_items),
                    "totalPages": (len(content_items) + limit - 1) // limit
                }
            }
        }
        
    except Exception as e:
        logger.exception(f"Error getting content for review: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get content: {str(e)}")

@router.get("/content/{content_id}", response_model=Dict[str, Any])
async def get_content_details(
    content_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get detailed information about specific content."""
    try:
        user_id = current_user.get('user_id', current_user.get('id', 'unknown'))
        
        # Get content from database
        content_collection = mongodb_service.get_collection('content_reviews')
        content = content_collection.find_one({
            "content_id": content_id,
            "uploaded_by": user_id
        })
        
        if not content:
            raise HTTPException(status_code=404, detail="Content not found")
        
        # Format response
        formatted_content = {
            "id": content["content_id"],
            "title": content["title"],
            "description": content.get("description"),
            "type": content["type"],
            "url": content["url"],
            "thumbnail": content.get("thumbnail"),
            "duration": content.get("duration"),
            "status": content.get("status", "pending"),
            "brandId": content["brand_id"],
            "campaignId": content["campaign_id"],
            "uploadedBy": content["uploaded_by"],
            "uploadedAt": content["uploaded_at"].isoformat(),
            "version": content.get("version", "v1.0"),
            "views": content.get("views", 0),
            "likes": content.get("likes", 0),
            "comments": content.get("comments", 0),
            "metadata": content.get("metadata", {})
        }
        
        return {
            "success": True,
            "data": formatted_content
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting content details: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get content details: {str(e)}")

@router.put("/content/{content_id}/status", response_model=Dict[str, Any])
async def update_content_status(
    content_id: str,
    request: StatusUpdateRequest,
    current_user: dict = Depends(get_current_user)
):
    """Update the status of content (audio approval/rejection)."""
    try:
        user_id = current_user.get('user_id', current_user.get('id', 'unknown'))
        
        # content_id is actually audio_id from audio_campaign_assignments
        # Update audio assignment status
        assignments_collection = mongodb_service.get_collection('audio_campaign_assignments')
        
        # First try to find by audio_id
        assignment = assignments_collection.find_one({"audio_id": content_id})
        
        if assignment:
            # Update assignment status
            result = assignments_collection.update_one(
                {"audio_id": content_id},
                {
                    "$set": {
                        "review_status": request.status,
                        "review_notes": request.notes,
                        "reviewed_by": user_id,
                        "reviewed_at": datetime.utcnow()
                    }
                }
            )
            
            return {
                "success": True,
                "message": "Content status updated successfully",
                "data": {
                    "contentId": content_id,
                    "status": request.status,
                    "notes": request.notes,
                    "updatedAt": datetime.utcnow().isoformat()
                }
            }
        else:
            # Fallback: Create a review record if assignment doesn't exist
            review_collection = mongodb_service.get_collection('content_reviews')
            review_doc = {
                "content_id": content_id,
                "audio_id": content_id,
                "status": request.status,
                "status_notes": request.notes,
                "status_updated_by": user_id,
                "status_updated_at": datetime.utcnow(),
                "created_at": datetime.utcnow()
            }
            review_collection.insert_one(review_doc)
            
            return {
                "success": True,
                "message": "Content status updated successfully",
                "data": {
                    "contentId": content_id,
                    "status": request.status,
                    "notes": request.notes,
                    "updatedAt": datetime.utcnow().isoformat()
                }
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating content status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update content status: {str(e)}")

# ============================================================================
# COMMENTS & FEEDBACK APIs
# ============================================================================

@router.get("/content/{content_id}/comments", response_model=Dict[str, Any])
async def get_content_comments(
    content_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get all comments for specific content."""
    try:
        # Get comments from database
        comments_collection = mongodb_service.get_collection('content_comments')
        comments = list(comments_collection.find(
            {"content_id": content_id},
            {"_id": 0}
        ).sort("created_at", 1))
        
        # Format response
        formatted_comments = []
        for comment in comments:
            formatted_comments.append({
                "id": comment["comment_id"],
                "content": comment["content"],
                "timestamp": comment.get("timestamp"),
                "timeInSeconds": comment.get("time_in_seconds"),
                "type": comment.get("type", "feedback"),
                "parentId": comment.get("parent_id"),
                "authorId": comment["author_id"],
                "authorName": comment.get("author_name", "Unknown"),
                "authorAvatar": comment.get("author_avatar"),
                # Timeline selection features
                "startTime": comment.get("start_time"),
                "endTime": comment.get("end_time"),
                "selectionType": comment.get("selection_type"),
                "markerPosition": comment.get("marker_position"),
                "version": comment.get("version"),
                "likes": comment.get("likes", 0),
                "resolved": comment.get("resolved", False),
                "createdAt": comment["created_at"].isoformat(),
                "updatedAt": comment.get("updated_at", comment["created_at"]).isoformat()
            })
        
        return {
            "success": True,
            "data": {
                "comments": formatted_comments
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting comments: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get comments: {str(e)}")

@router.post("/content/{content_id}/comments", response_model=Dict[str, Any])
async def add_comment(
    content_id: str,
    request: CommentRequest,
    current_user: dict = Depends(get_current_user)
):
    """Add a comment to content."""
    try:
        user_id = current_user.get('user_id', current_user.get('id', 'unknown'))
        user_name = current_user.get('name', current_user.get('email', 'Unknown'))
        
        # Create comment
        comment_id = str(uuid.uuid4())
        comment_doc = {
            "comment_id": comment_id,
            "content_id": content_id,
            "parent_id": request.parentId,
            "content": request.content,
            "timestamp": request.timestamp,
            "time_in_seconds": request.timeInSeconds,
            "type": request.type,
            "author_id": user_id,
            "author_name": user_name,
            "author_avatar": current_user.get('avatar'),
            "likes": 0,
            "resolved": False,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            # Timeline selection features
            "start_time": request.startTime,
            "end_time": request.endTime,
            "selection_type": request.selectionType,
            "marker_position": request.markerPosition,
            "version": request.version
        }
        
        # Save comment
        comments_collection = mongodb_service.get_collection('content_comments')
        comments_collection.insert_one(comment_doc)
        
        # Update comment count
        content_collection = mongodb_service.get_collection('content_reviews')
        content_collection.update_one(
            {"content_id": content_id},
            {"$inc": {"comments": 1}}
        )
        
        return {
            "success": True,
            "message": "Comment added successfully",
            "data": {
                "id": comment_id,
                "content": request.content,
                "timestamp": request.timestamp,
                "timeInSeconds": request.timeInSeconds,
                "type": request.type,
                "parentId": request.parentId,
                "authorId": user_id,
                "authorName": user_name,
                "authorAvatar": current_user.get('avatar'),
                "likes": 0,
                "resolved": False,
                "createdAt": datetime.utcnow().isoformat(),
                "updatedAt": datetime.utcnow().isoformat(),
                # Timeline selection features
                "startTime": request.startTime,
                "endTime": request.endTime,
                "selectionType": request.selectionType,
                "markerPosition": request.markerPosition,
                "version": request.version
            }
        }
        
    except Exception as e:
        logger.error(f"Error adding comment: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to add comment: {str(e)}")

@router.put("/comments/{comment_id}", response_model=Dict[str, Any])
async def update_comment(
    comment_id: str,
    request: CommentRequest,
    current_user: dict = Depends(get_current_user)
):
    """Update a comment."""
    try:
        user_id = current_user.get('user_id', current_user.get('id', 'unknown'))
        
        # Update comment
        comments_collection = mongodb_service.get_collection('content_comments')
        result = comments_collection.update_one(
            {"comment_id": comment_id, "author_id": user_id},
            {
                "$set": {
                    "content": request.content,
                    "timestamp": request.timestamp,
                    "time_in_seconds": request.timeInSeconds,
                    "type": request.type,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Comment not found or not authorized")
        
        return {
            "success": True,
            "message": "Comment updated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating comment: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update comment: {str(e)}")

@router.delete("/comments/{comment_id}", response_model=Dict[str, Any])
async def delete_comment(
    comment_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a comment."""
    try:
        user_id = current_user.get('user_id', current_user.get('id', 'unknown'))
        
        # Get comment to find content_id
        comments_collection = mongodb_service.get_collection('content_comments')
        comment = comments_collection.find_one({"comment_id": comment_id})
        
        if not comment:
            raise HTTPException(status_code=404, detail="Comment not found")
        
        if comment["author_id"] != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to delete this comment")
        
        # Delete comment
        comments_collection.delete_one({"comment_id": comment_id})
        
        # Update comment count
        content_collection = mongodb_service.get_collection('content_reviews')
        content_collection.update_one(
            {"content_id": comment["content_id"]},
            {"$inc": {"comments": -1}}
        )
        
        return {
            "success": True,
            "message": "Comment deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting comment: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete comment: {str(e)}")

@router.post("/comments/{comment_id}/like", response_model=Dict[str, Any])
async def like_comment(
    comment_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Like a comment."""
    try:
        user_id = current_user.get('user_id', current_user.get('id', 'unknown'))
        
        # Check if already liked
        likes_collection = mongodb_service.get_collection('comment_likes')
        existing_like = likes_collection.find_one({
            "comment_id": comment_id,
            "user_id": user_id
        })
        
        if existing_like:
            return {
                "success": True,
                "message": "Comment already liked"
            }
        
        # Add like
        like_doc = {
            "like_id": str(uuid.uuid4()),
            "comment_id": comment_id,
            "user_id": user_id,
            "created_at": datetime.utcnow()
        }
        likes_collection.insert_one(like_doc)
        
        # Update comment like count
        comments_collection = mongodb_service.get_collection('content_comments')
        comments_collection.update_one(
            {"comment_id": comment_id},
            {"$inc": {"likes": 1}}
        )
        
        return {
            "success": True,
            "message": "Comment liked successfully"
        }
        
    except Exception as e:
        logger.error(f"Error liking comment: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to like comment: {str(e)}")

@router.delete("/comments/{comment_id}/like", response_model=Dict[str, Any])
async def unlike_comment(
    comment_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Unlike a comment."""
    try:
        user_id = current_user.get('user_id', current_user.get('id', 'unknown'))
        
        # Remove like
        likes_collection = mongodb_service.get_collection('comment_likes')
        result = likes_collection.delete_one({
            "comment_id": comment_id,
            "user_id": user_id
        })
        
        if result.deleted_count == 0:
            return {
                "success": True,
                "message": "Comment was not liked"
            }
        
        # Update comment like count
        comments_collection = mongodb_service.get_collection('content_comments')
        comments_collection.update_one(
            {"comment_id": comment_id},
            {"$inc": {"likes": -1}}
        )
        
        return {
            "success": True,
            "message": "Comment unliked successfully"
        }
        
    except Exception as e:
        logger.error(f"Error unliking comment: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to unlike comment: {str(e)}")

# ============================================================================
# CHAT SYSTEM REMOVED - Using comments only as per requirements
# ============================================================================

# ============================================================================
# VERSIONING APIs
# ============================================================================

@router.get("/content/{content_id}/versions", response_model=Dict[str, Any])
async def get_content_versions(
    content_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get all versions of content."""
    try:
        # Get versions from content_reviews collection
        content_collection = mongodb_service.get_collection('content_reviews')
        versions = list(content_collection.find(
            {"content_id": content_id}
        ).sort("created_at", -1))
        
        formatted_versions = []
        for version in versions:
            formatted_versions.append({
                "version": version.get("version", "1.0"),
                "status": version.get("status", "pending"),
                "createdAt": version["created_at"].isoformat(),
                "createdBy": version.get("uploaded_by"),
                "notes": version.get("status_notes"),
                "comments": version.get("comments", 0),
                "likes": version.get("likes", 0)
            })
        
        return {
            "success": True,
            "data": {
                "contentId": content_id,
                "versions": formatted_versions,
                "totalVersions": len(formatted_versions)
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting content versions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get versions: {str(e)}")

@router.post("/content/{content_id}/versions", response_model=Dict[str, Any])
async def create_content_version(
    content_id: str,
    version: str = Query(..., description="Version number (e.g., 1.1, 2.0)"),
    notes: Optional[str] = Query(None, description="Version notes"),
    current_user: dict = Depends(get_current_user)
):
    """Create a new version of content."""
    try:
        user_id = current_user.get('user_id', current_user.get('id', 'unknown'))
        
        # Create new version document
        version_doc = {
            "content_id": content_id,
            "version": version,
            "status": "pending",
            "status_notes": notes,
            "uploaded_by": user_id,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "comments": 0,
            "likes": 0,
            "views": 0
        }
        
        # Save version
        content_collection = mongodb_service.get_collection('content_reviews')
        content_collection.insert_one(version_doc)
        
        return {
            "success": True,
            "message": f"Version {version} created successfully",
            "data": {
                "contentId": content_id,
                "version": version,
                "status": "pending",
                "createdAt": datetime.utcnow().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error creating content version: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create version: {str(e)}")

@router.get("/content/{content_id}/versions/{version}/comments", response_model=Dict[str, Any])
async def get_version_comments(
    content_id: str,
    version: str,
    current_user: dict = Depends(get_current_user)
):
    """Get comments for a specific version."""
    try:
        # Get comments for specific version
        comments_collection = mongodb_service.get_collection('content_comments')
        comments = list(comments_collection.find({
            "content_id": content_id,
            "version": version
        }).sort("created_at", -1))
        
        formatted_comments = []
        for comment in comments:
            formatted_comments.append({
                "id": comment["comment_id"],
                "content": comment["content"],
                "timestamp": comment.get("timestamp"),
                "timeInSeconds": comment.get("time_in_seconds"),
                "type": comment.get("type", "feedback"),
                "parentId": comment.get("parent_id"),
                "authorId": comment["author_id"],
                "authorName": comment.get("author_name", "Unknown"),
                "authorAvatar": comment.get("author_avatar"),
                "startTime": comment.get("start_time"),
                "endTime": comment.get("end_time"),
                "selectionType": comment.get("selection_type"),
                "markerPosition": comment.get("marker_position"),
                "version": comment.get("version"),
                "likes": comment.get("likes", 0),
                "resolved": comment.get("resolved", False),
                "createdAt": comment["created_at"].isoformat(),
                "updatedAt": comment.get("updated_at", comment["created_at"]).isoformat()
            })
        
        return {
            "success": True,
            "data": {
                "contentId": content_id,
                "version": version,
                "comments": formatted_comments,
                "totalComments": len(formatted_comments)
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting version comments: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get version comments: {str(e)}")

# ============================================================================
# NOTIFICATIONS APIs
# ============================================================================

@router.get("/notifications", response_model=Dict[str, Any])
async def get_notifications(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: dict = Depends(get_current_user)
):
    """Get user notifications."""
    try:
        user_id = current_user.get('user_id', current_user.get('id', 'unknown'))
        
        # Get notifications from database
        notifications_collection = mongodb_service.get_collection('notifications')
        skip = (page - 1) * limit
        
        notifications = list(notifications_collection.find(
            {"user_id": user_id}
        ).sort("created_at", -1).skip(skip).limit(limit))
        
        total = notifications_collection.count_documents({"user_id": user_id})
        
        # Format response
        formatted_notifications = []
        for notification in notifications:
            formatted_notifications.append({
                "id": notification["notification_id"],
                "title": notification["title"],
                "message": notification["message"],
                "type": notification.get("type", "info"),
                "contentId": notification.get("content_id"),
                "isRead": notification.get("is_read", False),
                "createdAt": notification["created_at"].isoformat()
            })
        
        return {
            "success": True,
            "data": {
                "notifications": formatted_notifications,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": total,
                    "totalPages": (total + limit - 1) // limit
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting notifications: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get notifications: {str(e)}")

@router.put("/notifications/{notification_id}/read", response_model=Dict[str, Any])
async def mark_notification_read(
    notification_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Mark a notification as read."""
    try:
        user_id = current_user.get('user_id', current_user.get('id', 'unknown'))
        
        # Update notification
        notifications_collection = mongodb_service.get_collection('notifications')
        result = notifications_collection.update_one(
            {"notification_id": notification_id, "user_id": user_id},
            {"$set": {"is_read": True, "read_at": datetime.utcnow()}}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Notification not found")
        
        return {
            "success": True,
            "message": "Notification marked as read"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking notification as read: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to mark notification as read: {str(e)}")

@router.put("/notifications/read-all", response_model=Dict[str, Any])
async def mark_all_notifications_read(
    current_user: dict = Depends(get_current_user)
):
    """Mark all notifications as read."""
    try:
        user_id = current_user.get('user_id', current_user.get('id', 'unknown'))
        
        # Update all notifications
        notifications_collection = mongodb_service.get_collection('notifications')
        result = notifications_collection.update_many(
            {"user_id": user_id, "is_read": False},
            {"$set": {"is_read": True, "read_at": datetime.utcnow()}}
        )
        
        return {
            "success": True,
            "message": f"Marked {result.modified_count} notifications as read"
        }
        
    except Exception as e:
        logger.error(f"Error marking all notifications as read: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to mark all notifications as read: {str(e)}")

# ============================================================================
# ANALYTICS & REPORTING APIs
# ============================================================================

@router.get("/analytics", response_model=Dict[str, Any])
async def get_review_analytics(
    brand_id: Optional[str] = Query(None, description="Filter by brand ID"),
    campaign_id: Optional[str] = Query(None, description="Filter by campaign ID"),
    date_range: Optional[str] = Query(None, description="Date range filter"),
    current_user: dict = Depends(get_current_user)
):
    """Get review analytics and statistics."""
    try:
        user_id = current_user.get('user_id', current_user.get('id', 'unknown'))
        
        # Build query
        query = {"uploaded_by": user_id}
        if brand_id:
            query["brand_id"] = brand_id
        if campaign_id:
            query["campaign_id"] = campaign_id
        
        # Get analytics from database
        content_collection = mongodb_service.get_collection('content_reviews')
        
        # Total content count
        total_content = content_collection.count_documents(query)
        
        # Content by status
        status_pipeline = [
            {"$match": query},
            {"$group": {"_id": "$status", "count": {"$sum": 1}}}
        ]
        status_stats = list(content_collection.aggregate(status_pipeline))
        
        # Content by type
        type_pipeline = [
            {"$match": query},
            {"$group": {"_id": "$type", "count": {"$sum": 1}}}
        ]
        type_stats = list(content_collection.aggregate(type_pipeline))
        
        # Recent activity
        recent_content = list(content_collection.find(query).sort("uploaded_at", -1).limit(5))
        
        return {
            "success": True,
            "data": {
                "totalContent": total_content,
                "statusBreakdown": {item["_id"]: item["count"] for item in status_stats},
                "typeBreakdown": {item["_id"]: item["count"] for item in type_stats},
                "recentActivity": [
                    {
                        "id": item["content_id"],
                        "title": item["title"],
                        "type": item["type"],
                        "status": item.get("status", "pending"),
                        "uploadedAt": item["uploaded_at"].isoformat()
                    }
                    for item in recent_content
                ]
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting review analytics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get analytics: {str(e)}")

# ============================================================================
# FILE UPLOAD APIs
# ============================================================================

@router.post("/upload", response_model=Dict[str, Any])
async def upload_content_file(
    file: UploadFile = File(...),
    content_type: str = Form(..., description="Content type (video/audio/content)"),
    brand_id: str = Form(...),
    campaign_id: str = Form(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user)
):
    """Upload content file for review."""
    try:
        user_id = current_user.get('user_id', current_user.get('id', 'unknown'))
        
        # Validate file type
        allowed_types = ['video/mp4', 'video/avi', 'video/mov', 'audio/mp3', 'audio/wav', 'audio/m4a']
        if file.content_type not in allowed_types:
            raise HTTPException(status_code=400, detail="Invalid file type")
        
        # Generate unique filename
        file_ext = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        folder_name = f"reviews/{brand_id}/{campaign_id}"
        
        # Save file (using existing audio storage service)
        file_content = await file.read()
        file_url = await audio_storage_service.upload_file(
            file_content,
            file.content_type,
            unique_filename,
            folder_name
        )
        
        if not file_url:
            raise HTTPException(status_code=500, detail="Failed to upload file")
        
        # Create content record
        content_id = str(uuid.uuid4())
        content_doc = {
            "content_id": content_id,
            "title": title,
            "description": description,
            "type": content_type,
            "url": file_url,
            "thumbnail": None,  # Will be generated later
            "duration": None,   # Will be calculated later
            "status": "pending",
            "brand_id": brand_id,
            "campaign_id": campaign_id,
            "uploaded_by": user_id,
            "uploaded_at": datetime.utcnow(),
            "version": "v1.0",
            "views": 0,
            "likes": 0,
            "comments": 0,
            "metadata": {
                "original_filename": file.filename,
                "file_size": len(file_content),
                "content_type": file.content_type
            }
        }
        
        # Save to database
        content_collection = mongodb_service.get_collection('content_reviews')
        content_collection.insert_one(content_doc)
        
        return {
            "success": True,
            "message": "Content uploaded successfully",
            "data": {
                "id": content_id,
                "title": title,
                "type": content_type,
                "url": file_url,
                "status": "pending",
                "uploadedAt": datetime.utcnow().isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading content file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")

# ============================================================================
# SEARCH & FILTER APIs
# ============================================================================

@router.get("/search", response_model=Dict[str, Any])
async def search_content(
    q: str = Query(..., description="Search query"),
    content_type: Optional[str] = Query(None, description="Filter by content type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    brand_id: Optional[str] = Query(None, description="Filter by brand ID"),
    campaign_id: Optional[str] = Query(None, description="Filter by campaign ID"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    current_user: dict = Depends(get_current_user)
):
    """Search content with filters."""
    try:
        user_id = current_user.get('user_id', current_user.get('id', 'unknown'))
        
        # Build search query
        query = {
            "uploaded_by": user_id,
            "$or": [
                {"title": {"$regex": q, "$options": "i"}},
                {"description": {"$regex": q, "$options": "i"}}
            ]
        }
        
        if content_type:
            query["type"] = content_type
        if status:
            query["status"] = status
        if brand_id:
            query["brand_id"] = brand_id
        if campaign_id:
            query["campaign_id"] = campaign_id
        
        # Search in database
        content_collection = mongodb_service.get_collection('content_reviews')
        skip = (page - 1) * limit
        
        results = list(content_collection.find(query).sort("uploaded_at", -1).skip(skip).limit(limit))
        total = content_collection.count_documents(query)
        
        # Format response
        formatted_results = []
        for item in results:
            formatted_results.append({
                "id": item["content_id"],
                "title": item["title"],
                "description": item.get("description"),
                "type": item["type"],
                "url": item["url"],
                "status": item.get("status", "pending"),
                "brandId": item["brand_id"],
                "campaignId": item["campaign_id"],
                "uploadedAt": item["uploaded_at"].isoformat()
            })
        
        return {
            "success": True,
            "data": {
                "results": formatted_results,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": total,
                    "totalPages": (total + limit - 1) // limit
                },
                "query": q
            }
        }
        
    except Exception as e:
        logger.error(f"Error searching content: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to search content: {str(e)}")

# ============================================================================
# PERMISSIONS & ACCESS APIs
# ============================================================================

@router.get("/permissions", response_model=Dict[str, Any])
async def check_review_permissions(
    current_user: dict = Depends(get_current_user)
):
    """Check user's review permissions."""
    try:
        user_id = current_user.get('user_id', current_user.get('id', 'unknown'))
        
        # Get user permissions (simplified for now)
        permissions = {
            "canReview": True,
            "canApprove": True,
            "canReject": True,
            "canComment": True,
            "canUpload": True,
            "canDelete": True
        }
        
        return {
            "success": True,
            "data": {
                "permissions": permissions
            }
        }
        
    except Exception as e:
        logger.error(f"Error checking permissions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to check permissions: {str(e)}")

@router.get("/team-members", response_model=Dict[str, Any])
async def get_team_members(
    brand_id: Optional[str] = Query(None, description="Filter by brand ID"),
    request: Request = None,
    current_user: dict = Depends(get_current_user)
):
    """Get team members for collaboration based on brand."""
    try:
        user_id = current_user.get('user_id', current_user.get('id', 'unknown'))
        
        if not brand_id:
            return {
                "success": False,
                "error": "Brand ID is required to get team members"
            }
        
        # Use direct database access instead of internal API call
        brand = mongodb_service.get_collection('brands').find_one({
            "brand_id": brand_id,
            "$or": [
                {"owner_id": user_id},
                {"team_members.user_id": user_id}
            ]
        })
        
        if not brand:
            return {
                "success": False,
                "error": "Brand not found or access denied"
            }
        
        # Get team members from brand
        team_members = brand.get("team_members", [])
        
        # Format team members with complete user details
        formatted_members = []
        users_collection = mongodb_service.get_collection('users')
        
        for member in team_members:
            # Fetch complete user details from users collection
            user_details = users_collection.find_one({
                "$or": [
                    {"user_id": member.get("user_id")},
                    {"_id": member.get("user_id")}
                ]
            })
            
            # Use user details from users collection if available, otherwise fallback to stored data
            email = None
            name = None
            
            if user_details:
                email = user_details.get("email")
                name = user_details.get("name")
            else:
                # Fallback to stored data in team_members
                email = member.get("email")
                name = member.get("name")
            
            # If still no name, use email as name
            if not name and email:
                name = email
            
            formatted_members.append({
                "id": member.get("user_id"),
                "name": name,
                "email": email,
                "avatar": user_details.get("avatar") if user_details else None,
                "role": member.get("role"),
                "lastActive": to_iso(member.get("joined_at")),
                "status": member.get("status", "active"),
                "permissions": member.get("permissions", []),
                "isOwner": member.get("user_id") == brand.get("owner_id")
            })
        
        return {
            "success": True,
            "data": {
                "brandId": brand_id,
                "brandName": brand.get("name", ""),
                "teamMembers": formatted_members,
                "totalMembers": len(formatted_members)
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting team members: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get team members: {str(e)}")

# ============================================================================
# AUDIO MANAGEMENT
# ============================================================================

@router.post("/content/add-audios")
async def add_audios_to_review(
    brand_id: str = Query(..., description="Brand ID"),
    campaign_id: str = Query(..., description="Campaign ID"),
    request: Request = None,
    current_user: dict = Depends(get_current_user)
):
    """Add assigned audios from campaign to review system."""
    try:
        # Fetch real assigned audios from campaign
        import httpx
        
        # Use direct database access instead of internal API call
        # Get campaign details directly from database
        campaigns_collection = mongodb_service.get_collection('campaigns')
        campaign = campaigns_collection.find_one({
            "campaign_id": campaign_id,
            "brand_id": brand_id
        })
        
        if not campaign:
            return {
                "success": False,
                "error": "Campaign not found"
            }
        
        # Get assigned audios from audio_campaign_assignments
        assignments_collection = mongodb_service.get_collection('audio_campaign_assignments')
        assignments = list(assignments_collection.find({
            "$or": [
                {"campaign_id": campaign_id},
                {"metadata.campaign_id": campaign_id}
            ]
        }))
        
        assigned_audios = []
        for assignment in assignments:
            audio_id = assignment.get("audio_id")
            if audio_id:
                # Get audio details using audio_storage_service
                audio_result = await audio_storage_service.get_audio_by_id(
                    audio_id=audio_id,
                    user_id=assignment.get("user_id")
                )
                
                if audio_result.get("success"):
                    audio_file = audio_result.get("audio_file", {})
                    assigned_audios.append({
                        "audio_id": audio_id,
                        "audio_url": audio_file.get("audio_url", ""),
                        "text": audio_file.get("text", ""),
                        "language": audio_file.get("language", "english"),
                        "gender": audio_file.get("gender", "unknown"),
                        "model_used": audio_file.get("model_used", "unknown"),
                        "processing_time": audio_file.get("processing_time", 0.0),
                        "status": "completed",
                        "created_at": audio_file.get("created_at"),
                        "updated_at": audio_file.get("updated_at"),
                        "assigned_at": assignment.get("assigned_at"),
                        "assigned_by": assignment.get("assigned_by"),
                        "notes": assignment.get("notes", ""),
                        "source": audio_result.get("source", "unknown"),
                        "metadata": {
                            "voice_priority": audio_file.get("voice_priority", "english_male"),
                            "speaker_name": audio_file.get("speaker_name", "default"),
                            "generation_method": audio_file.get("generation_method", "ai_orchestration")
                        },
                        "assignment_info": {
                            "assignment_id": assignment.get("assignment_id"),
                            "campaign_id": assignment.get("metadata", {}).get("campaign_id"),
                            "assignment_type": assignment.get("metadata", {}).get("assignment_type", "campaign")
                        }
                    })
        
        return {
            "success": True,
            "message": "Audios added to review system successfully",
            "data": {
                "added_count": len(assigned_audios),
                "brand_id": brand_id,
                "campaign_id": campaign_id,
                "assigned_audios": assigned_audios
            }
        }
        
    except Exception as e:
        logger.error(f"Error adding audios to review system: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to add audios to review system: {str(e)}")

# ============================================================================
# HEALTH CHECK
# ============================================================================

@router.get("/health")
async def health_check():
    """Health check endpoint for review management service."""
    return {
        "success": True,
        "message": "Review Management service is healthy",
        "timestamp": datetime.utcnow().isoformat()
    }
