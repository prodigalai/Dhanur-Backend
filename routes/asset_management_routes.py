#!/usr/bin/env python3
"""
Campaign Asset Management Routes for Content Crew Prodigal
MongoDB-based Asset Management System
"""

import os
import logging
import secrets
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import mimetypes
from pathlib import Path
import json

from middleware.auth import get_current_user
from services.mongodb_service import mongodb_service
from services.s3_service import upload_buffer_to_s3, delete_file_from_s3

logger = logging.getLogger(__name__)
router = APIRouter()

# Ensure collections exist on startup
def ensure_collections_exist():
    """Ensure required collections exist."""
    try:
        collections = ['campaign_assets', 'brand_guidelines', 'asset_activity_log']
        for collection_name in collections:
            collection = mongodb_service.get_collection(collection_name)
            # Just accessing the collection creates it if it doesn't exist
            collection.find_one()
        logger.info("Asset management collections ensured")
    except Exception as e:
        logger.error(f"Error ensuring collections: {e}")

# Call this on module import
ensure_collections_exist()

# Pydantic Models
class AssetUploadRequest(BaseModel):
    category: str = Field(..., description="Asset category")
    description: Optional[str] = Field(None, description="Asset description")
    tags: List[str] = Field(default=[], description="Asset tags")
    is_public: bool = Field(default=True, description="Is asset public")

class AssetUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, description="Asset name")
    description: Optional[str] = Field(None, description="Asset description")
    category: Optional[str] = Field(None, description="Asset category")
    tags: Optional[List[str]] = Field(None, description="Asset tags")
    is_public: Optional[bool] = Field(None, description="Is asset public")

class BrandGuidelineUploadRequest(BaseModel):
    title: str = Field(..., description="Guideline title")
    version: str = Field(..., description="Guideline version")
    category: str = Field(..., description="Guideline category")
    description: Optional[str] = Field(None, description="Guideline description")
    tags: List[str] = Field(default=[], description="Guideline tags")
    is_active: bool = Field(default=True, description="Is guideline active")

class AssetSearchRequest(BaseModel):
    query: Optional[str] = Field(None, description="Search query")
    category: Optional[str] = Field(None, description="Filter by category")
    type: Optional[str] = Field(None, description="Filter by type")
    tags: Optional[List[str]] = Field(None, description="Filter by tags")
    is_public: Optional[bool] = Field(None, description="Filter by public status")
    page: int = Field(default=1, description="Page number")
    limit: int = Field(default=20, description="Items per page")
    sort_by: str = Field(default="uploaded_at", description="Sort field")
    sort_order: str = Field(default="desc", description="Sort order")

# Helper Functions
def get_file_metadata(file: UploadFile) -> Dict[str, Any]:
    """Extract metadata from uploaded file."""
    try:
        # Get file size
        file.file.seek(0, 2)  # Seek to end
        size_bytes = file.file.tell()
        file.file.seek(0)  # Reset to beginning
        
        # Get file type
        content_type = file.content_type or mimetypes.guess_type(file.filename)[0]
        file_type = content_type.split('/')[0] if content_type else 'unknown'
        
        # Get file extension
        file_ext = Path(file.filename).suffix.lower() if file.filename else ''
        
        return {
            "size_bytes": size_bytes,
            "size_display": format_file_size(size_bytes),
            "content_type": content_type,
            "file_type": file_type,
            "file_extension": file_ext,
            "original_name": file.filename
        }
    except Exception as e:
        logger.error(f"Error getting file metadata: {e}")
        return {
            "size_bytes": 0,
            "size_display": "0 B",
            "content_type": "application/octet-stream",
            "file_type": "unknown",
            "file_extension": "",
            "original_name": file.filename or "unknown"
        }

