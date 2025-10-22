import os
import jwt
import datetime
from typing import Optional, Dict, Any

def get_jwt_secret():
    """Get JWT secret from environment variables."""
    secret = os.getenv("JWT_SECRET_KEY", "dhanur_super_secret_jwt_key_2024_make_it_long_and_secure")
    return secret

def create_jwt_token(data: Dict[str, Any], secret_key: str, expires_delta: Optional[datetime.timedelta] = None) -> str:
    """Create a JWT token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.datetime.now(datetime.timezone.utc) + expires_delta
    else:
        expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=7)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm="HS256")
    return encoded_jwt

def generate_jwt(entity_id, email: str, user_id = None, 
                entity_type: str = None, purpose: str = "authentication") -> str:
    """Generate JWT token with custom claims for backward compatibility."""
    jwt_secret = get_jwt_secret()
    
    # Handle both string and integer IDs
    if isinstance(entity_id, str):
        entity_id = entity_id
    if isinstance(user_id, str):
        user_id = user_id
    elif user_id is None:
        user_id = entity_id
    
    claims = {
        "entity_id": entity_id,
        "email": email,
        "user_id": user_id,
        "entity_type": entity_type,
        "purpose": purpose
    }
    
    return create_jwt_token(claims, jwt_secret)

def verify_jwt_token(token: str, secret_key: str) -> Optional[Dict[str, Any]]:
    """Verify and decode a JWT token."""
    try:
        payload = jwt.decode(token, secret_key, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def validate_jwt(token_string: str) -> Dict[str, Any]:
    """Legacy function for backward compatibility."""
    # This is kept for any remaining legacy usage
    # You should use verify_jwt_token instead
    secret_key = "dhanur_super_secret_jwt_key_2024_make_it_long_and_secure"
    return verify_jwt_token(token_string, secret_key) or {}

def create_access_token(data: Dict[str, Any], secret_key: str, expires_delta: Optional[datetime.timedelta] = None) -> str:
    """Create an access token."""
    return create_jwt_token(data, secret_key, expires_delta)

class JWTService:
    """JWT service for token management."""
    
    def __init__(self, secret_key: Optional[str] = None):
        self.secret_key = secret_key or get_jwt_secret()
    
    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[datetime.timedelta] = None) -> str:
        """Create an access token."""
        return create_jwt_token(data, self.secret_key, expires_delta)
    
    def create_refresh_token(self, data: Dict[str, Any], expires_delta: Optional[datetime.timedelta] = None) -> str:
        """Create a refresh token."""
        return create_refresh_token(data, self.secret_key, expires_delta)
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode a JWT token."""
        return verify_jwt_token(token, self.secret_key)

def create_refresh_token(data: Dict[str, Any], secret_key: str, expires_delta: Optional[datetime.timedelta] = None) -> str:
    """Create a refresh token."""
    if expires_delta is None:
        expires_delta = datetime.timedelta(days=30)
    return create_jwt_token(data, secret_key, expires_delta)
