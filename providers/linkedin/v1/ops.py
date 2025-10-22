import requests
import json
from typing import Dict, Optional, List


def get_profile(access_token: str) -> Dict:
    """
    Get LinkedIn user profile using OpenID Connect.
    """
    from .oauth import get_user_profile
    return get_user_profile(access_token)


def create_post(access_token: str, post_data: Dict) -> Dict:
    """
    Create a LinkedIn post with support for text, images, videos, documents, and PDFs.
    
    Args:
        access_token: LinkedIn access token
        post_data: Post content including text, visibility, media files, etc.
    
    Returns:
        Created post response
    """
    post_url = "https://api.linkedin.com/rest/posts"
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'LinkedIn-Version': '202502',
        'X-RestLi-Protocol-Version': '2.0.0',
        'Content-Type': 'application/json'
    }
    
    # Use the profile_id from the connection data for proper ownership
    author_urn = f"urn:li:person:{post_data.get('profile_id')}"
    
    # Build the post body using Posts API format
    post_body = {
        "author": author_urn,
        "commentary": post_data.get('text', ''),
        "visibility": post_data.get('visibility', 'PUBLIC'),
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": []
        },
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False
    }
    
    # Handle different media types for Posts API
    media_files = post_data.get('media_files', [])
    if media_files and len(media_files) > 0:
        # Filter out media files without valid assets
        valid_media_files = [f for f in media_files if f.get('asset')]
        
        if valid_media_files:
            # For Posts API, we can only handle one media item at a time
            # Use the first valid media file
            media_file = valid_media_files[0]
            media_type = media_file.get('type', '')
            
            # Check if this is a document type
            if 'pdf' in media_type.lower() or 'document' in media_type.lower():
                print(f"⚠️ Documents not fully supported in Posts API, falling back to UGC Posts API")
                # For documents, we need to use the old UGC Posts API
                return create_post_ugc(access_token, post_data)
            
            # Add media to post using Posts API format for images/videos
            post_body["content"] = {
                "media": {
                    "id": media_file.get('asset')
                }
            }
            
            print(f"✅ Media post prepared with media: {media_file.get('asset')}")
        else:
            print(f"⚠️ No valid media assets found, creating text-only post")
    else:
        print(f"📝 Creating text-only post")
    
    # Legacy support for single media_url
    if post_data.get('media_url'):
        post_body["content"] = {
            "media": {
                "id": post_data.get('media_url')
            }
        }
    
    # Debug logging
    print(f"🔧 LinkedIn Post Request:")
    print(f"   URL: {post_url}")
    print(f"   Headers: {headers}")
    print(f"   Body: {json.dumps(post_body, indent=2)}")
    print(f"   Author URN: {author_urn}")
    print(f"   Profile ID: {post_data.get('profile_id')}")
    
    response = requests.post(post_url, headers=headers, json=post_body)
    
    # Debug response
    print(f"🔧 LinkedIn Post Response:")
    print(f"   Status: {response.status_code}")
    print(f"   Headers: {dict(response.headers)}")
    print(f"   Body: {response.text}")
    
    response.raise_for_status()
    
    # Handle empty response body (common with LinkedIn API)
    if response.status_code == 201 and not response.text.strip():
        # Success with empty body - extract post ID from Location header
        location_header = response.headers.get('Location', '')
        if location_header:
            # Extract post ID from Location header
            post_id = location_header.split('/')[-1]
            return {"id": post_id, "status": "created"}
        else:
            # Fallback for successful creation without Location header
            return {"id": "unknown", "status": "created"}
    
    # Try to parse JSON response if available
    try:
        return response.json()
    except ValueError:
        # If JSON parsing fails, return basic success info
        return {"id": "unknown", "status": "created", "response_text": response.text}


