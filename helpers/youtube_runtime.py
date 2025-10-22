"""
YouTube Runtime Helper Functions
Handles token decryption and API calls for YouTube operations
"""

from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from core.crypto import decrypt_token_blob
from models.youtube_connection import YoutubeConnection
from providers.youtube.v1.ops import (
    videos_insert, videos_update, videos_delete,
    playlists_insert, playlist_items_insert,
    channels_list_mine
)

def load_token_for_connection(db: Session, connection_id: str) -> Dict:
    """Load and decrypt token for a specific YouTube connection"""
    row = db.query(YoutubeConnection).filter(
        YoutubeConnection.id == connection_id,
        YoutubeConnection.is_active == True,
        YoutubeConnection.revoked_at == None
    ).first()
    
    if not row:
        raise RuntimeError("Connection not found or revoked")
    
    # Decrypt the token blob
    blob = {
        "wrapped_iv": row.token_wrapped_iv,
        "wrapped_ct": row.token_wrapped_ct,
        "iv": row.token_iv,
        "ct": row.token_ct,
        "fp": row.token_fp
    }
    
    return decrypt_token_blob(blob)

def upload_video(db: Session, connection_id: str, video_path: str, 
                title: str, description: str = "", tags: Optional[List[str]] = None, 
                privacy_status: str = "unlisted") -> Dict:
    """Upload a video using a specific connection"""
    token = load_token_for_connection(db, connection_id)
    
    # Update last used timestamp
    connection = db.query(YoutubeConnection).filter(YoutubeConnection.id == connection_id).first()
    if connection:
        from datetime import datetime, timezone
        connection.last_used_at = datetime.now(timezone.utc)
        db.flush()
    
    return videos_insert(
        token_blob=token,
        video_path=video_path,
        title=title,
        description=description,
        tags=tags or [],
        privacy_status=privacy_status,
        role="uploader"
    )

def update_video(db: Session, connection_id: str, video_id: str,
                title: Optional[str] = None, description: Optional[str] = None,
                tags: Optional[List[str]] = None, privacy_status: Optional[str] = None) -> Dict:
    """Update video metadata using a specific connection"""
    token = load_token_for_connection(db, connection_id)
    
    # Update last used timestamp
    connection = db.query(YoutubeConnection).filter(YoutubeConnection.id == connection_id).first()
    if connection:
        from datetime import datetime, timezone
        connection.last_used_at = datetime.now(timezone.utc)
        db.flush()
    
    return videos_update(
        token_blob=token,
        video_id=video_id,
        title=title,
        description=description,
        tags=tags,
        privacy_status=privacy_status,
        role="editor"
    )

def delete_video(db: Session, connection_id: str, video_id: str) -> Dict:
    """Delete a video using a specific connection"""
    token = load_token_for_connection(db, connection_id)
    
    # Update last used timestamp
    connection = db.query(YoutubeConnection).filter(YoutubeConnection.id == connection_id).first()
    if connection:
        from datetime import datetime, timezone
        connection.last_used_at = datetime.now(timezone.utc)
        db.flush()
    
    return videos_delete(
        token_blob=token,
        video_id=video_id,
        role="admin"
    )

def create_playlist(db: Session, connection_id: str, title: str,
                   description: str = "", privacy_status: str = "unlisted") -> Dict:
    """Create a playlist using a specific connection"""
    token = load_token_for_connection(db, connection_id)
    
    # Update last used timestamp
    connection = db.query(YoutubeConnection).filter(YoutubeConnection.id == connection_id).first()
    if connection:
        from datetime import datetime, timezone
        connection.last_used_at = datetime.now(timezone.utc)
        db.flush()
    
    return playlists_insert(
        token_blob=token,
        title=title,
        description=description,
        privacy_status=privacy_status,
        role="editor"
    )

def add_video_to_playlist(db: Session, connection_id: str, playlist_id: str, video_id: str) -> Dict:
    """Add a video to a playlist using a specific connection"""
    token = load_token_for_connection(db, connection_id)
    
    # Update last used timestamp
    connection = db.query(YoutubeConnection).filter(YoutubeConnection.id == connection_id).first()
    if connection:
        from datetime import datetime, timezone
        connection.last_used_at = datetime.now(timezone.utc)
        db.flush()
    
    return playlist_items_insert(
        token_blob=token,
        playlist_id=playlist_id,
        video_id=video_id,
        role="editor"
    )

def get_channel_info(db: Session, connection_id: str) -> Dict:
    """Get channel information using a specific connection"""
    token = load_token_for_connection(db, connection_id)
    
    # Update last used timestamp
    connection = db.query(YoutubeConnection).filter(YoutubeConnection.id == connection_id).first()
    if connection:
        from datetime import datetime, timezone
        connection.last_used_at = datetime.now(timezone.utc)
        db.flush()
    
    return channels_list_mine(token_blob=token, role="viewer")

def validate_connection_permissions(db: Session, connection_id: str, required_operation: str) -> bool:
    """Validate that a connection has the required permissions for an operation"""
    connection = db.query(YoutubeConnection).filter(
        YoutubeConnection.id == connection_id,
        YoutubeConnection.is_active == True,
        YoutubeConnection.revoked_at == None
    ).first()
    
    if not connection:
        return False
    
    # Check if the connection has the required scope for the operation
    operation_scopes = {
        "videos_insert": ["upload"],
        "videos_update": ["manage"],
        "videos_delete": ["manage"],
        "playlists_insert": ["manage"],
        "playlistItems_insert": ["manage"],
        "channels_list_mine": ["read_only"]
    }
    
    required_scopes = operation_scopes.get(required_operation, [])
    
    # Check if connection has any of the required scopes
    for scope in required_scopes:
        if scope in connection.scope_keys:
            return True
    
    return False
