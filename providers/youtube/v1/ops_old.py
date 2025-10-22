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
    
    # Try the simplest possible approach - individual field updates
    if title is not None:
        print(f"🔧 Updating title to: {title}")
        try:
            # Create the most minimal possible request
            minimal_body = {
                "id": video_id,
                "snippet": {"title": title}
            }
            print(f"🔧 Minimal title body: {minimal_body}")
            
            # Use the most basic update call possible
            req = yt.videos().update(part="snippet", body=minimal_body)
            result = req.execute()
            print(f"✅ Title update successful: {result}")
        except Exception as e:
            print(f"❌ Title update failed: {e}")
            raise e
    
    if description is not None:
        print(f"🔧 Updating description to: {description}")
        try:
            minimal_body = {
                "id": video_id,
                "snippet": {"description": description}
            }
            print(f"🔧 Minimal description body: {minimal_body}")
            
            req = yt.videos().update(part="snippet", body=minimal_body)
            result = req.execute()
            print(f"✅ Description update successful: {result}")
        except Exception as e:
            print(f"❌ Description update failed: {e}")
            raise e
    
    if tags is not None:
        print(f"🔧 Updating tags to: {tags}")
        try:
            minimal_body = {
                "id": video_id,
                "snippet": {"tags": tags}
            }
            print(f"🔧 Minimal tags body: {minimal_body}")
            
            req = yt.videos().update(part="snippet", body=minimal_body)
            result = req.execute()
            print(f"✅ Tags update successful: {result}")
        except Exception as e:
            print(f"❌ Tags update failed: {e}")
            raise e
    
    if privacy_status is not None:
        print(f"🔧 Updating privacy status to: {privacy_status}")
        try:
            minimal_body = {
                "id": video_id,
                "status": {"privacyStatus": privacy_status}
            }
            print(f"🔧 Minimal privacy body: {minimal_body}")
            
            req = yt.videos().update(part="status", body=minimal_body)
            result = req.execute()
            print(f"✅ Privacy status update successful: {result}")
        except Exception as e:
            print(f"❌ Privacy status update failed: {e}")
            raise e
    
    # Return a simple success response since we're doing individual updates
    return {"success": True, "video_id": video_id}

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