def create_post_ugc(access_token: str, post_data: Dict) -> Dict:
    """
    Create a LinkedIn post using UGC Posts API for documents and other media types.
    
    Args:
        access_token: LinkedIn access token
        post_data: Post content and metadata
    
    Returns:
        Created post response
    """
    post_url = "https://api.linkedin.com/v2/ugcPosts"
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'X-Restli-Protocol-Version': '2.0.0',
        'Content-Type': 'application/json'
    }
    
    # Use the profile_id from the connection data for proper ownership
    author_urn = f"urn:li:person:{post_data.get('profile_id')}"
    
    # Build the post body using UGC Posts API format
    post_body = {
        "author": author_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {
                    "text": post_data.get('text', '')
                },
                "shareMediaCategory": "NONE"
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": post_data.get('visibility', 'PUBLIC')
        }
    }
    
    # Handle media files for UGC Posts API
    media_files = post_data.get('media_files', [])
    if media_files and len(media_files) > 0:
        valid_media_files = [f for f in media_files if f.get('asset')]
        
        if valid_media_files:
            media_file = valid_media_files[0]
            media_type = media_file.get('type', '')
            
            # Determine media category
            if 'pdf' in media_type.lower() or 'document' in media_type.lower():
                post_body["specificContent"]["com.linkedin.ugc.ShareContent"]["shareMediaCategory"] = "DOCUMENT"
            elif 'image' in media_type.lower():
                post_body["specificContent"]["com.linkedin.ugc.ShareContent"]["shareMediaCategory"] = "IMAGE"
            elif 'video' in media_type.lower():
                post_body["specificContent"]["com.linkedin.ugc.ShareContent"]["shareMediaCategory"] = "VIDEO"
            
            # Add media files
            post_body["specificContent"]["com.linkedin.ugc.ShareContent"]["media"] = [{
                "status": "READY",
                "media": media_file.get('asset')
            }]
            
            print(f"✅ UGC Media post prepared with {media_file.get('type')}: {media_file.get('asset')}")
    
    # Debug logging
    print(f"🔧 LinkedIn UGC Post Request:")
    print(f"   URL: {post_url}")
    print(f"   Headers: {headers}")
    print(f"   Body: {json.dumps(post_body, indent=2)}")
    
    response = requests.post(post_url, headers=headers, json=post_body)
    
    # Debug response
    print(f"🔧 LinkedIn UGC Post Response:")
    print(f"   Status: {response.status_code}")
    print(f"   Headers: {dict(response.headers)}")
    print(f"   Body: {response.text}")
    
    response.raise_for_status()
    
    # Handle empty response body (common with LinkedIn API)
    if response.status_code == 201 and not response.text.strip():
        # Success with empty body - extract post ID from Location header
        location_header = response.headers.get('Location', '')
        if location_header:
            # Extract post ID from Location header
            post_id = location_header.split('/')[-1]
            return {"id": post_id, "status": "created"}
        else:
            # Fallback for successful creation without Location header
            return {"id": "unknown", "status": "created"}
    
    # Try to parse JSON response if available
    try:
        return response.json()
    except ValueError:
        # If JSON parsing fails, return basic success info
        return {"id": "unknown", "status": "created", "response_text": response.text}


def update_post(access_token: str, post_id: str, update_data: Dict) -> Dict:
    """
    Update an existing LinkedIn post using the appropriate API based on post ID format.
    
    Args:
        access_token: LinkedIn access token
        post_id: ID of the post to update
        update_data: Updated post content
    
    Returns:
        Updated post response
    """
    # Detect which API to use based on post ID format
    if post_id.startswith("urn:li:share:"):
        # This is a Posts API post ID, use Posts API for update
        print(f"🔧 Detected Posts API post ID: {post_id}")
        
        # Try to verify ownership, but don't fail if verification fails
        # The user might have created this post through our system
        ownership_verified = verify_post_ownership(access_token, post_id)
        
        if not ownership_verified:
            print(f"⚠️ Ownership verification failed, but attempting update anyway...")
            print(f"⚠️ This might work if the post was created through our system")
        
        return update_post_modern(access_token, post_id, update_data)
    elif post_id.startswith("urn:li:activity:"):
        # Activity URNs are read-only and cannot be updated
        error_msg = (
            f"Cannot update LinkedIn post with URN: {post_id}\n"
            f"Activity URNs (urn:li:activity:...) are read-only and represent LinkedIn's internal feed format.\n"
            f"These posts cannot be updated or deleted via the API.\n"
            f"To update a post, you need a share URN (urn:li:share:...) from a post created via the API."
        )
        print(f"❌ {error_msg}")
        raise Exception(error_msg)
    else:
        # This is a UGC Posts API post ID, use UGC Posts API for update
        print(f"🔧 Detected UGC Posts API post ID: {post_id}")
        return update_post_ugc(access_token, post_id, update_data)