def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format."""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"

def check_campaign_access(brand_id: str, campaign_id: str, user_id: str) -> bool:
    """Check if user has access to campaign."""
    try:
        # Check brand access
        brand = mongodb_service.get_collection('brands').find_one({
            "brand_id": brand_id,
            "$or": [
                {"owner_id": user_id},
                {"team_members.user_id": user_id}
            ]
        })
        
        if not brand:
            return False
        
        # Check campaign exists
        campaign = mongodb_service.get_collection('campaigns').find_one({
            "brand_id": brand_id,
            "campaign_id": campaign_id
        })
        
        return campaign is not None
    except Exception as e:
        logger.error(f"Error checking campaign access: {e}")
        return False

def log_asset_activity(asset_id: str, user_id: str, action: str, metadata: Dict[str, Any] = None):
    """Log asset activity."""
    try:
        activity_log = {
            "asset_id": asset_id,
            "user_id": user_id,
            "action": action,
            "metadata": metadata or {},
            "created_at": datetime.utcnow()
        }
        mongodb_service.get_collection('asset_activity_log').insert_one(activity_log)
    except Exception as e:
        logger.error(f"Error logging asset activity: {e}")

# ============================================================================
# CAMPAIGN ASSET MANAGEMENT APIs
# ============================================================================

@router.post("/brands/{brand_id}/campaigns/{campaign_id}/assets/upload")
async def upload_campaign_assets(
    brand_id: str,
    campaign_id: str,
    files: List[UploadFile] = File(...),
    category: str = Form(...),
    description: Optional[str] = Form(None),
    tags: str = Form("[]"),  # JSON string
    is_public: bool = Form(True),
    current_user: dict = Depends(get_current_user)
):
    """Upload multiple assets to a campaign."""
    try:
        user_id = current_user.get('user_id', current_user.get('id', 'unknown'))
        
        # Check access
        if not check_campaign_access(brand_id, campaign_id, user_id):
            raise HTTPException(status_code=403, detail="Insufficient permissions or campaign not found")
        
        # Parse tags
        try:
            tags_list = json.loads(tags) if tags else []
        except:
            tags_list = []
        
        uploaded_assets = []
        
        for file in files:
            # Validate file
            if not file.filename:
                continue
            
            # Get file metadata
            metadata = get_file_metadata(file)
            
            # Read file content
            file_content = await file.read()
            
            # Generate unique filename
            file_ext = Path(file.filename).suffix
            unique_filename = f"{uuid.uuid4()}{file_ext}"
            folder_name = f"campaigns/{brand_id}/{campaign_id}/assets"
            
            # Upload to S3 or local storage
            try:
                file_url = upload_buffer_to_s3(
                    file_content,
                    metadata['content_type'],
                    unique_filename,
                    folder_name
                )
                
                if not file_url:
                    raise Exception("S3 upload failed")
                    
            except Exception as e:
                logger.warning(f"S3 upload failed, using local storage: {e}")
                # Fallback to local storage for testing
                import os
                local_dir = f"static/uploads/{folder_name}"
                os.makedirs(local_dir, exist_ok=True)
                local_path = os.path.join(local_dir, unique_filename)
                
                with open(local_path, 'wb') as f:
                    f.write(file_content)
                
                file_url = f"https://dhanur-ai-10fd99bc9730.herokuapp.com/static/uploads/{folder_name}/{unique_filename}"
            
            # Create asset document
            asset_id = str(uuid.uuid4())
            asset_doc = {
                "asset_id": asset_id,
                "campaign_id": campaign_id,
                "brand_id": brand_id,
                "name": file.filename,
                "original_name": file.filename,
                "type": metadata['file_type'],
                "url": file_url,
                "size_bytes": metadata['size_bytes'],
                "size_display": metadata['size_display'],
                "category": category,
                "description": description,
                "tags": tags_list,
                "is_public": is_public,
                "uploaded_by": user_id,
                "uploaded_at": datetime.utcnow(),
                "download_count": 0,
                "last_accessed": None,
                "metadata": {
                    "content_type": metadata['content_type'],
                    "file_extension": metadata['file_extension'],
                    "original_name": file.filename
                },
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            # Save to MongoDB
            mongodb_service.get_collection('campaign_assets').insert_one(asset_doc)
            
            # Log activity
            log_asset_activity(asset_id, user_id, "upload", {"filename": file.filename})
            
            uploaded_assets.append({
                "id": asset_id,
                "name": file.filename,
                "type": metadata['file_type'],
                "url": file_url,
                "size": metadata['size_display'],
                "sizeBytes": metadata['size_bytes'],
                "category": category,
                "description": description,
                "tags": tags_list,
                "isPublic": is_public,
                "uploadedBy": user_id,
                "uploadedAt": asset_doc['uploaded_at'].isoformat(),
                "downloadCount": 0,
                "metadata": asset_doc['metadata']
            })
        
        return {
            "success": True,
            "message": f"Successfully uploaded {len(uploaded_assets)} assets",
            "data": {
                "assets": uploaded_assets
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading assets: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upload assets: {str(e)}")

# ============================================================================
# ASSET ANALYTICS & STATISTICS APIs (Must come before generic routes)
# ============================================================================

@router.get("/brands/{brand_id}/campaigns/{campaign_id}/assets/stats")
async def get_asset_statistics(
    brand_id: str,
    campaign_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get asset statistics for a campaign."""
    try:
        user_id = current_user.get('user_id', current_user.get('id', 'unknown'))
        
        # Check access
        if not check_campaign_access(brand_id, campaign_id, user_id):
            raise HTTPException(status_code=403, detail="Insufficient permissions or campaign not found")
        
        # Get basic stats
        total_assets = mongodb_service.get_collection('campaign_assets').count_documents({
            "brand_id": brand_id,
            "campaign_id": campaign_id
        })
        
        # Get total size
        pipeline = [
            {"$match": {"brand_id": brand_id, "campaign_id": campaign_id}},
            {"$group": {"_id": None, "total_size": {"$sum": "$size_bytes"}}}
        ]
        size_result = list(mongodb_service.get_collection('campaign_assets').aggregate(pipeline))
        total_size_bytes = size_result[0]['total_size'] if size_result else 0
        
        # Get category breakdown
        category_pipeline = [
            {"$match": {"brand_id": brand_id, "campaign_id": campaign_id}},
            {"$group": {"_id": "$category", "count": {"$sum": 1}}}
        ]
        category_stats = list(mongodb_service.get_collection('campaign_assets').aggregate(category_pipeline))
        by_category = {item['_id']: item['count'] for item in category_stats}
        
        # Get type breakdown
        type_pipeline = [
            {"$match": {"brand_id": brand_id, "campaign_id": campaign_id}},
            {"$group": {"_id": "$type", "count": {"$sum": 1}}}
        ]
        type_stats = list(mongodb_service.get_collection('campaign_assets').aggregate(type_pipeline))
        by_type = {item['_id']: item['count'] for item in type_stats}
        
        # Get download stats
        download_pipeline = [
            {"$match": {"brand_id": brand_id, "campaign_id": campaign_id}},
            {"$group": {"_id": None, "total_downloads": {"$sum": "$download_count"}}}
        ]
        download_result = list(mongodb_service.get_collection('campaign_assets').aggregate(download_pipeline))
        total_downloads = download_result[0]['total_downloads'] if download_result else 0
        
        # Get most downloaded asset
        most_downloaded = mongodb_service.get_collection('campaign_assets').find_one(
            {"brand_id": brand_id, "campaign_id": campaign_id},
            sort=[("download_count", -1)]
        )
        
        # Get recent activity
        recent_activity = list(mongodb_service.get_collection('asset_activity_log').find(
            {"asset_id": {"$in": [asset['asset_id'] for asset in mongodb_service.get_collection('campaign_assets').find(
                {"brand_id": brand_id, "campaign_id": campaign_id},
                {"asset_id": 1}
            )]}}
        ).sort("created_at", -1).limit(10))
        
        return {
            "success": True,
            "data": {
                "totalAssets": total_assets,
                "totalSize": format_file_size(total_size_bytes),
                "totalSizeBytes": total_size_bytes,
                "byCategory": by_category,
                "byType": by_type,
                "downloadStats": {
                    "totalDownloads": total_downloads,
                    "mostDownloaded": most_downloaded['asset_id'] if most_downloaded else None
                },
                "recentActivity": [
                    {
                        "assetId": activity['asset_id'],
                        "action": activity['action'],
                        "user": activity['user_id'],
                        "timestamp": activity['created_at'].isoformat()
                    }
                    for activity in recent_activity
                ]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting asset statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get asset statistics: {str(e)}")

@router.get("/brands/{brand_id}/campaigns/{campaign_id}/assets/filters")
async def get_asset_filters(
    brand_id: str,
    campaign_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get available filters for assets."""
    try:
        user_id = current_user.get('user_id', current_user.get('id', 'unknown'))
        
        # Check access
        if not check_campaign_access(brand_id, campaign_id, user_id):
            raise HTTPException(status_code=403, detail="Insufficient permissions or campaign not found")
        
        # Get distinct values
        categories = mongodb_service.get_collection('campaign_assets').distinct("category", {"brand_id": brand_id, "campaign_id": campaign_id})
        types = mongodb_service.get_collection('campaign_assets').distinct("type", {"brand_id": brand_id, "campaign_id": campaign_id})
        
        # Get all tags
        pipeline = [
            {"$match": {"brand_id": brand_id, "campaign_id": campaign_id}},
            {"$unwind": "$tags"},
            {"$group": {"_id": "$tags", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        tag_stats = list(mongodb_service.get_collection('campaign_assets').aggregate(pipeline))
        tags = [{"tag": item['_id'], "count": item['count']} for item in tag_stats]
        
        return {
            "success": True,
            "data": {
                "categories": categories,
                "types": types,
                "tags": tags
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting asset filters: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get asset filters: {str(e)}")

@router.post("/brands/{brand_id}/campaigns/{campaign_id}/assets/search")
async def search_assets(
    brand_id: str,
    campaign_id: str,
    request: AssetSearchRequest,
    current_user: dict = Depends(get_current_user)
):
    """Search assets with advanced filtering."""
    try:
        user_id = current_user.get('user_id', current_user.get('id', 'unknown'))
        
        # Check access
        if not check_campaign_access(brand_id, campaign_id, user_id):
            raise HTTPException(status_code=403, detail="Insufficient permissions or campaign not found")
        
        # Build query
        query = {
            "brand_id": brand_id,
            "campaign_id": campaign_id
        }
        
        if request.category:
            query["category"] = request.category
        if request.type:
            query["type"] = request.type
        if request.is_public is not None:
            query["is_public"] = request.is_public
        if request.tags:
            query["tags"] = {"$in": request.tags}
        if request.query:
            query["$or"] = [
                {"name": {"$regex": request.query, "$options": "i"}},
                {"description": {"$regex": request.query, "$options": "i"}},
                {"tags": {"$regex": request.query, "$options": "i"}}
            ]
        
        # Calculate skip
        skip = (request.page - 1) * request.limit
        
        # Sort order
        sort_direction = -1 if request.sort_order == "desc" else 1
        sort_field = request.sort_by if request.sort_by in ["name", "uploaded_at", "size_bytes", "download_count"] else "uploaded_at"
        
        # Get assets
        cursor = mongodb_service.get_collection('campaign_assets').find(query).sort(sort_field, sort_direction).skip(skip).limit(request.limit)
        assets = list(cursor)
        
        # Get total count
        total = mongodb_service.get_collection('campaign_assets').count_documents(query)
        
        # Format response
        formatted_assets = []
        for asset in assets:
            # Update URL to production if it's localhost
            asset_url = asset['url']
            if "localhost:8000" in asset_url:
                asset_url = asset_url.replace("http://localhost:8000", "https://dhanur-ai-10fd99bc9730.herokuapp.com")
            
            formatted_assets.append({
                "id": asset['asset_id'],
                "name": asset['name'],
                "type": asset['type'],
                "url": asset_url,
                "size": asset['size_display'],
                "sizeBytes": asset['size_bytes'],
                "category": asset['category'],
                "description": asset.get('description'),
                "tags": asset.get('tags', []),
                "isPublic": asset.get('is_public', True),
                "uploadedBy": asset['uploaded_by'],
                "uploadedAt": asset['uploaded_at'].isoformat(),
                "downloadCount": asset.get('download_count', 0),
                "metadata": asset.get('metadata', {})
            })
        
        return {
            "success": True,
            "data": {
                "assets": formatted_assets,
                "pagination": {
                    "page": request.page,
                    "limit": request.limit,
                    "total": total,
                    "totalPages": (total + request.limit - 1) // request.limit
                },
                "query": {
                    "search": request.query,
                    "category": request.category,
                    "type": request.type,
                    "tags": request.tags,
                    "isPublic": request.is_public
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching assets: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to search assets: {str(e)}")

# ============================================================================
# CAMPAIGN ASSET MANAGEMENT APIs
# ============================================================================

@router.get("/brands/{brand_id}/campaigns/{campaign_id}/assets")
async def get_campaign_assets(
    brand_id: str,
    campaign_id: str,
    category: Optional[str] = Query(None, description="Filter by category"),
    type: Optional[str] = Query(None, description="Filter by type"),
    search: Optional[str] = Query(None, description="Search query"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    sort_by: str = Query("uploaded_at", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order"),
    current_user: dict = Depends(get_current_user)
):
    """Get all assets for a campaign with filtering and pagination."""
    try:
        user_id = current_user.get('user_id', current_user.get('id', 'unknown'))
        
        # Check access
        if not check_campaign_access(brand_id, campaign_id, user_id):
            raise HTTPException(status_code=403, detail="Insufficient permissions or campaign not found")
        
        # Build query
        query = {
            "brand_id": brand_id,
            "campaign_id": campaign_id
        }
        
        if category:
            query["category"] = category
        if type:
            query["type"] = type
        if search:
            query["$or"] = [
                {"name": {"$regex": search, "$options": "i"}},
                {"description": {"$regex": search, "$options": "i"}},
                {"tags": {"$in": [{"$regex": search, "$options": "i"}]}}
            ]
        
        # Calculate skip
        skip = (page - 1) * limit
        
        # Sort order
        sort_direction = -1 if sort_order == "desc" else 1
        sort_field = sort_by if sort_by in ["name", "uploaded_at", "size_bytes", "download_count"] else "uploaded_at"
        
        # Get assets
        cursor = mongodb_service.get_collection('campaign_assets').find(query).sort(sort_field, sort_direction).skip(skip).limit(limit)
        assets = list(cursor)
        
        # Get total count
        total = mongodb_service.get_collection('campaign_assets').count_documents(query)
        
        # Format response
        formatted_assets = []
        for asset in assets:
            # Update URL to production if it's localhost
            asset_url = asset['url']
            if "localhost:8000" in asset_url:
                asset_url = asset_url.replace("http://localhost:8000", "https://dhanur-ai-10fd99bc9730.herokuapp.com")
            
            formatted_assets.append({
                "id": asset['asset_id'],
                "name": asset['name'],
                "type": asset['type'],
                "url": asset_url,
                "size": asset['size_display'],
                "sizeBytes": asset['size_bytes'],
                "category": asset['category'],
                "description": asset.get('description'),
                "tags": asset.get('tags', []),
                "isPublic": asset.get('is_public', True),
                "uploadedBy": asset['uploaded_by'],
                "uploadedAt": asset['uploaded_at'].isoformat(),
                "downloadCount": asset.get('download_count', 0),
                "lastAccessed": asset.get('last_accessed').isoformat() if asset.get('last_accessed') else None,
                "metadata": asset.get('metadata', {})
            })
        
        # Get available filters
        categories = mongodb_service.get_collection('campaign_assets').distinct("category", {"brand_id": brand_id, "campaign_id": campaign_id})
        types = mongodb_service.get_collection('campaign_assets').distinct("type", {"brand_id": brand_id, "campaign_id": campaign_id})
        
        return {
            "success": True,
            "data": {
                "assets": formatted_assets,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": total,
                    "totalPages": (total + limit - 1) // limit
                },
                "filters": {
                    "categories": categories,
                    "types": types
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting campaign assets: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get campaign assets: {str(e)}")

@router.get("/brands/{brand_id}/campaigns/{campaign_id}/assets/{asset_id}")
async def get_campaign_asset(
    brand_id: str,
    campaign_id: str,
    asset_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get single campaign asset details."""
    try:
        user_id = current_user.get('user_id', current_user.get('id', 'unknown'))
        
        # Check access
        if not check_campaign_access(brand_id, campaign_id, user_id):
            raise HTTPException(status_code=403, detail="Insufficient permissions or campaign not found")
        
        # Get asset
        asset = mongodb_service.get_collection('campaign_assets').find_one({
            "asset_id": asset_id,
            "brand_id": brand_id,
            "campaign_id": campaign_id
        })
        
        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")
        
        # Log view activity
        log_asset_activity(asset_id, user_id, "view")
        
        return {
            "success": True,
            "data": {
                "id": asset['asset_id'],
                "name": asset['name'],
                "type": asset['type'],
                "url": asset['url'],
                "size": asset['size_display'],
                "sizeBytes": asset['size_bytes'],
                "category": asset['category'],
                "description": asset.get('description'),
                "tags": asset.get('tags', []),
                "isPublic": asset.get('is_public', True),
                "uploadedBy": asset['uploaded_by'],
                "uploadedAt": asset['uploaded_at'].isoformat(),
                "downloadCount": asset.get('download_count', 0),
                "lastAccessed": asset.get('last_accessed').isoformat() if asset.get('last_accessed') else None,
                "metadata": asset.get('metadata', {})
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting campaign asset: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get campaign asset: {str(e)}")

@router.put("/brands/{brand_id}/campaigns/{campaign_id}/assets/{asset_id}")
async def update_campaign_asset(
    brand_id: str,
    campaign_id: str,
    asset_id: str,
    request: AssetUpdateRequest,
    current_user: dict = Depends(get_current_user)
):
    """Update campaign asset details."""
    try:
        user_id = current_user.get('user_id', current_user.get('id', 'unknown'))
        
        # Check access
        if not check_campaign_access(brand_id, campaign_id, user_id):
            raise HTTPException(status_code=403, detail="Insufficient permissions or campaign not found")
        
        # Get asset
        asset = mongodb_service.get_collection('campaign_assets').find_one({
            "asset_id": asset_id,
            "brand_id": brand_id,
            "campaign_id": campaign_id
        })
        
        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")
        
        # Prepare update data
        update_data = {"updated_at": datetime.utcnow()}
        
        if request.name is not None:
            update_data["name"] = request.name
        if request.description is not None:
            update_data["description"] = request.description
        if request.category is not None:
            update_data["category"] = request.category
        if request.tags is not None:
            update_data["tags"] = request.tags
        if request.is_public is not None:
            update_data["is_public"] = request.is_public
        
        # Update asset
        result = mongodb_service.get_collection('campaign_assets').update_one(
            {"asset_id": asset_id},
            {"$set": update_data}
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=400, detail="No changes made")
        
        # Log activity
        log_asset_activity(asset_id, user_id, "edit", {"changes": update_data})
        
        return {
            "success": True,
            "message": "Asset updated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating campaign asset: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update campaign asset: {str(e)}")

@router.delete("/brands/{brand_id}/campaigns/{campaign_id}/assets/{asset_id}")
async def delete_campaign_asset(
    brand_id: str,
    campaign_id: str,
    asset_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete campaign asset."""
    try:
        user_id = current_user.get('user_id', current_user.get('id', 'unknown'))
        
        # Check access
        if not check_campaign_access(brand_id, campaign_id, user_id):
            raise HTTPException(status_code=403, detail="Insufficient permissions or campaign not found")
        
        # Get asset
        asset = mongodb_service.get_collection('campaign_assets').find_one({
            "asset_id": asset_id,
            "brand_id": brand_id,
            "campaign_id": campaign_id
        })
        
        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")
        
        # Delete from S3 (extract object key from URL)
        try:
            file_url = asset['url']
            # Extract object key from S3 URL
            # Assuming URL format: https://endpoint/bucket/folder/file
            url_parts = file_url.split('/')
            if len(url_parts) >= 4:
                object_key = '/'.join(url_parts[3:])  # Everything after bucket name
                delete_file_from_s3(object_key)
        except Exception as e:
            logger.warning(f"Failed to delete file from S3: {e}")
        
        # Delete from MongoDB
        result = mongodb_service.get_collection('campaign_assets').delete_one({
            "asset_id": asset_id
        })
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Asset not found")
        
        # Log activity
        log_asset_activity(asset_id, user_id, "delete", {"filename": asset['name']})
        
        return {
            "success": True,
            "message": "Asset deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting campaign asset: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete campaign asset: {str(e)}")

@router.get("/brands/{brand_id}/campaigns/{campaign_id}/assets/{asset_id}/download")
async def download_campaign_asset(
    brand_id: str,
    campaign_id: str,
    asset_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Download campaign asset."""
    try:
        user_id = current_user.get('user_id', current_user.get('id', 'unknown'))
        
        # Check access
        if not check_campaign_access(brand_id, campaign_id, user_id):
            raise HTTPException(status_code=403, detail="Insufficient permissions or campaign not found")
        
        # Get asset
        asset = mongodb_service.get_collection('campaign_assets').find_one({
            "asset_id": asset_id,
            "brand_id": brand_id,
            "campaign_id": campaign_id
        })
        
        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")
        
        # Update download count and last accessed
        mongodb_service.get_collection('campaign_assets').update_one(
            {"asset_id": asset_id},
            {
                "$inc": {"download_count": 1},
                "$set": {"last_accessed": datetime.utcnow()}
            }
        )
        
        # Log activity
        log_asset_activity(asset_id, user_id, "download")
        
        # Return redirect to S3 URL (update to production if localhost)
        download_url = asset['url']
        if "localhost:8000" in download_url:
            download_url = download_url.replace("http://localhost:8000", "https://dhanur-ai-10fd99bc9730.herokuapp.com")
        
        return {
            "success": True,
            "download_url": download_url,
            "filename": asset['name']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading campaign asset: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to download campaign asset: {str(e)}")

@router.get("/brands/{brand_id}/campaigns/{campaign_id}/assets/{asset_id}/preview")
async def get_asset_preview_url(
    brand_id: str,
    campaign_id: str,
    asset_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get asset preview URL."""
    try:
        user_id = current_user.get('user_id', current_user.get('id', 'unknown'))
        
        # Check access
        if not check_campaign_access(brand_id, campaign_id, user_id):
            raise HTTPException(status_code=403, detail="Insufficient permissions or campaign not found")
        
        # Get asset
        asset = mongodb_service.get_collection('campaign_assets').find_one({
            "asset_id": asset_id,
            "brand_id": brand_id,
            "campaign_id": campaign_id
        })
        
        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")
        
        # Log view activity
        log_asset_activity(asset_id, user_id, "preview")
        
        return {
            "success": True,
            "preview_url": asset['url'],
            "filename": asset['name'],
            "content_type": asset.get('metadata', {}).get('content_type', 'application/octet-stream')
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting asset preview: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get asset preview: {str(e)}")

# ============================================================================
# BRAND GUIDELINES MANAGEMENT APIs
# ============================================================================

@router.post("/brands/{brand_id}/guidelines/upload")
async def upload_brand_guideline(
    brand_id: str,
    file: UploadFile = File(...),
    title: str = Form(...),
    version: str = Form(...),
    category: str = Form(...),
    description: Optional[str] = Form(None),
    tags: str = Form("[]"),  # JSON string
    is_active: bool = Form(True),
    current_user: dict = Depends(get_current_user)
):
    """Upload brand guideline."""
    try:
        user_id = current_user.get('user_id', current_user.get('id', 'unknown'))
        
        # Check brand access
        brand = mongodb_service.get_collection('brands').find_one({
            "brand_id": brand_id,
            "$or": [
                {"owner_id": user_id},
                {"team_members.user_id": user_id}
            ]
        })
        
        if not brand:
            raise HTTPException(status_code=403, detail="Insufficient permissions or brand not found")
        
        # Parse tags
        try:
            tags_list = json.loads(tags) if tags else []
        except:
            tags_list = []
        
        # Get file metadata
        metadata = get_file_metadata(file)
        
        # Read file content
        file_content = await file.read()
        
        # Generate unique filename
        file_ext = Path(file.filename).suffix
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        folder_name = f"brands/{brand_id}/guidelines"
        
        # Upload to S3 or local storage
        try:
            file_url = upload_buffer_to_s3(
                file_content,
                metadata['content_type'],
                unique_filename,
                folder_name
            )
            
            if not file_url:
                raise Exception("S3 upload failed")
                
        except Exception as e:
            logger.warning(f"S3 upload failed, using local storage: {e}")
            # Fallback to local storage for testing
            import os
            local_dir = f"static/uploads/{folder_name}"
            os.makedirs(local_dir, exist_ok=True)
            local_path = os.path.join(local_dir, unique_filename)
            
            with open(local_path, 'wb') as f:
                f.write(file_content)
            
            file_url = f"https://dhanur-ai-10fd99bc9730.herokuapp.com/static/uploads/{folder_name}/{unique_filename}"
        
        # Create guideline document
        guideline_id = str(uuid.uuid4())
        guideline_doc = {
            "guideline_id": guideline_id,
            "brand_id": brand_id,
            "title": title,
            "version": version,
            "category": category,
            "description": description,
            "file_url": file_url,
            "file_type": metadata['file_type'],
            "file_size": metadata['size_display'],
            "file_size_bytes": metadata['size_bytes'],
            "uploaded_by": user_id,
            "uploaded_at": datetime.utcnow(),
            "is_active": is_active,
            "tags": tags_list,
            "download_count": 0,
            "last_accessed": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        # Save to MongoDB
        mongodb_service.get_collection('brand_guidelines').insert_one(guideline_doc)
        
        return {
            "success": True,
            "message": "Brand guideline uploaded successfully",
            "data": {
                "id": guideline_id,
                "title": title,
                "version": version,
                "category": category,
                "url": file_url,
                "size": metadata['size_display'],
                "isActive": is_active
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading brand guideline: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upload brand guideline: {str(e)}")

@router.get("/brands/{brand_id}/guidelines")
async def get_brand_guidelines(
    brand_id: str,
    category: Optional[str] = Query(None, description="Filter by category"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search query"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: dict = Depends(get_current_user)
):
    """Get all brand guidelines with filtering and pagination."""
    try:
        user_id = current_user.get('user_id', current_user.get('id', 'unknown'))
        
        # Check brand access
        brand = mongodb_service.get_collection('brands').find_one({
            "brand_id": brand_id,
            "$or": [
                {"owner_id": user_id},
                {"team_members.user_id": user_id}
            ]
        })
        
        if not brand:
            raise HTTPException(status_code=403, detail="Insufficient permissions or brand not found")
        
        # Build query
        query = {"brand_id": brand_id}
        
        if category:
            query["category"] = category
        if is_active is not None:
            query["is_active"] = is_active
        if search:
            query["$or"] = [
                {"title": {"$regex": search, "$options": "i"}},
                {"description": {"$regex": search, "$options": "i"}},
                {"tags": {"$in": [{"$regex": search, "$options": "i"}]}}
            ]
        
        # Calculate skip
        skip = (page - 1) * limit
        
        # Get guidelines
        cursor = mongodb_service.get_collection('brand_guidelines').find(query).sort("uploaded_at", -1).skip(skip).limit(limit)
        guidelines = list(cursor)
        
        # Get total count
        total = mongodb_service.get_collection('brand_guidelines').count_documents(query)
        
        # Format response
        formatted_guidelines = []
        for guideline in guidelines:
            # Update URL to production if it's localhost
            guideline_url = guideline['file_url']
            if "localhost:8000" in guideline_url:
                guideline_url = guideline_url.replace("http://localhost:8000", "https://dhanur-ai-10fd99bc9730.herokuapp.com")
            
            formatted_guidelines.append({
                "id": guideline['guideline_id'],
                "title": guideline['title'],
                "version": guideline['version'],
                "category": guideline['category'],
                "description": guideline.get('description'),
                "url": guideline_url,
                "size": guideline['file_size'],
                "sizeBytes": guideline['file_size_bytes'],
                "isActive": guideline.get('is_active', True),
                "tags": guideline.get('tags', []),
                "uploadedBy": guideline['uploaded_by'],
                "uploadedAt": guideline['uploaded_at'].isoformat(),
                "downloadCount": guideline.get('download_count', 0),
                "lastAccessed": guideline.get('last_accessed').isoformat() if guideline.get('last_accessed') else None
            })
        
        return {
            "success": True,
            "data": {
                "guidelines": formatted_guidelines,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": total,
                    "totalPages": (total + limit - 1) // limit
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting brand guidelines: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get brand guidelines: {str(e)}")

@router.get("/brands/{brand_id}/guidelines/{guideline_id}/download")
async def download_brand_guideline(
    brand_id: str,
    guideline_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Download brand guideline."""
    try:
        user_id = current_user.get('user_id', current_user.get('id', 'unknown'))
        
        # Check brand access
        brand = mongodb_service.get_collection('brands').find_one({
            "brand_id": brand_id,
            "$or": [
                {"owner_id": user_id},
                {"team_members.user_id": user_id}
            ]
        })
        
        if not brand:
            raise HTTPException(status_code=403, detail="Insufficient permissions or brand not found")
        
        # Get guideline
        guideline = mongodb_service.get_collection('brand_guidelines').find_one({
            "guideline_id": guideline_id,
            "brand_id": brand_id
        })
        
        if not guideline:
            raise HTTPException(status_code=404, detail="Guideline not found")
        
        # Update download count and last accessed
        mongodb_service.get_collection('brand_guidelines').update_one(
            {"guideline_id": guideline_id},
            {
                "$inc": {"download_count": 1},
                "$set": {"last_accessed": datetime.utcnow()}
            }
        )
        
        # Update URL to production if it's localhost
        download_url = guideline['file_url']
        if "localhost:8000" in download_url:
            download_url = download_url.replace("http://localhost:8000", "https://dhanur-ai-10fd99bc9730.herokuapp.com")
        
        return {
            "success": True,
            "download_url": download_url,
            "filename": f"{guideline['title']}_{guideline['version']}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading brand guideline: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to download brand guideline: {str(e)}")

