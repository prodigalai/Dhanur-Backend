import os
import jwt
from functools import wraps
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from services.jwt_service import verify_jwt_token
from services.permissions import has_permissions

# JWT secret key
JWT_SECRET = os.getenv("JWT_SECRET_KEY", "dhanur_super_secret_jwt_key_2024_make_it_long_and_secure")

# HTTP Bearer scheme for FastAPI
security = HTTPBearer()

def auth_required(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """FastAPI dependency for required authentication."""
    try:
        token = credentials.credentials
        payload = verify_jwt_token(token, JWT_SECRET)
        if not payload:
            raise HTTPException(status_code=401, detail="Invalid token")
        return payload
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")

def optional_auth(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """FastAPI dependency for optional authentication."""
    try:
        token = credentials.credentials
        payload = verify_jwt_token(token, JWT_SECRET)
        return payload
    except:
        return None

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """FastAPI dependency for getting current authenticated user."""
    try:
        token = credentials.credentials
        payload = verify_jwt_token(token, JWT_SECRET)
        if not payload:
            raise HTTPException(status_code=401, detail="Invalid token")
        return payload
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")

def assign_permission_score(auth_data):
    """Assign permission score to auth data."""
    if auth_data and 'entity_id' in auth_data:
        # Calculate permission score based on user's roles and permissions
        # This is a simplified version - you can enhance it based on your needs
        auth_data['permission_score'] = 100  # Default score
    return auth_data

# Legacy decorators for backward compatibility (if needed)
def auth_required_decorator(f):
    """Legacy decorator for backward compatibility."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # This is kept for any remaining legacy usage
        return f(*args, **kwargs)
    return decorated_function

def optional_auth_decorator(f):
    """Legacy decorator for backward compatibility."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # This is kept for any remaining legacy usage
        return f(*args, **kwargs)
    return decorated_function