def update_post_modern(access_token: str, post_id: str, update_data: Dict) -> Dict:
    """
    Update a LinkedIn post using the modern Posts API with PARTIAL_UPDATE method.
    
    Args:
        access_token: LinkedIn access token
        post_id: ID of the post to update
        update_data: Updated post content
    
    Returns:
        Updated post response
    """
    # URL encode the URN for the path
    import urllib.parse
    encoded_post_id = urllib.parse.quote(post_id, safe='')
    post_url = f"https://api.linkedin.com/rest/posts/{encoded_post_id}"
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'LinkedIn-Version': '202502',
        'X-RestLi-Protocol-Version': '2.0.0',
        'X-RestLi-Method': 'PARTIAL_UPDATE',
        'Content-Type': 'application/json'
    }
    
    # Build update body using LinkedIn's patch format
    patch_operations = {}
    
    if 'text' in update_data:
        patch_operations["commentary"] = update_data['text']
    
    # LinkedIn only allows editing certain fields via PARTIAL_UPDATE
    # visibility and content assets cannot be changed via update
    update_body = {
        "patch": {
            "$set": patch_operations
        }
    }
    
    print(f"🔧 Updating post using Posts API PARTIAL_UPDATE: {post_url}")
    print(f"🔧 Update body: {json.dumps(update_body, indent=2)}")
    
    # Use POST with PARTIAL_UPDATE method, not PUT
    response = requests.post(post_url, headers=headers, json=update_body)
    
    print(f"🔧 Posts API Update Response:")
    print(f"   Status: {response.status_code}")
    print(f"   Headers: {dict(response.headers)}")
    print(f"   Body: {response.text}")
    
    # Handle specific error cases
    if response.status_code == 403:
        print(f"❌ 403 Forbidden - User doesn't have permission to edit this post")
        print(f"❌ This could be due to:")
        print(f"   - Post was created by a different user/account")
        print(f"   - Post is from an organization page you don't admin")
        print(f"   - Access token doesn't have the right scope")
        raise Exception("403 Forbidden: User doesn't have permission to edit this post")
    elif response.status_code == 404:
        print(f"❌ 404 Not Found - Post doesn't exist or wrong URN format")
        raise Exception("404 Not Found: Post doesn't exist or wrong URN format")
    
    response.raise_for_status()
    
    # Handle empty response body
    if response.status_code == 200 and not response.text.strip():
        return {"id": post_id, "status": "updated"}
    
    try:
        return response.json()
    except ValueError:
        return {"id": post_id, "status": "updated", "response_text": response.text}


