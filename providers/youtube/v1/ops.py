from typing import Dict, Optional, List
from googleapiclient.http import MediaFileUpload
from .client import youtube_service, media_upload
from .policy import assert_allowed

def get_assignable_categories(youtube, region_code="IN", hl="en"):
    """Get valid, assignable video categories for the specified region."""
    try:
        cats = {}
        req = youtube.videoCategories().list(part="snippet", regionCode=region_code, hl=hl)
        res = req.execute()
        for it in res.get("items", []):
            if it["snippet"].get("assignable"):
                cats[it["snippet"]["title"].lower()] = it["id"]
        print(f"🔍 Found {len(cats)} assignable categories for region {region_code}")
        return cats
    except Exception as e:
        print(f"❌ Error fetching categories: {e}")
        # Return some common fallback categories
        return {
            "people & blogs": "22",
            "entertainment": "24", 
            "gaming": "20",
            "music": "10",
            "education": "27"
        }

def get_safe_category_id(youtube, current_category_id=None, region_code="IN"):
    """Get a safe category ID, preferring the current one if it's valid."""
    try:
        # First try to validate the current category ID
        if current_category_id:
            try:
                cat_info = youtube.videoCategories().list(part="snippet", id=current_category_id).execute()
                if cat_info.get("items") and cat_info["items"][0]["snippet"].get("assignable"):
                    print(f"✅ Current category ID {current_category_id} is valid and assignable")
                    return current_category_id
                else:
                    print(f"⚠️ Current category ID {current_category_id} is not assignable")
            except Exception as e:
                print(f"⚠️ Error validating current category ID {current_category_id}: {e}")
        
        # If current category is invalid, get a safe fallback
        cats = get_assignable_categories(youtube, region_code)
        # Prefer "People & Blogs" as it's widely available
        safe_id = cats.get("people & blogs", "22")
        print(f"🔄 Using safe fallback category ID: {safe_id}")
        return safe_id
    except Exception as e:
        print(f"❌ Error getting safe category ID: {e}")
        return "22"  # Final fallback

# ---- READ
def channels_list_mine(token_blob: Dict, role: str = "viewer"):
    op = "channels_list_mine"
    assert_allowed(role, op)
    yt = youtube_service(token_blob)
    req = yt.channels().list(
        mine=True,
        part="snippet,contentDetails,statistics"
    )
    return req.execute()

# ---- CREATE (upload video)
def videos_insert(token_blob: Dict, video_path: str, title: str, description: str,
                  tags: Optional[List[str]] = None, privacy_status: str = "unlisted",
                  role: str = "uploader", mimetype: str = "video/*"):
    op = "videos_insert"
    assert_allowed(role, op)
    yt = youtube_service(token_blob)
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags or []
        },
        "status": {
            "privacyStatus": privacy_status
        }
    }
    media = media_upload(video_path, mimetype)
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
    return req.execute()

# ---- UPDATE (metadata)
def videos_update(token_blob: Dict, video_id: str, title: Optional[str] = None,
                  description: Optional[str] = None, tags: Optional[List[str]] = None,
                  privacy_status: Optional[str] = None, role: str = "editor"):
    op = "videos_update"
    assert_allowed(role, op)
    yt = youtube_service(token_blob)
    
    # First, let's get the current video data to see what fields exist
    print(f"🔍 Getting current video data for: {video_id}")
    try:
        current_video = yt.videos().list(part="snippet,status", id=video_id).execute()
        if not current_video.get("items"):
            raise ValueError(f"Video {video_id} not found")
        
        current_snippet = current_video["items"][0].get("snippet", {})
        current_status = current_video["items"][0].get("status", {})
        print(f"🔍 Current snippet fields: {list(current_snippet.keys())}")
        print(f"🔍 Current status fields: {list(current_status.keys())}")
        
        # Check if categoryId exists and what its value is
        if "categoryId" in current_snippet:
            print(f"⚠️ Found categoryId: {current_snippet['categoryId']}")
        
    except Exception as e:
        print(f"❌ Error getting current video data: {e}")
        # Continue with update anyway
    
    # Get a safe category ID for the video
    current_category_id = current_snippet.get("categoryId")
    safe_category_id = get_safe_category_id(yt, current_category_id)
    print(f"🔧 Using safe category ID: {safe_category_id}")
    
    # Build a complete update request with all required fields
    update_fields = {}
    if title is not None:
        update_fields["title"] = title
    if description is not None:
        update_fields["description"] = description
    if tags is not None:
        update_fields["tags"] = tags
    
    if update_fields:
        print(f"🔧 Updating snippet fields: {list(update_fields.keys())}")
        
        # Create a complete snippet object with required fields
        snippet_body = {}
        for field, value in update_fields.items():
            if value is not None and value != "":
                snippet_body[field] = value
        
        # Always include the title if we're updating the snippet (YouTube requirement)
        if "title" not in snippet_body and current_snippet.get("title"):
            snippet_body["title"] = current_snippet["title"]
            print(f"🔧 Including existing title: {snippet_body['title']}")
        
        # Always include a valid categoryId (YouTube requirement)
        snippet_body["categoryId"] = safe_category_id
        print(f"🔧 Including safe categoryId: {safe_category_id}")
        
        # Build the complete update body
        update_body = {
            "id": video_id,
            "snippet": snippet_body
        }
        
        print(f"🔧 Complete snippet update body: {update_body}")
        
        try:
            req = yt.videos().update(part="snippet", body=update_body)
            result = req.execute()
            print(f"✅ Snippet update successful: {result}")
        except Exception as e:
            print(f"❌ Snippet update failed: {e}")
            raise e
    
    # Handle privacy status separately (it's in the status part, not snippet)
    if privacy_status is not None:
        print(f"🔧 Updating privacy status to: {privacy_status}")
        try:
            status_body = {
                "id": video_id,
                "status": {"privacyStatus": privacy_status}
            }
            print(f"🔧 Status update body: {status_body}")
            
            req = yt.videos().update(part="status", body=status_body)
            result = req.execute()
            print(f"✅ Privacy status update successful: {result}")
        except Exception as e:
            print(f"❌ Privacy status update failed: {e}")
            raise e
    
    # Return a simple success response since we're doing individual updates
    return {"success": True, "video_id": video_id}

