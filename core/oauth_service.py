from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import uuid
import json
import base64
from models.user import User
from models.brand import Brand
from models.brand_membership import BrandMembership, UserRole
from models.oauth_account import OAuthAccount
from models.youtube_connection import YoutubeConnection
from models.linkedin_connection import LinkedInConnection
from core.crypto import encrypt_token_blob, decrypt_token_blob
from core.registry_loader import load_youtube_permissions, load_linkedin_permissions

class OAuthService:
    """Service for managing OAuth connections across multiple brands and channels"""
    
    def __init__(self, db: Session):
        self.db = db
        # Load both YouTube and LinkedIn permissions
        youtube_permissions = load_youtube_permissions()
        linkedin_permissions = load_linkedin_permissions()
        
        # Merge permissions - combine operations from both platforms
        merged_roles = {}
        
        # Get all unique roles from both platforms
        all_roles = set(youtube_permissions.get("roles", {}).keys()) | set(linkedin_permissions.get("roles", {}).keys())
        
        for role in all_roles:
            youtube_role = youtube_permissions.get("roles", {}).get(role, {})
            linkedin_role = linkedin_permissions.get("roles", {}).get(role, {})
            
            # Merge allows and scopes from both platforms
            merged_roles[role] = {
                "allows": (youtube_role.get("allows", []) + linkedin_role.get("allows", [])),
                "scopes": (youtube_role.get("scopes", []) + linkedin_role.get("scopes", []))
            }
        
        self.permissions = {"roles": merged_roles}
        
        print(f"🔧 OAuthService initialized with merged permissions: {self.permissions}")
    
    def create_or_get_user(self, email: str, full_name: str = None, username: str = None) -> User:
        """Create or get existing user"""
        user = self.db.query(User).filter(User.email == email).first()
        if not user:
            user = User(
                email=email,
                full_name=full_name or email.split('@')[0],
                username=username or email.split('@')[0]
            )
            self.db.add(user)
            self.db.flush()
        return user
    
    def create_or_get_user_by_id(self, user_id: str, email: str, full_name: str = None, username: str = None) -> User:
        """Create or get existing user by ID"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            user = User(
                id=user_id,
                email=email,
                full_name=full_name or email.split('@')[0],
                username=username or email.split('@')[0]
            )
            self.db.add(user)
            self.db.flush()
        return user
    
    def create_or_get_brand(self, name: str, slug: str = None) -> Brand:
        """Create or get existing brand"""
        if not slug:
            slug = name.lower().replace(' ', '-').replace('&', 'and')
        
        brand = self.db.query(Brand).filter(Brand.slug == slug).first()
        if not brand:
            brand = Brand(name=name, slug=slug)
            self.db.add(brand)
            self.db.flush()
        return brand
    
    def create_or_get_brand_by_id(self, brand_id: str, name: str, slug: str = None) -> Brand:
        """Create or get existing brand by ID"""
        brand = self.db.query(Brand).filter(Brand.id == brand_id).first()
        if not brand:
            brand = Brand(
                id=brand_id,
                name=name,
                slug=slug or brand_id
            )
            self.db.add(brand)
            self.db.flush()
        return brand
    
    def add_user_to_brand(self, user_id, brand_id, role: UserRole = UserRole.OWNER) -> BrandMembership:
        """Add user to brand with specified role"""
        membership = self.db.query(BrandMembership).filter(
            BrandMembership.user_id == user_id,
            BrandMembership.brand_id == brand_id
        ).first()
        
        if not membership:
            membership = BrandMembership(
                user_id=user_id,
                brand_id=brand_id,
                role=role
            )
            self.db.add(membership)
            self.db.flush()
        return membership
    
    def create_oauth_account(self, user_id, provider: str, provider_user_id: str, 
                           provider_email: str = None, provider_username: str = None, provider_avatar: str = None) -> OAuthAccount:
        """Create or get OAuth account for user"""
        oauth_account = self.db.query(OAuthAccount).filter(
            OAuthAccount.user_id == user_id,
            OAuthAccount.provider == provider,
            OAuthAccount.provider_user_id == provider_user_id
        ).first()
        
        if not oauth_account:
            oauth_account = OAuthAccount(
                user_id=user_id,
                provider=provider,
                provider_user_id=provider_user_id,
                provider_email=provider_email,
                provider_username=provider_username,
                provider_avatar=provider_avatar
            )
            self.db.add(oauth_account)
            self.db.flush()
        return oauth_account
    
    def create_youtube_connection(self, brand_id, user_id, oauth_account_id, 
                                channel_data: dict, token_data: dict, scopes: List[str] = None) -> YoutubeConnection:
        """Create YouTube connection for brand"""
        # Extract channel information
        channel_id = channel_data.get('id', '')
        channel_title = channel_data.get('snippet', {}).get('title', '')
        channel_description = channel_data.get('snippet', {}).get('description', '')
        channel_avatar = channel_data.get('snippet', {}).get('thumbnails', {}).get('default', {}).get('url', '')
        subscriber_count = channel_data.get('statistics', {}).get('subscriberCount', 0)
        view_count = channel_data.get('statistics', {}).get('viewCount', 0)
        
        # Encrypt the actual token data using the new format
        token_blob = encrypt_token_blob({
            'access_token': token_data.get('access_token', ''),
            'refresh_token': token_data.get('refresh_token', ''),
            'token_uri': 'https://oauth2.googleapis.com/token',
            'client_id': token_data.get('client_id', ''),
            'client_secret': token_data.get('client_secret', ''),
            'expires_at': token_data.get('expires_at'),
            'scopes': token_data.get('scopes', [])
        })
        
        # Convert to JSON string for storage (new format)
        access_token_encrypted = json.dumps({
            "wrapped_iv": base64.b64encode(token_blob['wrapped_iv']).decode(),
            "wrapped_ct": base64.b64encode(token_blob['wrapped_ct']).decode(),
            "iv": base64.b64encode(token_blob['iv']).decode(),
            "ct": base64.b64encode(token_blob['ct']).decode(),
            "fp": base64.b64encode(token_blob['fp']).decode()
        })
        
        connection = YoutubeConnection(
            brand_id=brand_id,
            user_id=user_id,
            oauth_account_id=oauth_account_id,
            channel_id=channel_id,
            channel_title=channel_title,
            channel_description=channel_description,
            channel_avatar=channel_avatar,
            subscriber_count=subscriber_count,
            view_count=view_count,
            scopes=scopes or [],
            scope_keys=self._get_scope_keys(scopes or []),
            access_token_encrypted=access_token_encrypted
        )
        
        self.db.add(connection)
        self.db.flush()
        return connection
    
    def create_linkedin_connection(self, brand_id, user_id, oauth_account_id,
                                 profile_id: str, profile_url: str = None, first_name: str = None,
                                 last_name: str = None, headline: str = None, industry: str = None,
                                 location: str = None, access_token_encrypted: str = None) -> LinkedInConnection:
        """Create LinkedIn connection for brand"""
        connection = LinkedInConnection(
            brand_id=brand_id,
            user_id=user_id,
            oauth_account_id=oauth_account_id,
            profile_id=profile_id,
            profile_url=profile_url,
            first_name=first_name,
            last_name=last_name,
            headline=headline,
            industry=industry,
            location=location,
            access_token_encrypted=access_token_encrypted
        )
        
        self.db.add(connection)
        self.db.flush()
        return connection
    
    def get_brand_youtube_connections(self, brand_id, user_id) -> List[Dict]:
        """Get YouTube connections for a brand with user role information"""
        connections = self.db.query(YoutubeConnection, BrandMembership.role).join(
            BrandMembership,
            (YoutubeConnection.user_id == BrandMembership.user_id) & 
            (YoutubeConnection.brand_id == BrandMembership.brand_id)
        ).filter(
            YoutubeConnection.brand_id == brand_id,
            YoutubeConnection.user_id == user_id,
            YoutubeConnection.is_active == True,
            YoutubeConnection.revoked_at == None
        ).all()
        
        result = []
        for connection, role in connections:
            connection_dict = {
                'id': connection.id,
                'channel_id': connection.channel_id,
                'channel_title': connection.channel_title,
                'channel_description': connection.channel_description,
                'channel_avatar': connection.channel_avatar,
                'subscriber_count': connection.subscriber_count,
                'view_count': connection.view_count,
                'scopes': connection.scopes,
                'scope_keys': connection.scope_keys,
                'is_active': connection.is_active,
                'is_verified': connection.is_verified,
                'last_used_at': connection.last_used_at,
                'created_at': connection.created_at,
                'role': role.value if role else None
            }
            result.append(connection_dict)
        
        return result
    
    def get_brand_linkedin_connections(self, brand_id, user_id) -> List[Dict]:
        """Get LinkedIn connections for a brand with user role information"""
        connections = self.db.query(LinkedInConnection, BrandMembership.role).join(
            BrandMembership,
            (LinkedInConnection.user_id == BrandMembership.user_id) & 
            (LinkedInConnection.brand_id == BrandMembership.brand_id)
        ).filter(
            LinkedInConnection.brand_id == brand_id,
            LinkedInConnection.user_id == user_id,
            LinkedInConnection.is_active == True,
            LinkedInConnection.revoked_at == None
        ).all()
        
        result = []
        for connection, role in connections:
            connection_dict = {
                'id': connection.id,
                'profile_id': connection.profile_id,
                'profile_url': connection.profile_url,
                'first_name': connection.first_name,
                'last_name': connection.last_name,
                'headline': connection.headline,
                'industry': connection.industry,
                'location': connection.location,
                'is_active': connection.is_active,
                'is_verified': connection.is_verified,
                'last_used_at': connection.last_used_at,
                'created_at': connection.created_at,
                'role': role.value if role else None
            }
            result.append(connection_dict)
        
        return result
    
    def get_user_youtube_connections(self, user_id) -> List[YoutubeConnection]:
        """Get all YouTube connections for a user across all brands"""
        return self.db.query(YoutubeConnection).filter(
            YoutubeConnection.user_id == user_id,
            YoutubeConnection.is_active == True,
            YoutubeConnection.revoked_at == None
        ).all()
    
    def get_user_linkedin_connections(self, user_id) -> List[LinkedInConnection]:
        """Get all LinkedIn connections for a user across all brands"""
        return self.db.query(LinkedInConnection).filter(
            LinkedInConnection.user_id == user_id,
            LinkedInConnection.is_active == True,
            LinkedInConnection.revoked_at == None
        ).all()
    
    def get_youtube_connection(self, connection_id) -> Optional[YoutubeConnection]:
        """Get specific YouTube connection by ID"""
        return self.db.query(YoutubeConnection).filter(
            YoutubeConnection.id == connection_id,
            YoutubeConnection.is_active == True,
            YoutubeConnection.revoked_at == None
        ).first()
    
    def get_linkedin_connection(self, connection_id) -> Optional[LinkedInConnection]:
        """Get specific LinkedIn connection by ID"""
        return self.db.query(LinkedInConnection).filter(
            LinkedInConnection.id == connection_id,
            LinkedInConnection.is_active == True,
            LinkedInConnection.revoked_at == None
        ).first()
    
    def refresh_youtube_token(self, connection_id) -> bool:
        """Refresh YouTube OAuth token"""
        connection = self.get_youtube_connection(connection_id)
        if not connection:
            return False
        
        try:
            # Decrypt current token
            current_token = decrypt_token_blob({
                'wrapped_iv': connection.token_wrapped_iv,
                'wrapped_ct': connection.token_wrapped_ct,
                'iv': connection.token_iv,
                'ct': connection.token_ct,
                'fp': connection.token_fp
            })
            
            # Check if refresh is needed
            if not current_token.get('refresh_token'):
                return False
            
            # TODO: Implement token refresh logic using YouTube API
            # For now, just update the last_used timestamp
            connection.last_used_at = datetime.now(timezone.utc)
            self.db.flush()
            return True
            
        except Exception as e:
            print(f"Token refresh failed: {e}")
            return False
    
    def revoke_youtube_connection(self, connection_id) -> bool:
        """Revoke YouTube connection"""
        connection = self.get_youtube_connection(connection_id)
        if not connection:
            return False
        
        connection.revoked_at = datetime.now(timezone.utc)
        connection.is_active = False
        self.db.flush()
        return True
    
    def revoke_linkedin_connection(self, connection_id) -> bool:
        """Revoke LinkedIn connection"""
        connection = self.get_linkedin_connection(connection_id)
        if not connection:
            return False
        
        connection.revoked_at = datetime.now(timezone.utc)
        connection.is_active = False
        self.db.flush()
        return True
    
    def _get_scope_keys(self, scopes: List[str]) -> List[str]:
        """Convert full scope URLs to scope keys"""
        scope_keys = []
        for scope in scopes:
            if 'youtube.readonly' in scope:
                scope_keys.append('read_only')
            elif 'youtube.upload' in scope:
                scope_keys.append('upload')
            elif 'youtube' in scope and 'upload' not in scope:
                scope_keys.append('manage')
            elif 'youtube.force-ssl' in scope:
                scope_keys.append('force_ssl')
        return list(set(scope_keys))  # Remove duplicates
    
    def check_user_permission(self, user_id, brand_id, 
                            operation: str) -> bool:
        """Check if user has permission for specific operation on brand"""
        print(f"🔍 Checking permission: user_id={user_id}, brand_id={brand_id}, operation={operation}")
        
        membership = self.db.query(BrandMembership).filter(
            BrandMembership.user_id == user_id,
            BrandMembership.brand_id == brand_id,
            BrandMembership.is_active == True
        ).first()
        
        if not membership:
            print(f"❌ No membership found for user {user_id} in brand {brand_id}")
            return False
        
        print(f"✅ Found membership with role: {membership.role.value}")
        
        # Get role permissions
        role_permissions = self.permissions['roles'].get(membership.role.value, {})
        print(f"📋 Role permissions: {role_permissions}")
        
        allowed_operations = role_permissions.get('allows', [])
        print(f"🔓 Allowed operations: {allowed_operations}")
        
        has_permission = operation in allowed_operations
        print(f"🎯 Operation '{operation}' allowed: {has_permission}")
        
        return has_permission
    
    def get_user_brand_membership(self, user_id, brand_id) -> Optional[BrandMembership]:
        """Get user's membership in a specific brand"""
        return self.db.query(BrandMembership).filter(
            BrandMembership.user_id == user_id,
            BrandMembership.brand_id == brand_id,
            BrandMembership.is_active == True
        ).first()