def explain_urn_types():
    """
    Explain the different LinkedIn URN types and their capabilities.
    """
    explanation = """
🔍 LinkedIn URN Types Explained:

1. 📝 urn:li:share:... (Posts API)
   ✅ CAN: Create, Update, Delete
   ✅ CAN: Add media, change visibility
   ✅ USE: Modern Posts API (/rest/posts)
   📍 Source: Posts created via LinkedIn API

2. 📋 urn:li:activity:... (Activity Feed)
   ❌ CANNOT: Update or Delete
   ❌ CANNOT: Modify content or media
   ✅ CAN: View, Like, Comment, Share
   📍 Source: LinkedIn's internal activity feed
   📍 Note: These are read-only posts

3. 📄 urn:li:ugcPost:... (UGC Posts API)
   ✅ CAN: Create, Update, Delete
   ✅ CAN: Add media, change visibility
   ✅ USE: Legacy UGC Posts API (/v2/ugcPosts)
   📍 Source: Posts created via legacy API

💡 To Update/Delete Posts:
   - Use URNs starting with 'urn:li:share:' or 'urn:li:ugcPost:'
   - Avoid 'urn:li:activity:' URNs (they're read-only)
   - Create new posts via API to get editable URNs
    """
    return explanation


def verify_post_ownership(access_token: str, post_id: str) -> bool:
    """
    Verify that the current user has ownership/access to edit a post.
    
    Args:
        access_token: LinkedIn access token
        post_id: ID of the post to verify
    
    Returns:
        True if user can edit the post, False otherwise
    """
    # URL encode the URN for the path
    import urllib.parse
    encoded_post_id = urllib.parse.quote(post_id, safe='')
    
    # Try different view contexts to check access
    view_contexts = [
        "AUTHOR",           # Check if user is the author
        "MEMBER",           # Check if user is a member (for org posts)
        "PUBLIC"            # Check if post is publicly accessible
    ]
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'LinkedIn-Version': '202502',
        'X-RestLi-Protocol-Version': '2.0.0'
    }
    
    print(f"🔍 Verifying post ownership for: {post_id}")
    
    # For activity URNs, we might need to try a different endpoint
    if post_id.startswith("urn:li:activity:"):
        print(f"🔍 Activity URN detected - trying alternative verification methods")
        
        # Try the activity endpoint first
        activity_url = f"https://api.linkedin.com/rest/activities/{encoded_post_id}"
        try:
            response = requests.get(activity_url, headers=headers)
            if response.status_code == 200:
                print(f"✅ Activity access verified via activities endpoint")
                return True
        except Exception as e:
            print(f"⚠️ Activity endpoint failed: {str(e)}")
    
    # Try the standard posts endpoint
    for context in view_contexts:
        verify_url = f"https://api.linkedin.com/rest/posts/{encoded_post_id}?viewContext={context}"
        print(f"🔍 Trying viewContext: {context}")
        
        try:
            response = requests.get(verify_url, headers=headers)
            
            if response.status_code == 200:
                print(f"✅ Post access verified with {context} context")
                return True
            elif response.status_code == 403:
                print(f"⚠️ Access denied with {context} context - trying next...")
                continue
            elif response.status_code == 404:
                print(f"❌ Post not found with {context} context")
                continue
            else:
                print(f"⚠️ Unexpected response {response.status_code} with {context} context")
                continue
                
        except Exception as e:
            print(f"❌ Error with {context} context: {str(e)}")
            continue
    
    # If we get here, none of the view contexts worked
    print(f"❌ Post ownership verification failed - user cannot access this post")
    return False


def update_post_ugc(access_token: str, post_id: str, update_data: Dict) -> Dict:
    """
    Update a LinkedIn post using the UGC Posts API.
    
    Args:
        access_token: LinkedIn access token
        post_id: ID of the post to update
        update_data: Updated post content
    
    Returns:
        Updated post response
    """
    post_url = f"https://api.linkedin.com/v2/ugcPosts/{post_id}"
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'X-Restli-Protocol-Version': '2.0.0',
        'Content-Type': 'application/json'
    }
    
    # Build update body with only provided fields
    update_body = {}
    
    if 'text' in update_data:
        update_body["specificContent"] = {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {
                    "text": update_data['text']
                }
            }
        }
    
    if 'visibility' in update_data:
        update_body["visibility"] = {
            "com.linkedin.ugc.MemberNetworkVisibility": update_data['visibility']
        }
    
    print(f"🔧 Updating post using UGC Posts API: {post_url}")
    print(f"🔧 Update body: {json.dumps(update_body, indent=2)}")
    
    response = requests.put(post_url, headers=headers, json=update_body)
    
    print(f"🔧 UGC Posts API Update Response:")
    print(f"   Status: {response.status_code}")
    print(f"   Headers: {dict(response.headers)}")
    print(f"   Body: {response.text}")
    
    response.raise_for_status()
    
    try:
        return response.json()
    except ValueError:
        return {"id": post_id, "status": "updated", "response_text": response.text}