# ---- UPDATE (channel metadata)
def channels_update(token_blob: Dict, channel_id: str, body: Dict, part: str = "snippet,brandingSettings,localizations", role: str = "editor"):
    op = "channels_update"
    assert_allowed(role, op)
    yt = youtube_service(token_blob)
    
    print(f"🔧 Updating channel {channel_id} with part: {part}")
    print(f"🔧 Update body: {body}")
    
    req = yt.channels().update(
        part=part,
        body=body
    )
    return req.execute()

def channel_banners_insert(token_blob, media_body, role):
    """Upload channel banner image"""
    yt = get_youtube_client(token_blob, role)
    return yt.channelBanners().insert(
        media_body=media_body
    ).execute()

def watermarks_set(token_blob, channel_id, body, media_body, role):
    """Set channel watermark"""
    yt = get_youtube_client(token_blob, role)
    return yt.watermarks().set(
        channelId=channel_id,
        body=body,
        media_body=media_body
    ).execute()

def watermarks_unset(token_blob, channel_id, role):
    """Remove channel watermark"""
    yt = get_youtube_client(token_blob, role)
    return yt.watermarks().unset(
        channelId=channel_id
    ).execute()

def channel_sections_list(token_blob, channel_id, part, role):
    """List channel sections"""
    yt = get_youtube_client(token_blob, role)
    return yt.channelSections().list(
        channelId=channel_id,
        part=part
    ).execute()

def channel_sections_insert(token_blob, body, part, role):
    """Create channel section"""
    yt = get_youtube_client(token_blob, role)
    return yt.channelSections().insert(
        part=part,
        body=body
    ).execute()

def channel_sections_update(token_blob, section_id, body, part, role):
    """Update channel section"""
    yt = get_youtube_client(token_blob, role)
    return yt.channelSections().update(
        part=part,
        body=body
    ).execute()

def channel_sections_delete(token_blob, section_id, role):
    """Delete channel section"""
    yt = get_youtube_client(token_blob, role)
    return yt.channelSections().delete(
        id=section_id
    ).execute()

# ---- DELETE
def videos_delete(token_blob: Dict, video_id: str, role: str = "admin"):
    op = "videos_delete"
    assert_allowed(role, op)
    yt = youtube_service(token_blob)
    req = yt.videos().delete(id=video_id)
    return req.execute()

# ---- PLAYLISTS
def playlists_insert(token_blob: Dict, title: str, description: str = "",
                     privacy_status: str = "unlisted", role: str = "editor"):
    op = "playlists_insert"
    assert_allowed(role, op)
    yt = youtube_service(token_blob)
    body = {
        "snippet": {"title": title, "description": description},
        "status": {"privacyStatus": privacy_status}
    }
    req = yt.playlists().insert(part="snippet,status", body=body)
    return req.execute()

def playlist_items_insert(token_blob: Dict, playlist_id: str, video_id: str, role: str = "editor"):
    op = "playlistItems_insert"
    assert_allowed(role, op)
    yt = youtube_service(token_blob)
    body = {
        "snippet": {
            "playlistId": playlist_id,
            "resourceId": {"kind": "youtube#video", "videoId": video_id}
        }
    }
    req = yt.playlistItems().insert(part="snippet", body=body)
    return req.execute()
