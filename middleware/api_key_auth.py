from functools import wraps
from fastapi import Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from typing import Optional, Callable, Any
import hashlib
from datetime import datetime

def api_key_auth(f: Callable) -> Callable:
    """Decorator to enforce API key-based authentication."""
    @wraps(f)
    async def decorated_function(*args, **kwargs):
        # Get request from kwargs or create a mock request
        request = None
        for arg in args:
            if isinstance(arg, Request):
                request = arg
                break
        
        if not request:
            # If no request found in args, this decorator needs to be used differently
            raise HTTPException(status_code=500, detail="Request object not found")
        
        raw_key = request.headers.get('X-API-Key')
        if not raw_key:
            raise HTTPException(status_code=401, detail="Missing API key")
        
        # Hash the raw key
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        
        # Get database session
        # Database session function - implement as needed for production
def get_db_session():
    """Get database session."""
    return None
        db_session = get_db_session()
        
        if not db_session:
            raise HTTPException(status_code=500, detail="Database connection failed")
        
        try:
            # Load key
            from models.api_key_models import APIKey
            key = db_session.query(APIKey).filter(
                APIKey.key_hash == key_hash,
                APIKey.is_active == True
            ).first()
            
            if not key:
                raise HTTPException(status_code=403, detail="Invalid or revoked key")
            
            # Check expiry
            if key.expires_at and datetime.utcnow() > key.expires_at:
                raise HTTPException(status_code=403, detail="API key expired")
            
            # Check usage cap
            if key.usage_limit and key.usage_count >= key.usage_limit:
                raise HTTPException(status_code=429, detail="Usage limit exceeded")
            
            # Find route ID
            from models.api_key_models import APIRouteRegistry
            # For FastAPI, we need to get the route path differently
            full_path = str(request.url.path)
            method = request.method
            
            route = db_session.query(APIRouteRegistry).filter(
                APIRouteRegistry.path == full_path,
                APIRouteRegistry.method == method
            ).first()
            
            if not route:
                raise HTTPException(status_code=404, detail="Route not registered")
            
            # Check binding
            from models.api_key_models import APIKeyRoute
            bind = db_session.query(APIKeyRoute).filter(
                APIKeyRoute.api_key_id == key.id,
                APIKeyRoute.route_id == route.id
            ).first()
            
            if not bind:
                raise HTTPException(status_code=403, detail="Key not allowed on this route")
            
            # Increment usage
            key.usage_count += 1
            db_session.commit()
            
            # For FastAPI, we'll pass the auth data through kwargs
            # Store auth data in a way that can be accessed by the endpoint
            kwargs['auth_data'] = {
                'organization_id': key.organization_id,
                'entity_id': key.organization_id,
                'user_id': key.created_by_user_id
            }
            
            return await f(*args, **kwargs)
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
        finally:
            db_session.close()
    
    return decorated_function

def get_organization_id(auth_data: dict) -> Optional[int]:
    """Get current organization ID from auth data."""
    return auth_data.get('organization_id') if auth_data else None

def get_api_key_user_id(auth_data: dict) -> Optional[int]:
    """Get current API key user ID from auth data."""
    return auth_data.get('user_id') if auth_data else None