def delete_post(access_token: str, post_id: str) -> bool:
    """
    Delete a LinkedIn post using the appropriate API based on post ID format.
    
    Args:
        access_token: LinkedIn access token
        post_id: ID of the post to delete
    
    Returns:
        True if successful
    """
    # Detect which API to use based on post ID format
    if post_id.startswith("urn:li:share:"):
        # This is a Posts API post ID, use Posts API for delete
        return delete_post_modern(access_token, post_id)
    elif post_id.startswith("urn:li:activity:"):
        # Activity URNs are read-only and cannot be deleted
        error_msg = (
            f"Cannot delete LinkedIn post with URN: {post_id}\n"
            f"Activity URNs (urn:li:activity:...) are read-only and represent LinkedIn's internal feed format.\n"
            f"These posts cannot be updated or deleted via the API.\n"
            f"To delete a post, you need a share URN (urn:li:share:...) from a post created via the API."
        )
        print(f"❌ {error_msg}")
        raise Exception(error_msg)
    else:
        # This is a UGC Posts API post ID, use UGC Posts API for delete
        return delete_post_ugc(access_token, post_id)


def delete_post_modern(access_token: str, post_id: str) -> bool:
    """
    Delete a LinkedIn post using the modern Posts API.
    
    Args:
        access_token: LinkedIn access token
        post_id: ID of the post to delete
    
    Returns:
        True if successful
    """
    # URL encode the URN for the path
    import urllib.parse
    encoded_post_id = urllib.parse.quote(post_id, safe='')
    post_url = f"https://api.linkedin.com/rest/posts/{encoded_post_id}"
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'LinkedIn-Version': '202502',
        'X-RestLi-Protocol-Version': '2.0.0'
    }
    
    print(f"🔧 Deleting post using Posts API: {post_url}")
    print(f"🔧 Encoded post ID: {post_id} -> {encoded_post_id}")
    
    response = requests.delete(post_url, headers=headers)
    
    print(f"🔧 Posts API Delete Response:")
    print(f"   Status: {response.status_code}")
    print(f"   Headers: {dict(response.headers)}")
    print(f"   Body: {response.text}")
    
    # Handle specific error cases
    if response.status_code == 422:
        print(f"❌ 422 Unprocessable Content - Post cannot be deleted")
        print(f"❌ This could be due to:")
        print(f"   - Post is already deleted")
        print(f"   - Post is from an organization page")
        print(f"   - Post has engagement (likes, comments, shares)")
        print(f"   - Post is older than allowed deletion window")
        raise Exception("422 Unprocessable Content: Post cannot be deleted")
    elif response.status_code == 403:
        print(f"❌ 403 Forbidden - User doesn't have permission to delete this post")
        raise Exception("403 Forbidden: User doesn't have permission to delete this post")
    elif response.status_code == 404:
        print(f"❌ 404 Not Found - Post doesn't exist or wrong URN format")
        raise Exception("404 Not Found: Post doesn't exist or wrong URN format")
    
    response.raise_for_status()
    
    return True


def delete_post_ugc(access_token: str, post_id: str) -> bool:
    """
    Delete a LinkedIn post using the UGC Posts API.
    
    Args:
        access_token: LinkedIn access token
        post_id: ID of the post to delete
    
    Returns:
        True if successful
    """
    post_url = f"https://api.linkedin.com/v2/ugcPosts/{post_id}"
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'X-Restli-Protocol-Version': '2.0.0'
    }
    
    print(f"🔧 Deleting post using UGC Posts API: {post_url}")
    
    response = requests.delete(post_url, headers=headers)
    
    print(f"🔧 UGC Posts API Delete Response:")
    print(f"   Status: {response.status_code}")
    print(f"   Headers: {dict(response.headers)}")
    
    response.raise_for_status()
    
    return True


