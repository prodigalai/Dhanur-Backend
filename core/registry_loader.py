import json
from pathlib import Path
from typing import Dict, Any

def load_youtube_permissions() -> Dict[str, Any]:
    """Load YouTube permissions configuration from registry"""
    registry_path = Path("config/platforms/registries/youtube/versions/v1/policies")
    
    # Load permissions from the permissions.json file
    permissions_file = registry_path / "permissions.json"
    if permissions_file.exists():
        try:
            with open(permissions_file, 'r') as f:
                permissions = json.load(f)
            print(f"✅ Loaded permissions from {permissions_file}")
            return permissions
        except Exception as e:
            print(f"❌ Error loading permissions from {permissions_file}: {e}")
    
    # Fallback to hardcoded permissions if file not found
    print(f"⚠️ Permissions file not found at {permissions_file}, using fallback permissions")
    
    registry_path = Path("config/platforms/registries/youtube/versions/v1/spec")
    
    # Load operations
    operations_file = registry_path / "operations.json"
    if operations_file.exists():
        with open(operations_file, 'r') as f:
            operations = json.load(f)
    else:
        operations = {"operations": {}}
    
    # Load scopes
    scopes_file = registry_path / "scopes.json"
    if scopes_file.exists():
        with open(scopes_file, 'r') as f:
            scopes = json.load(f)
    else:
        scopes = {}
    
    # Define role-based permissions (fallback)
    roles = {
        "VIEWER": {
            "scopes": ["read_only"],
            "allows": ["channels_list_mine", "channels_update"]
        },
        "UPLOADER": {
            "scopes": ["upload"],
            "allows": ["channels_list_mine", "videos_insert"]
        },
        "EDITOR": {
            "scopes": ["manage"],
            "allows": ["channels_list_mine", "videos_update", "playlists_insert", "playlistItems_insert", "channels_update"]
        },
        "ADMIN": {
            "scopes": ["manage", "upload", "force_ssl"],
            "allows": ["channels_list_mine", "videos_insert", "videos_update", "videos_delete", "playlists_insert", "playlistItems_insert", "comments_insert", "channels_update"]
        },
        "OWNER": {
            "scopes": ["manage", "upload", "force_ssl"],
            "allows": ["channels_list_mine", "videos_insert", "videos_update", "videos_delete", "playlists_insert", "playlistItems_insert", "comments_insert", "channels_update"]
        }
    }
    
    return {
        "operations": operations["operations"],
        "scopes": scopes,
        "roles": roles
    }


def load_linkedin_permissions() -> Dict[str, Any]:
    """Load LinkedIn permissions configuration from registry"""
    registry_path = Path("config/platforms/registries/linkedin/versions/v1/policies")
    
    # Load permissions from the permissions.json file
    permissions_file = registry_path / "permissions.json"
    if permissions_file.exists():
        try:
            with open(permissions_file, 'r') as f:
                permissions = json.load(f)
            print(f"✅ Loaded LinkedIn permissions from {permissions_file}")
            return permissions
        except Exception as e:
            print(f"❌ Error loading LinkedIn permissions from {permissions_file}: {e}")
    
    # Fallback to hardcoded permissions if file not found
    print(f"⚠️ LinkedIn permissions file not found at {permissions_file}, using fallback permissions")
    
    # Define role-based permissions (fallback)
    roles = {
        "VIEWER": {
            "scopes": ["read_only"],
            "allows": ["profile_read"]
        },
        "UPLOADER": {
            "scopes": ["post"],
            "allows": ["profile_read", "posts_create"]
        },
        "EDITOR": {
            "scopes": ["manage"],
            "allows": ["profile_read", "posts_create", "posts_update"]
        },
        "ADMIN": {
            "scopes": ["manage", "post", "force_ssl"],
            "allows": ["profile_read", "posts_create", "posts_update", "posts_delete", "posts_list"]
        },
        "OWNER": {
            "scopes": ["manage", "post", "force_ssl"],
            "allows": ["profile_read", "posts_create", "posts_update", "posts_delete", "posts_list"]
        }
    }
    
    return {
        "roles": roles
    }
