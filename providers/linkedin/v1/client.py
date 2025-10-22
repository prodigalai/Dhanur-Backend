from typing import Dict


def linkedin_client(token_data: Dict):
    """
    Create a LinkedIn client instance.
    
    Args:
        token_data: Dictionary containing access_token and other token info
    
    Returns:
        LinkedIn client object with methods for API operations
    """
    # Extract access token from token data
    access_token = token_data.get('access_token')
    if not access_token:
        raise ValueError("No access token found in token data")
    
    class LinkedInClient:
        def __init__(self, access_token: str):
            self.access_token = access_token
        
        def get_profile(self):
            """Get user profile"""
            from .oauth import get_user_profile
            return get_user_profile(self.access_token)
        
        def create_post(self, post_data: Dict):
            """Create a new post"""
            from .ops import create_post
            return create_post(self.access_token, post_data)
        
        def update_post(self, post_id: str, update_data: Dict):
            """Update an existing post"""
            from .ops import update_post
            return update_post(self.access_token, post_id, update_data)
        
        def delete_post(self, post_id: str):
            """Delete a post"""
            from .ops import delete_post
            return delete_post(self.access_token, post_id)
        
        def list_posts(self, author_id: str, count: int = 10):
            """List posts for a user"""
            from .ops import list_posts
            return list_posts(self.access_token, author_id, count)
        
        def get_post_analytics(self, post_id: str):
            """Get analytics for a post"""
            from .ops import get_post_analytics
            return get_post_analytics(self.access_token, post_id)
        
        def find_real_post_urn(self, author_id: str, activity_urn: str = None):
            """Find the real post URN (share/ugcPost) for deletion"""
            from .ops import find_real_post_urn
            return find_real_post_urn(self.access_token, author_id, activity_urn)
        
        def upload_image(self, image_file: bytes, filename: str, description: str = "", profile_id: str = None):
            """Upload an image for use in posts"""
            from .ops import upload_image
            return upload_image(self.access_token, image_file, filename, description, profile_id)
        
        def upload_video(self, video_file: bytes, filename: str, description: str = "", profile_id: str = None):
            """Upload a video for use in posts using LinkedIn Videos API"""
            from .ops import upload_video
            return upload_video(self.access_token, video_file, filename, description, profile_id)
        
        def upload_document(self, document_file: bytes, filename: str, description: str = "", profile_id: str = None):
            """Upload a document (PDF, Word, etc.) for use in posts"""
            from .ops import upload_document
            return upload_document(self.access_token, document_file, filename, description, profile_id)
    
    return LinkedInClient(access_token)