def list_posts(access_token: str, author_id: str = None, count: int = 20) -> List[Dict]:
    """
    List LinkedIn posts for the authenticated user.
    
    Args:
        access_token: LinkedIn access token
        author_id: LinkedIn user ID (optional, defaults to current user)
        count: Number of posts to retrieve
    
    Returns:
        List of posts
    """
    # LinkedIn doesn't have a direct endpoint to list posts by author
    # But we can try to get posts from the user's feed or profile
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'LinkedIn-Version': '202502',
        'X-RestLi-Protocol-Version': '2.0.0'
    }
    
    posts = []
    
    try:
        # Try to use LinkedIn's Posts API to list posts by the authenticated member
        # This requires r_member_social scope and only works for the token owner's posts
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'LinkedIn-Version': '202502',
            'X-RestLi-Protocol-Version': '2.0.0',
            'X-RestLi-Method': 'FINDER'
        }
        
        # Build the author URN
        author_urn = f"urn:li:person:{author_id}"
        
        # LinkedIn Posts API parameters
        params = {
            "q": "author",
            "author": author_urn,
            "count": min(count, 20),  # LinkedIn max is 20
            "sortBy": "LAST_MODIFIED"
        }
        
        print(f"🔍 Attempting to list posts for author: {author_urn}")
        print(f"🔍 Using LinkedIn Posts API: /rest/posts with params: {params}")
        
        response = requests.get(
            "https://api.linkedin.com/rest/posts",
            headers=headers,
            params=params
        )
        
        print(f"📡 LinkedIn Posts API Response: {response.status_code}")
        
        if response.status_code == 200:
            # Success! We got posts from the authenticated member
            posts_data = response.json()
            print(f"✅ Successfully retrieved posts from LinkedIn Posts API")
            
            if 'elements' in posts_data and posts_data['elements']:
                for post in posts_data['elements']:
                    posts.append({
                        "id": post.get('id', 'unknown'),
                        "type": "post",
                        "message": post.get('commentary', {}).get('text', 'No text content'),
                        "details": f"Post URN: {post.get('id')} | Created: {post.get('created')} | Status: {post.get('lifecycleState')}",
                        "created_at": post.get('created'),
                        "content": post.get('content'),
                        "error": False
                    })
            else:
                posts.append({
                    "id": f"urn:li:person:{author_id}",
                    "type": "info",
                    "message": "No posts found for this author",
                    "details": "The author may not have any published posts, or all posts are private",
                    "created_at": None,
                    "content": None,
                    "error": False
                })
                
        elif response.status_code == 403:
            # Missing required scope or insufficient permissions
            print(f"❌ 403 Forbidden: Missing r_member_social scope or insufficient permissions")
            
            posts.append({
                "id": f"urn:li:person:{author_id}",
                "type": "info",
                "message": "LinkedIn API requires r_member_social scope to list posts",
                "details": "Your current token has w_member_social (for posting) but needs r_member_social (for reading posts). Contact your LinkedIn app administrator to request this scope.",
                "created_at": None,
                "content": None,
                "error": False
            })
            
            posts.append({
                "id": f"urn:li:person:{author_id}",
                "type": "info",
                "message": "Alternative: You can still create, update, and delete posts",
                "details": "The w_member_social scope allows you to post content, but not read existing posts from the API",
                "created_at": None,
                "content": None,
                "error": False
            })
            
        elif response.status_code == 401:
            # Unauthorized - token expired or invalid
            print(f"❌ 401 Unauthorized: Token may be expired or invalid")
            posts.append({
                "id": "error",
                "type": "error",
                "message": "LinkedIn access token is invalid or expired",
                "details": "Please reconnect your LinkedIn account to refresh the access token",
                "created_at": None,
                "content": None,
                "error": True
            })
            
        else:
            # Other error
            print(f"❌ Unexpected response: {response.status_code} - {response.text}")
            posts.append({
                "id": "error",
                "type": "error",
                "message": f"LinkedIn API returned unexpected status: {response.status_code}",
                "details": f"Response: {response.text[:200]}...",
                "created_at": None,
                "content": None,
                "error": True
            })
            
    except Exception as e:
        print(f"❌ Error in list_posts: {str(e)}")
        posts.append({
            "id": "error",
            "type": "error",
            "message": f"Error processing posts request: {str(e)}",
            "error": True
        })
    
    return posts


def get_post_analytics(access_token: str, post_id: str) -> Dict:
    """
    Get analytics for a LinkedIn post.
    
    Args:
        access_token: LinkedIn access token
        post_id: ID of the post
    
    Returns:
        Post analytics data
    """
    # LinkedIn analytics require specific permissions and endpoints
    # This would need to be implemented based on available LinkedIn API endpoints
    
    return {
        "post_id": post_id,
        "analytics": "Not implemented - requires LinkedIn Analytics API access"
    }


def upload_image(access_token: str, image_file: bytes, filename: str, description: str = "", profile_id: str = None) -> Dict:
    """
    Upload an image to LinkedIn using the Images API for proper ownership.
    
    Args:
        access_token: LinkedIn access token
        image_file: Image file bytes
        filename: Name of the image file
        description: Description of the image
        profile_id: LinkedIn profile ID for the author URN
    
    Returns:
        Upload response with image URN
    """
    # Step 1: Initialize image upload using Images API
    init_url = "https://api.linkedin.com/rest/images?action=initializeUpload"
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'LinkedIn-Version': '202502',
        'X-RestLi-Protocol-Version': '2.0.0',
        'Content-Type': 'application/json'
    }
    
    # Use provided profile_id for proper ownership
    if not profile_id:
        raise ValueError("profile_id is required for image upload")
    
    owner_urn = f"urn:li:person:{profile_id}"
    
    # Initialize upload with correct owner
    init_data = {
        "initializeUploadRequest": {
            "owner": owner_urn
        }
    }
    
    print(f"🔧 Initializing image upload for owner: {owner_urn}")
    init_response = requests.post(init_url, headers=headers, json=init_data)
    init_response.raise_for_status()
    
    init_info = init_response.json()
    upload_url = init_info["value"]["uploadUrl"]
    image_urn = init_info["value"]["image"]
    
    print(f"✅ Image upload initialized: {image_urn}")
    
    # Step 2: Upload the actual image file
    upload_headers = {"Content-Type": "image/jpeg"}  # Adjust based on file type
    put_response = requests.put(upload_url, data=image_file, headers=upload_headers)
    put_response.raise_for_status()
    
    print(f"✅ Image file uploaded successfully")
    
    return {
        "asset": image_urn,  # Return image URN for use with Posts API
        "image_urn": image_urn,  # Also return as image_urn for clarity
        "status": "UPLOADED"
    }


def upload_video(access_token: str, video_file: bytes, filename: str, description: str = "", profile_id: str = None) -> Dict:
    """
    Upload a video to LinkedIn using the Videos API.
    
    Args:
        access_token: LinkedIn access token
        video_file: Video file bytes
        filename: Name of the video file
        description: Description of the video
        profile_id: LinkedIn profile ID for the author URN
    
    Returns:
        Upload response with video URN
    """
    # Step 1: Initialize video upload
    init_url = "https://api.linkedin.com/rest/videos?action=initializeUpload"
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'X-Restli-Protocol-Version': '2.0.0',
        'LinkedIn-Version': '202503',
        'Content-Type': 'application/json'
    }
    
    # Use provided profile_id instead of calling /v2/me
    if not profile_id:
        raise ValueError("profile_id is required for video upload")
    
    author_urn = f"urn:li:person:{profile_id}"
    
    # Initialize upload
    init_data = {
        "initializeUploadRequest": {
            "owner": author_urn,
            "fileSizeBytes": len(video_file),
            "uploadCaptions": False,
            "uploadThumbnail": False
        }
    }
    
    init_response = requests.post(init_url, headers=headers, json=init_data)
    init_response.raise_for_status()
    init_info = init_response.json()
    
    video_urn = init_info["value"]["video"]
    upload_url = init_info["value"]["uploadInstructions"][0]["uploadUrl"]
    upload_token = init_info["value"].get("uploadToken", "")
    
    # Step 2: Upload video parts
    upload_headers = {"Content-Type": "application/octet-stream"}
    put_response = requests.put(upload_url, data=video_file, headers=upload_headers)
    put_response.raise_for_status()
    etag = put_response.headers.get("ETag", "").strip('"')
    
    # Step 3: Finalize upload
    finalize_url = "https://api.linkedin.com/rest/videos?action=finalizeUpload"
    finalize_data = {
        "finalizeUploadRequest": {
            "uploadToken": upload_token,
            "uploadedPartIds": [etag] if etag else [],
            "video": video_urn
        }
    }
    
    finalize_response = requests.post(finalize_url, headers=headers, json=finalize_data)
    finalize_response.raise_for_status()
    
    return {
        "video_urn": video_urn,
        "status": "UPLOADED"
    }


def upload_document(access_token: str, document_file: bytes, filename: str, description: str = "", profile_id: str = None) -> Dict:
    """
    Upload a document (PDF, Word, etc.) to LinkedIn using the correct API.
    
    Args:
        access_token: LinkedIn access token
        document_file: Document file bytes
        filename: Name of the document file
        description: Description of the document
        profile_id: LinkedIn profile ID for the author URN
    
    Returns:
        Upload response with asset URN
    """
    # LinkedIn uses the Assets API for documents, but we need to ensure proper ownership
    upload_url = "https://api.linkedin.com/v2/assets?action=registerUpload"
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'X-Restli-Protocol-Version': '2.0.0',
        'Content-Type': 'application/json'
    }
    
    # Use provided profile_id for proper ownership
    if not profile_id:
        raise ValueError("profile_id is required for document upload")
    
    owner_urn = f"urn:li:person:{profile_id}"
    
    print(f"🔧 Initializing document upload for owner: {owner_urn}")
    
    # Register the upload for documents with correct ownership
    upload_data = {
        "registerUploadRequest": {
            "recipes": ["urn:li:digitalmediaRecipe:feedshare-document"],
            "owner": owner_urn,
            "serviceRelationships": [
                {
                    "relationshipType": "OWNER",
                    "identifier": "urn:li:userGeneratedContent"
                }
            ]
        }
    }
    
    # Step 1: Register the upload
    response = requests.post(upload_url, headers=headers, json=upload_data)
    response.raise_for_status()
    
    upload_info = response.json()
    asset_urn = upload_info.get("value", {}).get("asset")
    upload_url_actual = upload_info.get("value", {}).get("uploadUrl")
    
    print(f"✅ Document upload registered: {asset_urn}")
    
    if upload_url_actual and asset_urn:
        # Step 2: Upload the actual document file
        upload_headers = {"Content-Type": "application/pdf"}  # Adjust based on file type
        put_response = requests.put(upload_url_actual, data=document_file, headers=upload_headers)
        put_response.raise_for_status()
        
        print(f"✅ Document file uploaded successfully")
        
        return {
            "asset": asset_urn,
            "document_urn": asset_urn,  # Also return as document_urn for clarity
            "status": "UPLOADED"
        }
    else:
        print(f"❌ Document upload registration failed: {upload_info}")
        return {
            "asset": None,
            "status": "FAILED",
            "error": "Upload registration failed"
        }
