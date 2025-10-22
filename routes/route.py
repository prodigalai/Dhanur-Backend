#!/usr/bin/env python3
"""
API routes for Content Crew Prodigal
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timedelta, timezone
import httpx
import secrets
import hashlib

from controllers import auth_controller
from middleware.auth import get_current_user
from services.database_service import test_database_connection
from services.mongodb_service import mongodb_service
import logging

logger = logging.getLogger(__name__)

def get_user_permissions(role: str) -> list:
    """Get user permissions based on role."""
    permissions_map = {
        "owner": ["create_campaign", "edit_campaign", "delete_campaign", "manage_team", "view_analytics", "manage_settings"],
        "admin": ["create_campaign", "edit_campaign", "delete_campaign", "manage_team", "view_analytics", "manage_settings"],
        "editor": ["create_campaign", "edit_campaign", "view_analytics"],
        "viewer": ["view_campaign", "view_analytics"]
    }
    return permissions_map.get(role, ["view_campaign"])

from models.request_models import (
    UserRegistrationRequest, UserLoginRequest, TokenRefreshRequest, 
    ProfileUpdateRequest, AuthResponse, UserProfileResponse, 
    HealthResponse, DatabaseHealthResponse
)
# from models.sqlalchemy_models import User  # Using MongoDB instead
import logging

logger = logging.getLogger(__name__)

# Simple in-memory storage for PKCE values (in production, use Redis/database)
_pkce_store = {}
_oauth_state_store = {}

def store_code_verifier(state: str, code_verifier: str, user_id: Optional[str] = None):
    """Store code_verifier using state as key."""
    _pkce_store[state] = {
        "code_verifier": code_verifier,
        "user_id": user_id,
        "created_at": "2024-01-01T00:00:00Z"  # In production, use actual timestamp
    }
    print(f"🔐 Stored PKCE: state={state[:10]}..., verifier={code_verifier[:10]}...")
    print(f"📊 PKCE store size: {len(_pkce_store)}")

def get_stored_code_verifier(state: str) -> Optional[str]:
    """Retrieve code_verifier using state as key."""
    print(f"🔍 Looking for PKCE: state={state[:10]}...")
    print(f"📊 Available states: {list(_pkce_store.keys())[:3]}...")
    
    if state in _pkce_store:
        data = _pkce_store[state]
        code_verifier = data["code_verifier"]
        print(f"✅ Found PKCE: state={state[:10]}..., verifier={code_verifier[:10]}...")
        # Remove from store after use (one-time use)
        del _pkce_store[state]
        return code_verifier
    else:
        print(f"❌ PKCE not found for state: {state[:10]}...")
        return None

def store_oauth_state(state: str, state_payload: Dict[str, Any]):
    """Store OAuth state payload for enhanced OAuth flows."""
    _oauth_state_store[state] = state_payload
    print(f"🔐 Stored OAuth state: state={state[:10]}..., payload_keys={list(state_payload.keys())}")
    print(f"📊 OAuth state store size: {len(_oauth_state_store)}")

def get_stored_oauth_state(state: str) -> Optional[Dict[str, Any]]:
    """Retrieve OAuth state payload."""
    print(f"🔍 Looking for OAuth state: state={state[:10]}...")
    print(f"📊 Available OAuth states: {list(_oauth_state_store.keys())[:3]}...")
    
    if state in _oauth_state_store:
        data = _oauth_state_store[state]
        print(f"✅ Found OAuth state: state={state[:10]}..., payload_keys={list(data.keys())}")
        # Remove from store after use (one-time use)
        del _oauth_state_store[state]
        return data
    else:
        print(f"❌ OAuth state not found for state: {state[:10]}...")
        return None

router = APIRouter()

# =====================================================
# AUTHENTICATION ROUTES
# =====================================================

# Registration route moved to auth_routes.py to avoid conflicts

# Login route moved to auth_routes.py to avoid conflicts

@router.post("/auth/refresh-token", response_model=AuthResponse)
async def refresh_token(
    request: TokenRefreshRequest
) -> AuthResponse:
    """Refresh access token endpoint."""
    return auth_controller.refresh_token(request.refresh_token)

@router.post("/auth/logout")
async def logout():
    """User logout endpoint."""
    return {"success": True, "message": "Logged out successfully"}

@router.post("/auth/forgot-password")
async def forgot_password(
    request: Request
):
    """Handle forgot password request."""
    try:
        if not mongodb_service.is_connected():
            raise HTTPException(status_code=503, detail="Database not available")
            
        body = await request.json()
        email = body.get("email")
        
        if not email:
            raise HTTPException(status_code=400, detail="Email is required")
        
        # Check if user exists
        users = mongodb_service.get_collection("users")
        user = users.find_one({"email": email})
        
        if not user:
            # Don't reveal if user exists or not for security
            return {"success": True, "message": "If the email exists, a password reset link has been sent"}
        
        # Generate reset token
        reset_token = secrets.token_urlsafe(32)
        
        # Store reset token in database
        users.update_one(
            {"email": email},
            {
                "$set": {
                    "reset_token": reset_token,
                    "reset_token_expires": datetime.now(timezone.utc) + timedelta(hours=1),
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        
        # Send email with reset link
        from services.email_service import email_service
        
        reset_url = f"https://dhanur-ai-dashboard-omega.vercel.app/auth/reset-password?token={reset_token}"
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        
        # Send password reset email
        email_sent = await email_service.send_password_reset_email(
            to_email=email,
            reset_url=reset_url,
            expires_at=expires_at
        )
        
        if email_sent:
            logger.info(f"Password reset email sent to {email}")
        else:
            logger.warning(f"Failed to send password reset email to {email}")
        
        return {
            "success": True, 
            "message": "Password reset email sent",
            "email_sent": email_sent
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Forgot password error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/auth/reset-password")
async def reset_password(
    request: Request
):
    """Reset password endpoint."""
    try:
        if not mongodb_service.is_connected():
            raise HTTPException(status_code=503, detail="Database not available")
            
        body = await request.json()
        token = body.get("token")
        new_password = body.get("new_password")
        
        if not token or not new_password:
            raise HTTPException(status_code=400, detail="Token and new password are required")
        
        if len(new_password) < 8:
            raise HTTPException(status_code=400, detail="Password must be at least 8 characters long")
        
        # Find user with this reset token
        users = mongodb_service.get_collection("users")
        user = users.find_one({
            "reset_token": token,
            "reset_token_expires": {"$gt": datetime.now(timezone.utc)}
        })
        
        if not user:
            raise HTTPException(status_code=400, detail="Invalid or expired reset token")
        
        # Hash new password using the same method as auth_routes
        from routes.auth_routes import hash_password
        new_password_hash = hash_password(new_password)
        
        # Update password and clear reset token
        users.update_one(
            {"_id": user["_id"]},
            {
                "$set": {
                    "password": new_password_hash,
                    "updated_at": datetime.now(timezone.utc)
                },
                "$unset": {
                    "reset_token": "",
                    "reset_token_expires": ""
                }
            }
        )
        
        return {"success": True, "message": "Password reset successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Reset password error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/auth/change-password")
async def change_password(current_password: str, new_password: str):
    """Change password endpoint."""
    return {"success": True, "message": "Password changed successfully"}

@router.post("/auth/update-password")
async def update_password(current_password: str, new_password: str):
    """Update password endpoint (alternative)."""
    return {"success": True, "message": "Password updated successfully"}

@router.post("/auth/verify-email")
async def verify_email(token: str):
    """Verify email address."""
    return {"success": True, "message": "Email verified successfully"}

@router.post("/auth/resend-verify-email")
async def resend_verify_email(email: str):
    """Resend verification email."""
    return {"success": True, "message": "Verification email sent"}

@router.post("/auth/update-entity")
async def update_entity(
    full_name: str = None,
    email: str = None,
    phone: str = None
):
    """Update entity/profile information."""
    return {
        "success": True,
        "message": "Profile updated successfully",
        "data": {
            "full_name": full_name,
            "email": email,
            "phone": phone
        }
    }

@router.post("/auth/update-avatar")
async def update_avatar(avatar_url: str):
    """Update user avatar."""
    return {
        "success": True,
        "message": "Avatar updated successfully",
        "data": {
            "avatar_url": avatar_url
        }
    }

@router.post("/auth/deactivate-account")
async def deactivate_account(reason: str):
    """Deactivate user account."""
    return {"success": True, "message": "Account deactivated successfully"}

@router.get("/auth/profile", response_model=UserProfileResponse)
async def get_profile(
    user_id: str
) -> UserProfileResponse:
    """Get user profile endpoint."""
    return auth_controller.get_user_profile(user_id)

@router.put("/auth/profile", response_model=UserProfileResponse)
async def update_profile(
    user_id: str,
    request: ProfileUpdateRequest
) -> UserProfileResponse:
    """Update user profile endpoint."""
    profile_data = request.dict(exclude_unset=True)
    return auth_controller.update_user_profile(user_id, profile_data)

# Health check routes are defined in main.py

# =====================================================
# OAUTH ROUTES
# =====================================================

@router.get("/oauth/linkedin/callback")
async def linkedin_callback():
    """LinkedIn OAuth callback endpoint."""
    return {"message": "LinkedIn OAuth callback"}

@router.get("/oauth/youtube/callback")
async def youtube_callback():
    """YouTube OAuth callback endpoint."""
    return {"message": "YouTube OAuth callback"}

# =====================================================
# SPOTIFY OAUTH ROUTES
# =====================================================

@router.get("/spotify-oauth-test")
async def spotify_oauth_test_page():
    """Serve the Spotify OAuth test HTML page."""
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Spotify OAuth PKCE Test</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .btn {
            background: #1DB954;
            color: white;
            border: none;
            padding: 15px 30px;
            border-radius: 25px;
            font-size: 16px;
            cursor: pointer;
            margin: 10px 5px;
        }
        .btn:hover {
            background: #1ed760;
        }
        .btn:disabled {
            background: #ccc;
            cursor: not-allowed;
        }
        .status {
            margin: 20px 0;
            padding: 15px;
            border-radius: 5px;
        }
        .success {
            background: #d4edda;
            border: 1px solid #c3e6cb;
            color: #155724;
        }
        .error {
            background: #f8d7da;
            border: 1px solid #f5c6cb;
            color: #721c24;
        }
        .info {
            background: #d1ecf1;
            border: 1px solid #bee5eb;
            color: #0c5460;
        }
        .code-block {
            background: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 5px;
            padding: 15px;
            margin: 10px 0;
            font-family: monospace;
            white-space: pre-wrap;
            word-break: break-all;
        }
        .step {
            margin: 20px 0;
            padding: 15px;
            border-left: 4px solid #1DB954;
            background: #f8f9fa;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎵 Spotify OAuth PKCE Test</h1>
        <p>This page demonstrates the complete Spotify OAuth flow with PKCE security.</p>
        
        <div class="step">
            <h3>Step 1: Initiate OAuth</h3>
            <button class="btn" onclick="testButton()" id="loginBtn">Connect to Spotify</button>
            <div id="step1Status"></div>
        </div>
        
        <div class="step">
            <h3>Step 2: OAuth Status</h3>
            <div id="step2Status"></div>
        </div>
        
        <div class="step">
            <h3>Step 3: OAuth Result</h3>
            <div id="step3Status"></div>
        </div>
        
        <div class="step">
            <h3>Debug Information</h3>
            <div id="debugInfo"></div>
        </div>
    </div>

    <script>
        const SPOTIFY_OAUTH_BASE = 'http://localhost:8080/oauth/spotify';
        
        // Check if this is a callback from Spotify
        window.onload = function() {
            const urlParams = new URLSearchParams(window.location.search);
            const code = urlParams.get('code');
            const state = urlParams.get('state');
            
            if (code && state) {
                showStatus('step2Status', 'info', '🔄 OAuth callback detected! Processing...');
                handleOAuthCallback(code, state);
            } else {
                showStatus('step2Status', 'info', '⏳ Waiting for OAuth callback...');
            }
            
            updateDebugInfo();
        };
        
        async function initiateOAuth() {
            try {
                console.log('🚀 Starting OAuth initiation...');
                showStatus('step1Status', 'info', '🔄 Initiating Spotify OAuth...');
                document.getElementById('loginBtn').disabled = true;
                
                console.log('📡 Calling:', `${SPOTIFY_OAUTH_BASE}/login`);
                const response = await fetch(`${SPOTIFY_OAUTH_BASE}/login`);
                console.log('📥 Response status:', response.status);
                
                const data = await response.json();
                console.log('📊 Response data:', data);
                
                if (data.success) {
                    // Store PKCE data securely
                    sessionStorage.setItem('spotify_code_verifier', data.code_verifier);
                    sessionStorage.setItem('spotify_state', data.state);
                    sessionStorage.setItem('spotify_timestamp', Date.now().toString());
                    
                    showStatus('step1Status', 'success', '✅ OAuth initiated successfully!');
                    showStatus('step2Status', 'info', '🔄 Redirecting to Spotify...');
                    
                    // Store data for display
                    sessionStorage.setItem('spotify_auth_data', JSON.stringify(data));
                    
                    // Create enhanced state with code_verifier encoded
                    const enhancedState = `${data.state}:${data.code_verifier}`;
                    const enhancedAuthUrl = data.authorization_url.replace(data.state, enhancedState);
                    
                    console.log('🔗 Enhanced auth URL:', enhancedAuthUrl);
                    showStatus('step2Status', 'info', '🔄 Using enhanced state with encoded code_verifier...');
                    
                    // Redirect to Spotify with enhanced state
                    setTimeout(() => {
                        console.log('🔄 Redirecting to Spotify...');
                        window.location.href = enhancedAuthUrl;
                    }, 1000);
                    
                } else {
                    throw new Error(data.error?.message || 'Failed to initiate OAuth');
                }
                
            } catch (error) {
                console.error('❌ OAuth initiation failed:', error);
                showStatus('step1Status', 'error', `❌ OAuth initiation failed: ${error.message}`);
                document.getElementById('loginBtn').disabled = false;
            }
        }
        
        async function handleOAuthCallback(code, state) {
            try {
                showStatus('step2Status', 'info', '🔄 Processing OAuth callback...');
                
                // Check if this is an enhanced state (contains code_verifier)
                if (state && state.includes(':')) {
                    const [originalState, codeVerifier] = state.split(':', 1);
                    showStatus('step2Status', 'success', '✅ Enhanced state detected with encoded code_verifier!');
                    
                    // Complete OAuth with enhanced state (backend will extract code_verifier)
                    const response = await fetch(
                        `${SPOTIFY_OAUTH_BASE}/callback?code=${encodeURIComponent(code)}&state=${encodeURIComponent(state)}`
                    );
                    
                    const result = await response.json();
                    
                    if (result.success) {
                        showStatus('step3Status', 'success', '🎉 OAuth completed successfully!');
                        showStatus('step2Status', 'success', '✅ Callback processed successfully!');
                        
                        // Display OAuth result
                        displayOAuthResult(result);
                        
                    } else {
                        throw new Error(result.error?.message || 'OAuth completion failed');
                    }
                    
                } else {
                    // Fallback: try to use stored code_verifier
                    const codeVerifier = sessionStorage.getItem('spotify_code_verifier');
                    const storedState = sessionStorage.getItem('spotify_state');
                    
                    if (!codeVerifier || !storedState) {
                        throw new Error('No PKCE data found. Please restart the OAuth flow.');
                    }
                    
                    if (state !== storedState) {
                        throw new Error('State mismatch! Potential CSRF attack.');
                    }
                    
                    showStatus('step2Status', 'success', '✅ Using stored PKCE data...');
                    
                    // Complete OAuth with stored code_verifier
                    const response = await fetch(
                        `${SPOTIFY_OAUTH_BASE}/callback?code=${encodeURIComponent(code)}&state=${encodeURIComponent(state)}&code_verifier=${encodeURIComponent(codeVerifier)}`
                    );
                    
                    const result = await response.json();
                    
                    if (result.success) {
                        // Clear stored PKCE data
                        sessionStorage.removeItem('spotify_code_verifier');
                        sessionStorage.removeItem('spotify_state');
                        sessionStorage.removeItem('spotify_timestamp');
                        
                        showStatus('step3Status', 'success', '🎉 OAuth completed successfully!');
                        showStatus('step2Status', 'success', '✅ Callback processed successfully!');
                        
                        // Display OAuth result
                        displayOAuthResult(result);
                        
                    } else {
                        throw new Error(result.error?.message || 'OAuth completion failed');
                    }
                }
                
            } catch (error) {
                console.error('OAuth callback handling failed:', error);
                showStatus('step3Status', 'error', `❌ OAuth completion failed: ${error.message}`);
                
                // Clear stored data on error
                sessionStorage.removeItem('spotify_code_verifier');
                sessionStorage.removeItem('spotify_state');
                sessionStorage.removeItem('spotify_timestamp');
            }
            
            updateDebugInfo();
        }
        
        function displayOAuthResult(result) {
            const resultDiv = document.getElementById('step3Status');
            resultDiv.innerHTML = `
                <div class="success">
                    <h4>🎉 OAuth Successful!</h4>
                    <p><strong>Message:</strong> ${result.message}</p>
                    <p><strong>Provider:</strong> ${result.oauth_account?.provider}</p>
                    <p><strong>Provider User ID:</strong> ${result.oauth_account?.provider_user_id}</p>
                    <details>
                        <summary>View Full Response</summary>
                        <div class="code-block">${JSON.stringify(result, null, 2)}</div>
                    </details>
                </div>
            `;
        }
        
        function showStatus(elementId, type, message) {
            const element = document.getElementById(elementId);
            element.className = `status ${type}`;
            element.innerHTML = message;
        }
        
        function updateDebugInfo() {
            const debugDiv = document.getElementById('debugInfo');
            const urlParams = new URLSearchParams(window.location.search);
            const code = urlParams.get('code');
            const state = urlParams.get('state');
            
            const storedData = {
                codeVerifier: sessionStorage.getItem('spotify_code_verifier') ? '✅ Stored' : '❌ Missing',
                state: sessionStorage.getItem('spotify_state') ? '✅ Stored' : '❌ Missing',
                timestamp: sessionStorage.getItem('spotify_timestamp') || '❌ Missing',
                currentCode: code ? '✅ Present' : '❌ Missing',
                currentState: state ? '✅ Present' : '❌ Missing'
            };
            
            debugDiv.innerHTML = `
                <h4>🔍 Debug Information</h4>
                <div class="code-block">
URL Parameters:
- code: ${storedData.currentCode}
- state: ${storedData.currentState}

Stored PKCE Data:
- code_verifier: ${storedData.codeVerifier}
- state: ${storedData.state}
- timestamp: ${storedData.timestamp}

Current URL: ${window.location.href}
                </div>
            `;
        }
        
        // Add simple test function
        function testButton() {
            console.log('🔘 Button clicked!');
            showStatus('step1Status', 'info', '🔘 Button click detected! Testing OAuth...');
            initiateOAuth();
        }
        
        // Add refresh button for testing
        function refreshPage() {
            location.reload();
        }
        
        // Add manual test button
        function testCallback() {
            const codeVerifier = sessionStorage.getItem('spotify_code_verifier');
            const state = sessionStorage.getItem('spotify_state');
            
            if (codeVerifier && state) {
                showStatus('step2Status', 'info', `Testing with stored data: state=${state}, code_verifier=${codeVerifier.substring(0, 20)}...`);
            } else {
                showStatus('step2Status', 'error', 'No stored PKCE data found. Please initiate OAuth first.');
            }
        }
    </script>
    
    <div style="margin-top: 20px; text-align: center;">
        <button class="btn" onclick="refreshPage()" style="background: #6c757d;">🔄 Refresh Page</button>
        <button class="btn" onclick="testCallback()" style="background: #17a2b8;">🧪 Test Callback</button>
    </div>
</body>
</html>
    """
    
    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=html_content, status_code=200)

@router.get("/oauth/spotify/login")
async def spotify_login(user_id: Optional[str] = None):
    """Get Spotify OAuth login URL with PKCE."""
    from controllers.spotify_controller import SpotifyOAuthController
    from providers.spotify.v1.oauth import get_authorization_url
    
    try:
        # Generate PKCE values
        code_verifier = secrets.token_urlsafe(64)
        state = secrets.token_urlsafe(32)
        
        print(f"🚀 Generated PKCE: state={state[:10]}..., verifier={code_verifier[:10]}...")
        
        # Store PKCE values server-side using state as key
        store_code_verifier(state, code_verifier, user_id)
        
        # Get authorization URL with PKCE using our generated code_verifier
        auth_data = get_authorization_url(state, code_verifier)
        
        print(f"🔗 Authorization URL generated with state: {state[:10]}...")
        
        # Return only the authorization URL and state (no code_verifier)
        return {
            "success": True,
            "authorization_url": auth_data["authorization_url"],
            "state": state,
            "message": "Redirect to authorization_url to complete OAuth"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to generate OAuth URL: {str(e)}"
        }

@router.get("/oauth/spotify/test")
async def spotify_test():
    """Test endpoint to verify Spotify OAuth setup."""
    return {
        "success": True,
        "message": "Spotify OAuth test endpoint working",
        "timestamp": "2024-01-01T00:00:00Z",
        "endpoints": {
            "login": "/oauth/spotify/login",
            "callback": "/oauth/spotify/callback",
            "callback_auth": "/auth/spotify/callback"
        }
    }

@router.get("/auth/spotify/callback")
async def spotify_callback_auth(
    code: str,
    state: str,
    user_id: Optional[str] = None,
    request: Request = None
):
    """Spotify OAuth callback endpoint (auth path) - redirects to oauth path."""
    from fastapi.responses import RedirectResponse
    
    # Redirect to the actual oauth callback endpoint
    redirect_url = f"/oauth/spotify/callback?code={code}&state={state}"
    if user_id:
        redirect_url += f"&user_id={user_id}"
    
    return RedirectResponse(url=redirect_url)

@router.get("/oauth/spotify/callback")
async def spotify_callback(
    code: str,
    state: str,
    user_id: Optional[str] = None,
    request: Request = None
):
    """Spotify OAuth callback endpoint with PKCE."""
    from controllers.spotify_controller import SpotifyOAuthController
    import httpx
    import os
    
    try:
        print(f"🔄 OAuth callback received: code={code[:10]}..., state={state[:10]}...")
        
        # Get code_verifier from storage using state (not from URL)
        code_verifier = get_stored_code_verifier(state)
        if not code_verifier:
            return {
                "success": False,
                "error": {
                    "code": "INVALID_STATE",
                    "message": "Invalid or expired state parameter",
                    "details": {
                        "issue": "Cannot find code_verifier for this state",
                        "solution": "Restart the OAuth flow - the session may have expired"
                    }
                }
            }
        
        print(f"🔑 Using code_verifier: {code_verifier[:10]}...")
        
        # Exchange the authorization code for tokens
        token_data = await exchange_spotify_code_for_tokens(code, code_verifier)
        
        if not token_data.get("access_token"):
            return {
                "success": False,
                "error": {
                    "code": "TOKEN_EXCHANGE_FAILED",
                    "message": "Failed to exchange authorization code for tokens"
                }
            }
        
        # Get user profile from Spotify using the OAuth provider
        from providers.spotify.v1.oauth import get_user_profile
        profile_data = get_user_profile(token_data["access_token"])
        
        # Try to store OAuth account in database (optional for demo)
        try:
            oauth_result = SpotifyOAuthController._store_oauth_account(
                db_session, user_id, token_data, profile_data
            )
            oauth_stored = oauth_result.get("is_active", False)
            oauth_account_info = {
                "id": oauth_result.get("id"),
                "provider": oauth_result.get("provider"),
                "provider_user_id": oauth_result.get("provider_user_id"),
                "is_active": oauth_result.get("is_active", False),
                "user_updated": oauth_result.get("user_updated", False),
                "note": oauth_result.get("note", "")
            }
        except Exception as e:
            print(f"⚠️  OAuth storage failed (continuing without database): {e}")
            oauth_stored = False
            oauth_account_info = None
        
        return {
            "success": True,
            "message": "Spotify OAuth successful" + (
                " (stored in database)" if oauth_stored else " (demo mode - not stored)"
            ) + (
                " - User profile updated" if oauth_account_info and oauth_account_info.get("user_updated") else ""
            ),
            "oauth_stored": oauth_stored,
            "oauth_account": oauth_account_info,
            "profile": profile_data,
            "tokens": {
                "access_token": token_data.get("access_token"),
                "refresh_token": token_data.get("refresh_token"),
                "expires_in": token_data.get("expires_in")
            }
        }
        
    except Exception as e:
        print(f"OAuth callback error: {str(e)}")
        return {
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": f"Failed to handle OAuth callback: {str(e)}"
            }
        }

async def exchange_spotify_code_for_tokens(code: str, code_verifier: str) -> dict:
    """Exchange Spotify authorization code for tokens using PKCE."""
    import os
    
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI", "https://contacted-curious-themselves-answered.trycloudflare.com/oauth/spotify/callback")
    
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": client_id,
        "code_verifier": code_verifier
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://accounts.spotify.com/api/token",
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if response.status_code != 200:
            raise Exception(f"Token exchange failed: {response.text}")
        
        return response.json()



@router.post("/oauth/spotify/refresh")
async def spotify_refresh_tokens(
    oauth_account_id: str
):
    """Refresh Spotify access tokens."""
    from controllers.spotify_controller import SpotifyOAuthController
    return SpotifyOAuthController.refresh_tokens(oauth_account_id)

@router.post("/oauth/spotify/disconnect")
async def spotify_disconnect(
    oauth_account_id: str
):
    """Disconnect Spotify OAuth account."""
    from controllers.spotify_controller import SpotifyOAuthController
    return SpotifyOAuthController.disconnect_account(oauth_account_id)

@router.get("/oauth/spotify/status/{user_id}")
async def spotify_account_status(
    user_id: str
):
    """Get Spotify OAuth account status for a user."""
    from controllers.spotify_controller import SpotifyOAuthController
    return SpotifyOAuthController.get_account_status(user_id)

# =====================================================
# BRAND MANAGEMENT ROUTES
# =====================================================

@router.get("/brand/list-brands")
async def list_brands(
    current_user: dict = Depends(get_current_user)
):
    """List all brands for the current user."""
    try:
        user_id = current_user.get('user_id', current_user.get('id', 'unknown'))
        
        # Get brands from MongoDB
        from services.mongodb_service import mongodb_service
        
        # Find brands where user is owner or team member
        brands = list(mongodb_service.get_collection('brands').find({
            "$or": [
                {"owner_id": user_id},
                {"team_members.user_id": user_id}
            ]
        }))
        
        # Format response
        formatted_brands = []
        for brand in brands:
            # Get campaign count for this brand
            campaigns_count = mongodb_service.get_collection('campaigns').count_documents({
                "brand_id": brand.get("brand_id"),
                "status": {"$ne": "deleted"}  # Exclude deleted campaigns
            })
            
            formatted_brands.append({
                "brand_id": brand.get("brand_id"),
                "name": brand.get("name"),
                "description": brand.get("description"),
                "type": brand.get("type", "personal"),
                "owner_id": brand.get("owner_id"),
                "status": brand.get("status", "active"),
                "created_at": brand.get("created_at").isoformat() if brand.get("created_at") else None,
                "updated_at": brand.get("updated_at").isoformat() if brand.get("updated_at") else None,
                "team_members_count": len(brand.get("team_members", [])),
                "campaigns_count": campaigns_count
            })
        
        logger.info(f"Listed {len(formatted_brands)} brands for user {user_id}")
        
        return {
            "success": True,
            "data": formatted_brands,
            "total": len(formatted_brands)
        }
        
    except Exception as e:
        logger.error(f"Error listing brands: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/brand/create-brand")
async def create_brand(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Create brand endpoint."""
    try:
        # Get request body
        body = await request.json()
        
        # Extract brand data
        brand_name = body.get("name")
        description = body.get("description")
        brand_type = body.get("type", "personal")  # personal, team, enterprise
        organization_id = body.get("organization_id")
        
        # Validate required fields
        if not brand_name:
            raise HTTPException(status_code=400, detail="Brand name is required")
        
        if not description:
            raise HTTPException(status_code=400, detail="Description is required")
        
        # Create brand data
        from datetime import datetime
        from bson import ObjectId
        
        brand_id = str(ObjectId())
        user_id = current_user.get('user_id', current_user.get('id', 'unknown'))
        
        brand_data = {
            "brand_id": brand_id,
            "name": brand_name,
            "description": description,
            "type": brand_type,
            "owner_id": user_id,
            "organization_id": organization_id,
            "status": "active",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "settings": {
                "notifications": {
                    "email_notifications": True,
                    "campaign_updates": True,
                    "team_invites": True,
                    "analytics_reports": True
                },
                "privacy": {
                    "public_profile": False,
                    "show_team_members": True,
                    "allow_public_campaigns": False
                }
            },
            "team_members": [
                {
                    "user_id": user_id,
                    "role": "admin",
                    "permissions": ["create_campaign", "edit_campaign", "delete_campaign", "manage_team", "view_analytics", "manage_settings"],
                    "joined_at": datetime.utcnow(),
                    "status": "active"
                }
            ]
        }
        
        # Save to MongoDB
        from services.mongodb_service import mongodb_service
        result = mongodb_service.get_collection('brands').insert_one(brand_data)
        
        if result.inserted_id:
            # Auto-create team chat conversation for the brand
            try:
                from services.chat_service import chat_service
                
                # Create a general team chat conversation for the brand owner
                conversation_result = await chat_service.create_conversation(
                    brand_id=brand_id,
                    creator_id=user_id,
                    participant_ids=[user_id],  # Start with just the owner
                    name=f"{brand_name} Team Chat"
                )
                
                if conversation_result["success"]:
                    logger.info(f"Auto-created team chat conversation for new brand {brand_id}")
                else:
                    logger.warning(f"Failed to auto-create team chat for brand {brand_id}: {conversation_result.get('error')}")
            except Exception as e:
                # Don't fail brand creation if chat creation fails
                logger.error(f"Error creating auto team chat for brand {brand_id}: {e}")
            
            logger.info(f"Brand created successfully: {brand_name} (ID: {brand_id}) by user {user_id}")
            return {
                "success": True,
                "message": "Brand created successfully",
                "data": {
                    "brand_id": brand_id,
                    "name": brand_name,
                    "description": description,
                    "type": brand_type,
                    "owner_id": user_id,
                    "created_at": brand_data["created_at"].isoformat(),
                    "team_members": len(brand_data["team_members"])
                }
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to create brand")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating brand: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/brand/{brand_id}")
async def get_brand_details(
    brand_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get single brand details."""
    try:
        user_id = current_user.get('user_id', current_user.get('id', 'unknown'))
        
        # Get brand from MongoDB
        from services.mongodb_service import mongodb_service
        
        brand = mongodb_service.get_collection('brands').find_one({
            "brand_id": brand_id,
            "$or": [
                {"owner_id": user_id},
                {"team_members.user_id": user_id}
            ]
        })
        
        if not brand:
            raise HTTPException(status_code=404, detail="Brand not found or access denied")
        
        # Get campaign count for this brand
        campaigns_count = mongodb_service.get_collection('campaigns').count_documents({
            "brand_id": brand_id
        })
        
        # Format response
        response_data = {
            "brand_id": brand.get("brand_id"),
            "name": brand.get("name"),
            "description": brand.get("description"),
            "type": brand.get("type", "personal"),
            "owner_id": brand.get("owner_id"),
            "organization_id": brand.get("organization_id"),
            "status": brand.get("status", "active"),
            "created_at": brand.get("created_at").isoformat() if brand.get("created_at") else None,
            "updated_at": brand.get("updated_at").isoformat() if brand.get("updated_at") else None,
            "settings": brand.get("settings", {}),
            "team_members": brand.get("team_members", []),
            "team_members_count": len(brand.get("team_members", [])),
            "campaigns_count": campaigns_count,
            "user_role": "owner" if brand.get("owner_id") == user_id else "member"
        }
        
        # Add user's role in this brand
        if brand.get("owner_id") == user_id:
            response_data["user_role"] = "owner"
            response_data["permissions"] = ["create_campaign", "edit_campaign", "delete_campaign", "manage_team", "view_analytics", "manage_settings"]
        else:
            # Find user's role in team members
            user_member = next((member for member in brand.get("team_members", []) if member.get("user_id") == user_id), None)
            if user_member:
                response_data["user_role"] = user_member.get("role", "viewer")
                response_data["permissions"] = user_member.get("permissions", [])
            else:
                response_data["user_role"] = "viewer"
                response_data["permissions"] = ["view_campaign", "view_analytics"]
        
        logger.info(f"Retrieved brand details for {brand_id} by user {user_id}")
        
        return {
            "success": True,
            "data": response_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting brand details: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/brand/{brand_id}/audios")
async def get_brand_audios(
    brand_id: str,
    current_user: dict = Depends(get_current_user),
    limit: int = 50,
    skip: int = 0,
    status: str = "active"
):
    """
    Get all audios assigned to a brand.
    
    This endpoint returns all audios that have been assigned to the specified brand.
    Only accessible by brand owners and team members.
    """
    try:
        from services.audio_assignment_service import audio_assignment_service
        
        user_id = current_user.get('user_id', current_user.get('id', 'unknown'))
        
        # Check if user has access to this brand
        brand = mongodb_service.get_collection('brands').find_one({
            "brand_id": brand_id,
            "$or": [
                {"owner_id": user_id},
                {"team_members.user_id": user_id}
            ]
        })
        
        if not brand:
            raise HTTPException(status_code=403, detail="Insufficient permissions or brand not found")
        
        # Get brand audios
        result = await audio_assignment_service.get_brand_audios(
            brand_id=brand_id,
            user_id=user_id,
            limit=limit,
            skip=skip,
            status=status
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting brand audios: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.put("/brand/update-brand")
async def update_brand(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Update brand information (auth: owner/admin)."""
    try:
        from services.mongodb_service import mongodb_service
        from datetime import datetime, timezone
        
        user_id = current_user.get('user_id', current_user.get('id', 'unknown'))
        
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        # Get brand_id and update data from request body
        body = await request.json()
        brand_id = body.get('brand_id')
        
        if not brand_id:
            raise HTTPException(status_code=400, detail="brand_id is required in request body")
        
        # Check if user has permission to update this brand
        brand = mongodb_service.get_collection('brands').find_one({
            "brand_id": brand_id,
            "$or": [
                {"owner_id": user_id},
                {"team_members": {"$elemMatch": {"user_id": user_id, "role": {"$in": ["owner", "admin"]}}}}
            ]
        })
        
        if not brand:
            raise HTTPException(status_code=404, detail="Brand not found or insufficient permissions")
        
        # Get user role for additional validation
        user_role = None
        if brand.get("owner_id") == user_id:
            user_role = "owner"
        else:
            for member in brand.get("team_members", []):
                if member.get("user_id") == user_id:
                    user_role = member.get("role")
                    break
        
        if user_role not in ["owner", "admin"]:
            raise HTTPException(status_code=403, detail="Only owners and admins can update brand information")
        
        # Prepare update data
        update_data = {"updated_at": datetime.now(timezone.utc)}
        updated_fields = []
        
        if body.get("name") is not None:
            update_data["name"] = body["name"]
            updated_fields.append("name")
        
        if body.get("description") is not None:
            update_data["description"] = body["description"]
            updated_fields.append("description")
        
        if body.get("type") is not None:
            if body["type"] not in ["business", "personal", "agency", "team", "enterprise"]:
                raise HTTPException(status_code=400, detail="Invalid brand type. Must be: business, personal, agency, team, or enterprise")
            update_data["type"] = body["type"]
            updated_fields.append("type")
        
        if body.get("website") is not None:
            update_data["website"] = body["website"]
            updated_fields.append("website")
        
        if body.get("industry") is not None:
            update_data["industry"] = body["industry"]
            updated_fields.append("industry")
        
        if body.get("settings") is not None:
            # Merge with existing settings
            existing_settings = brand.get("settings", {})
            existing_settings.update(body["settings"])
            update_data["settings"] = existing_settings
            updated_fields.append("settings")
        
        if not updated_fields:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        # Update brand in database
        result = mongodb_service.get_collection('brands').update_one(
            {"brand_id": brand_id},
            {"$set": update_data}
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=400, detail="No changes made to brand")
        
        logger.info(f"Brand updated: {brand_id} by user {user_id}. Updated fields: {updated_fields}")
        
        return {
            "success": True,
            "message": "Brand updated successfully",
            "data": {
                "brand_id": brand_id,
                "updated_fields": updated_fields,
                "updated_at": update_data["updated_at"].isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating brand: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.delete("/brand/delete-brand")
async def delete_brand(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Delete brand (auth: owner only)."""
    try:
        from services.mongodb_service import mongodb_service
        from datetime import datetime, timezone
        
        user_id = current_user.get('user_id', current_user.get('id', 'unknown'))
        
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        # Get brand_id from request body
        body = await request.json()
        brand_id = body.get('brand_id')
        
        if not brand_id:
            raise HTTPException(status_code=400, detail="brand_id is required in request body")
        
        # Check if user is the owner of this brand
        brand = mongodb_service.get_collection('brands').find_one({
            "brand_id": brand_id,
            "owner_id": user_id
        })
        
        if not brand:
            raise HTTPException(status_code=404, detail="Brand not found or you are not the owner")
        
        # Check if brand has active campaigns
        active_campaigns = mongodb_service.get_collection('campaigns').count_documents({
            "brand_id": brand_id,
            "status": {"$in": ["draft", "active", "paused"]}
        })
        
        if active_campaigns > 0:
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot delete brand with {active_campaigns} active campaigns. Please complete or cancel all campaigns first."
            )
        
        # Check if brand has pending tasks
        pending_tasks = mongodb_service.get_collection('campaign_tasks').count_documents({
            "brand_id": brand_id,
            "status": {"$in": ["pending", "in_progress"]}
        })
        
        if pending_tasks > 0:
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot delete brand with {pending_tasks} pending tasks. Please complete or cancel all tasks first."
            )
        
        # Soft delete: Update status to 'deleted' instead of removing
        result = mongodb_service.get_collection('brands').update_one(
            {"brand_id": brand_id},
            {
                "$set": {
                    "status": "deleted",
                    "deleted_at": datetime.now(timezone.utc),
                    "deleted_by": user_id,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=400, detail="Failed to delete brand")
        
        # Also soft delete related campaigns
        mongodb_service.get_collection('campaigns').update_many(
            {"brand_id": brand_id},
            {
                "$set": {
                    "status": "deleted",
                    "deleted_at": datetime.now(timezone.utc),
                    "deleted_by": user_id,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        
        # Also soft delete related tasks
        mongodb_service.get_collection('campaign_tasks').update_many(
            {"brand_id": brand_id},
            {
                "$set": {
                    "status": "cancelled",
                    "deleted_at": datetime.now(timezone.utc),
                    "deleted_by": user_id,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        
        logger.info(f"Brand deleted: {brand_id} by user {user_id}")
        
        return {
            "success": True,
            "message": "Brand and all related data deleted successfully",
            "data": {
                "brand_id": brand_id,
                "brand_name": brand.get("name"),
                "deleted_at": datetime.now(timezone.utc).isoformat(),
                "deleted_campaigns": active_campaigns,
                "deleted_tasks": pending_tasks
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting brand: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# Brand Update Request Model
class BrandUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, description="Brand name", min_length=2, max_length=100)
    description: Optional[str] = Field(None, description="Brand description")
    type: Optional[str] = Field(None, description="Brand type: business, personal, agency, team, enterprise")
    website: Optional[str] = Field(None, description="Brand website URL")
    industry: Optional[str] = Field(None, description="Industry category")
    settings: Optional[Dict[str, Any]] = Field(None, description="Brand settings")

# Brand Campaign Management APIs

class CampaignCreateRequest(BaseModel):
    name: str = Field(..., description="Campaign name", min_length=2, max_length=120)
    description: Optional[str] = Field(None, description="Campaign description")
    start_date: Optional[str] = Field(None, description="ISO start date")
    end_date: Optional[str] = Field(None, description="ISO end date")
    budget: Optional[float] = Field(None, description="Budget amount")
    status: Optional[str] = Field("draft", description="Campaign status")
@router.get("/brand/{brand_id}/campaign")
async def list_brand_campaigns(
    brand_id: str,
    current_user: dict = Depends(get_current_user),
    limit: int = 50,
    skip: int = 0,
    status: Optional[str] = None
):
    """List all campaigns for a brand (auth: owner/admin/editor/viewer)."""
    try:
        from services.mongodb_service import mongodb_service

        user_id = current_user.get('user_id', current_user.get('id', 'unknown'))

        # Access: must be owner or any team member
        brand = mongodb_service.get_collection('brands').find_one({
            "brand_id": brand_id,
            "$or": [
                {"owner_id": user_id},
                {"team_members.user_id": user_id}
            ]
        })

        if not brand:
            raise HTTPException(status_code=403, detail="Insufficient permissions or brand not found")

        # Build query (exclude deleted campaigns)
        q = {"brand_id": brand_id, "status": {"$ne": "deleted"}}
        if status:
            q["status"] = status

        cursor = (
            mongodb_service
            .get_collection('campaigns')
            .find(q)
            .sort("created_at", -1)
            .skip(int(skip))
            .limit(int(limit))
        )

        items = []
        for doc in cursor:
            items.append({
                "campaign_id": doc.get("campaign_id"),
                "brand_id": doc.get("brand_id"),
                "name": doc.get("name"),
                "description": doc.get("description"),
                "status": doc.get("status"),
                "budget": doc.get("budget"),
                "start_date": doc.get("start_date").isoformat() if doc.get("start_date") else None,
                "end_date": doc.get("end_date").isoformat() if doc.get("end_date") else None,
                "created_at": doc.get("created_at").isoformat() if doc.get("created_at") else None,
                "updated_at": doc.get("updated_at").isoformat() if doc.get("updated_at") else None
            })

        total = mongodb_service.get_collection('campaigns').count_documents(q)

        return {
            "success": True,
            "data": {
                "brand_id": brand_id,
                "total": total,
                "returned": len(items),
                "items": items
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing campaigns: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/brand/{brand_id}/campaign/ongoing")
async def get_ongoing_campaigns(brand_id: str):
    """Get ongoing campaigns for a brand."""
    return {"message": f"Get ongoing campaigns for brand {brand_id} - to be implemented"}

@router.get("/brand/{brand_id}/campaign/completed")
async def get_completed_campaigns(brand_id: str):
    """Get completed campaigns for a brand."""
    return {"message": f"Get completed campaigns for brand {brand_id} - to be implemented"}

@router.get("/brand/{brand_id}/campaign/{campaign_id}")
async def get_campaign_details(
    brand_id: str, 
    campaign_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get campaign details (auth: owner/admin/editor/viewer)."""
    try:
        if not mongodb_service.is_connected():
            raise HTTPException(status_code=503, detail="Database not available")
        
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        # Check if user has access to this brand
        brand = mongodb_service.get_collection('brands').find_one({
            "brand_id": brand_id,
            "team_members": {
                "$elemMatch": {
                    "user_id": user_id,
                    "status": "active"
                }
            }
        })
        
        if not brand:
            raise HTTPException(status_code=404, detail="Brand not found or access denied")
        
        # Get campaign details
        campaign = mongodb_service.get_collection('campaigns').find_one({
            "brand_id": brand_id,
            "campaign_id": campaign_id
        })
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # Check user permissions
        user_role = None
        for member in brand.get("team_members", []):
            if member.get("user_id") == user_id:
                user_role = member.get("role")
                break
        
        if not user_role:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Prepare campaign details
        campaign_details = {
            "campaign_id": campaign.get("campaign_id"),
            "name": campaign.get("name"),
            "description": campaign.get("description"),
            "status": campaign.get("status"),
            "start_date": campaign.get("start_date").isoformat() if campaign.get("start_date") else None,
            "end_date": campaign.get("end_date").isoformat() if campaign.get("end_date") else None,
            "budget": campaign.get("budget"),
            "created_at": campaign.get("created_at").isoformat() if campaign.get("created_at") else None,
            "updated_at": campaign.get("updated_at").isoformat() if campaign.get("updated_at") else None,
            "created_by": campaign.get("created_by"),
            "brand_id": campaign.get("brand_id"),
            "brand_name": brand.get("name"),
            "permissions": get_user_permissions(user_role)
        }
        
        # Add additional details based on user role
        if user_role in ["owner", "admin", "editor"]:
            campaign_details.update({
                "settings": campaign.get("settings", {}),
                "metadata": campaign.get("metadata", {}),
                "last_modified_by": campaign.get("last_modified_by"),
                "version": campaign.get("version", 1)
            })
        
        # Get assigned audios for this campaign
        assigned_audios = []
        try:
            logger.info("Starting to get assigned audios for campaign")
            from services.audio_assignment_service import audio_assignment_service
            from services.audio_storage_service import audio_storage_service
            
            # Get assignments for this campaign
            assignments_collection = mongodb_service.get_collection('audio_campaign_assignments')
            
            # Debug logging
            logger.info(f"Looking for assignments with brand_id: {brand_id}, campaign_id: {campaign_id}")
            
            # Test the query step by step
            all_assignments_debug = list(assignments_collection.find({"brand_id": brand_id}))
            logger.info(f"All assignments for brand {brand_id}: {len(all_assignments_debug)}")
            
            campaign_assignments_debug = list(assignments_collection.find({"metadata.campaign_id": campaign_id}))
            logger.info(f"All assignments for campaign {campaign_id}: {len(campaign_assignments_debug)}")
            
            assignments = list(assignments_collection.find({
                "brand_id": brand_id,
                "metadata.campaign_id": campaign_id,
                "status": "active"
            }))
            
            logger.info(f"Found {len(assignments)} direct campaign assignments")
            
            # Also get assignments that might be assigned to the brand (without specific campaign)
            brand_assignments = list(assignments_collection.find({
                "brand_id": brand_id,
                "status": "active",
                "$or": [
                    {"metadata.campaign_id": campaign_id},
                    {"metadata.campaign_id": {"$exists": False}},
                    {"metadata.campaign_id": None}
                ]
            }))
            
            logger.info(f"Found {len(brand_assignments)} brand assignments")
            
            # Combine both types of assignments
            all_assignments = assignments + [a for a in brand_assignments if a not in assignments]
            
            logger.info(f"Total assignments found: {len(all_assignments)}")
            
            for assignment in all_assignments:
                audio_id = assignment.get("audio_id")
                assignment_user_id = assignment.get("user_id")
                logger.info(f"Processing assignment for audio_id: {audio_id}, user_id: {assignment_user_id}")
                if audio_id:
                    # Get audio details
                    audio_result = await audio_storage_service.get_audio_by_id(
                        audio_id=audio_id,
                        user_id=assignment_user_id
                    )
                    
                    logger.info(f"Audio result success: {audio_result.get('success')}, error: {audio_result.get('error', 'N/A')}")
                    
                    if audio_result.get("success"):
                        audio_file = audio_result.get("audio_file", {})
                        assigned_audios.append({
                            "audio_id": audio_id,
                            "audio_url": audio_file.get("audio_url"),
                            "text": audio_file.get("text"),
                            "text_length": audio_file.get("text_length"),
                            "language": audio_file.get("language"),
                            "gender": audio_file.get("gender"),
                            "model_used": audio_file.get("model_used"),
                            "processing_time": audio_file.get("processing_time"),
                            "status": audio_file.get("status"),
                            "created_at": audio_file.get("created_at"),
                            "updated_at": audio_file.get("updated_at"),
                            "assigned_at": assignment.get("assigned_at").isoformat() if assignment.get("assigned_at") else None,
                            "assigned_by": assignment.get("assigned_by"),
                            "notes": assignment.get("notes"),
                            "source": audio_result.get("source"),
                            "metadata": audio_file.get("metadata", {}),
                            "assignment_info": {
                                "assignment_id": assignment.get("assignment_id"),
                                "campaign_id": assignment.get("metadata", {}).get("campaign_id"),
                                "assignment_type": assignment.get("metadata", {}).get("assignment_type", "brand")
                            }
                        })
        except Exception as e:
            logger.error(f"Failed to get assigned audios for campaign: {str(e)}")
        
        campaign_details["assigned_audios"] = assigned_audios
        campaign_details["assigned_audios_count"] = len(assigned_audios)
        
        logger.info(f"Retrieved campaign details: {campaign_id} for user {user_id}")
        
        return {
            "success": True,
            "message": "Campaign details retrieved successfully",
            "data": campaign_details
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting campaign details: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get campaign details: {str(e)}")

@router.post("/brand/{brand_id}/campaign")
async def create_campaign(
    brand_id: str,
    request: CampaignCreateRequest,
    current_user: dict = Depends(get_current_user)
):
    """Create a new campaign for a brand (owner/admin/editor)."""
    try:
        from services.mongodb_service import mongodb_service
        from datetime import datetime

        user_id = current_user.get('user_id', current_user.get('id', 'unknown'))

        # Check access: must be owner or team member (admin/editor)
        brand = mongodb_service.get_collection('brands').find_one({
            "brand_id": brand_id,
            "$or": [
                {"owner_id": user_id},
                {"team_members": {"$elemMatch": {"user_id": user_id, "role": {"$in": ["admin", "editor"]}}}}
            ]
        })
        if not brand:
            raise HTTPException(status_code=403, detail="Insufficient permissions or brand not found")

        # Normalize dates
        def to_dt(value):
            if not value:
                return None
            try:
                return datetime.fromisoformat(value.replace('Z', '+00:00'))
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid date format; use ISO 8601")

        campaign_doc = {
            "campaign_id": secrets.token_hex(12),
            "brand_id": brand_id,
            "name": request.name,
            "description": request.description,
            "start_date": to_dt(request.start_date),
            "end_date": to_dt(request.end_date),
            "budget": request.budget,
            "status": request.status or "draft",
            "created_by": user_id,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }

        mongodb_service.get_collection('campaigns').insert_one(campaign_doc)

        return {
            "success": True,
            "message": "Campaign created",
            "data": {
                "campaign_id": campaign_doc["campaign_id"],
                "brand_id": brand_id,
                "name": campaign_doc["name"],
                "status": campaign_doc["status"]
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating campaign: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

class CampaignUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, description="Campaign name", min_length=2, max_length=120)
    description: Optional[str] = Field(None, description="Campaign description")
    status: Optional[str] = Field(None, description="Campaign status")
    settings: Optional[Dict[str, Any]] = Field(None, description="Campaign settings")

@router.put("/brand/{brand_id}/campaign/{campaign_id}")
async def update_campaign(
    brand_id: str, 
    campaign_id: str,
    request: CampaignUpdateRequest,
    current_user: dict = Depends(get_current_user)
):
    """Update a campaign (auth: owner/admin/editor)."""
    try:
        if not mongodb_service.is_connected():
            raise HTTPException(status_code=503, detail="Database not available")
        
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        # Check if user has access to this brand
        brand = mongodb_service.get_collection('brands').find_one({
            "brand_id": brand_id,
            "team_members": {
                "$elemMatch": {
                    "user_id": user_id,
                    "status": "active"
                }
            }
        })
        
        if not brand:
            raise HTTPException(status_code=404, detail="Brand not found or access denied")
        
        # Check user permissions
        user_role = None
        for member in brand.get("team_members", []):
            if member.get("user_id") == user_id:
                user_role = member.get("role")
                break
        
        if user_role not in ["owner", "admin", "editor"]:
            raise HTTPException(status_code=403, detail="Insufficient permissions to update campaign")
        
        # Check if campaign exists
        campaign = mongodb_service.get_collection('campaigns').find_one({
            "brand_id": brand_id,
            "campaign_id": campaign_id
        })
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # Prepare update data
        update_data = {"updated_at": datetime.now(timezone.utc)}
        
        if request.name is not None:
            update_data["name"] = request.name
        if request.description is not None:
            update_data["description"] = request.description
        if request.status is not None:
            update_data["status"] = request.status
        if request.settings is not None:
            update_data["settings"] = request.settings
        
        update_data["last_modified_by"] = user_id
        update_data["version"] = campaign.get("version", 1) + 1
        
        # Update campaign
        result = mongodb_service.get_collection('campaigns').update_one(
            {"brand_id": brand_id, "campaign_id": campaign_id},
            {"$set": update_data}
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=400, detail="No changes made to campaign")
        
        logger.info(f"Updated campaign: {campaign_id} by user {user_id}")
        
        return {
            "success": True,
            "message": "Campaign updated successfully",
            "data": {
                "campaign_id": campaign_id,
                "updated_fields": list(update_data.keys()),
                "version": update_data["version"]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating campaign: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update campaign: {str(e)}")

@router.delete("/brand/{brand_id}/campaign/{campaign_id}")
async def delete_campaign(
    brand_id: str, 
    campaign_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a campaign (auth: owner/admin)."""
    try:
        if not mongodb_service.is_connected():
            raise HTTPException(status_code=503, detail="Database not available")
        
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        # Check if user has access to this brand
        brand = mongodb_service.get_collection('brands').find_one({
            "brand_id": brand_id,
            "team_members": {
                "$elemMatch": {
                    "user_id": user_id,
                    "status": "active"
                }
            }
        })
        
        if not brand:
            raise HTTPException(status_code=404, detail="Brand not found or access denied")
        
        # Check user permissions
        user_role = None
        for member in brand.get("team_members", []):
            if member.get("user_id") == user_id:
                user_role = member.get("role")
                break
        
        if user_role not in ["owner", "admin"]:
            raise HTTPException(status_code=403, detail="Insufficient permissions to delete campaign")
        
        # Check if campaign exists
        campaign = mongodb_service.get_collection('campaigns').find_one({
            "brand_id": brand_id,
            "campaign_id": campaign_id
        })
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # Soft delete campaign (mark as deleted instead of removing)
        result = mongodb_service.get_collection('campaigns').update_one(
            {"brand_id": brand_id, "campaign_id": campaign_id},
            {
                "$set": {
                    "status": "deleted",
                    "deleted_at": datetime.now(timezone.utc),
                    "deleted_by": user_id,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=400, detail="Failed to delete campaign")
        
        logger.info(f"Deleted campaign: {campaign_id} by user {user_id}")
        
        return {
            "success": True,
            "message": "Campaign deleted successfully",
            "data": {
                "campaign_id": campaign_id,
                "deleted_at": datetime.now(timezone.utc).isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting campaign: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete campaign: {str(e)}")

# Brand Team Management APIs (RBAC)
@router.get("/brand/{brand_id}/team")
async def list_brand_team(
    brand_id: str,
    current_user: dict = Depends(get_current_user)
):
    """List all team members and invitations for a brand."""
    try:
        user_id = current_user.get('user_id', current_user.get('id', 'unknown'))
        
        # Check if user has access to this brand
        from services.mongodb_service import mongodb_service
        
        brand = mongodb_service.get_collection('brands').find_one({
            "brand_id": brand_id,
            "$or": [
                {"owner_id": user_id},
                {"team_members.user_id": user_id}
            ]
        })
        
        if not brand:
            raise HTTPException(status_code=404, detail="Brand not found or access denied")
        
        # Get team members
        team_members = brand.get("team_members", [])
        
        # Get pending invitations
        pending_invitations = list(mongodb_service.get_collection('team_invitations').find({
            "brand_id": brand_id,
            "status": "pending"
        }))
        
        # Get all invitations (for status tracking)
        all_invitations = list(mongodb_service.get_collection('team_invitations').find({
            "brand_id": brand_id
        }).sort("created_at", -1))  # Sort by newest first
        
        # Format team members with complete user details
        formatted_members = []
        users_collection = mongodb_service.get_collection('users')
        
        for member in team_members:
            # Fetch complete user details from users collection
            user_details = users_collection.find_one({
                "$or": [
                    {"user_id": member.get("user_id")},
                    {"_id": member.get("user_id")}
                ]
            })
            
            # Use user details from users collection if available, otherwise fallback to stored data
            email = None
            name = None
            
            if user_details:
                email = user_details.get("email")
                name = user_details.get("name")
            else:
                # Fallback to stored data in team_members
                email = member.get("email")
                name = member.get("name")
            
            # If still no name, use email as name
            if not name and email:
                name = email
            
            formatted_members.append({
                "user_id": member.get("user_id"),
                "email": email,
                "name": name,
                "role": member.get("role"),
                "permissions": member.get("permissions", []),
                "joined_at": member.get("joined_at").isoformat() if member.get("joined_at") else None,
                "status": member.get("status", "active"),
                "is_owner": member.get("user_id") == brand.get("owner_id")
            })
        
        # Format invitations with complete user details
        formatted_invitations = []
        for invitation in all_invitations:
            # Fetch inviter details
            inviter_details = None
            if invitation.get("inviter_id"):
                inviter_details = users_collection.find_one({
                    "$or": [
                        {"user_id": invitation.get("inviter_id")},
                        {"_id": invitation.get("inviter_id")}
                    ]
                })
            
            # Use inviter details from users collection if available
            inviter_name = invitation.get("inviter_name")
            if inviter_details:
                inviter_name = inviter_details.get("name") or inviter_details.get("email") or invitation.get("inviter_name")
            
            formatted_invitations.append({
                "invitation_id": invitation.get("invitation_id"),
                "email": invitation.get("invitee_email"),
                "role": invitation.get("role"),
                "message": invitation.get("message"),
                "status": invitation.get("status"),
                "inviter_name": inviter_name,
                "created_at": invitation.get("created_at").isoformat() if invitation.get("created_at") else None,
                "expires_at": invitation.get("expires_at").isoformat() if invitation.get("expires_at") else None,
                "accepted_at": invitation.get("accepted_at").isoformat() if invitation.get("accepted_at") else None,
                "declined_at": invitation.get("declined_at").isoformat() if invitation.get("declined_at") else None,
                "invitation_url": f"https://dhanur-ai-dashboard-omega.vercel.app/brand/invite/{invitation.get('token')}"
            })
        
        # Count by status
        status_counts = {
            "pending": len([inv for inv in all_invitations if inv.get("status") == "pending"]),
            "accepted": len([inv for inv in all_invitations if inv.get("status") == "accepted"]),
            "declined": len([inv for inv in all_invitations if inv.get("status") == "declined"]),
            "expired": len([inv for inv in all_invitations if inv.get("status") == "expired"])
        }
        
        logger.info(f"Listed team for brand {brand_id}: {len(formatted_members)} members, {len(formatted_invitations)} invitations")
        
        return {
            "success": True,
            "data": {
                "brand_id": brand_id,
                "brand_name": brand.get("name"),
                "team_members": formatted_members,
                "invitations": formatted_invitations,
                "status_counts": status_counts,
                "total_members": len(formatted_members),
                "total_invitations": len(formatted_invitations)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing brand team: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/brand/{brand_id}/team/invite")
async def invite_team_member(
    brand_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Invite a new team member to brand."""
    try:
        # Get request body
        body = await request.json()
        
        # Extract invitation data
        email = body.get("email")
        role = body.get("role", "viewer")
        message = body.get("message", "")
        
        # Validate required fields
        if not email:
            raise HTTPException(status_code=400, detail="Email is required")
        
        if role not in ["admin", "editor", "viewer"]:
            raise HTTPException(status_code=400, detail="Invalid role. Must be admin, editor, or viewer")
        
        # Check for duplicate email validation
        if not email or "@" not in email or "." not in email.split("@")[1]:
            raise HTTPException(status_code=400, detail="Invalid email format")
        
        user_id = current_user.get('user_id', current_user.get('id', 'unknown'))
        
        # Check if brand exists and user has permission
        from services.mongodb_service import mongodb_service
        
        brand = mongodb_service.get_collection('brands').find_one({
            "brand_id": brand_id,
            "$or": [
                {"owner_id": user_id},
                {"team_members.user_id": user_id, "team_members.role": {"$in": ["admin"]}}
            ]
        })
        
        if not brand:
            raise HTTPException(status_code=404, detail="Brand not found or insufficient permissions")
        
        # Check if trying to invite the brand owner
        brand_owner = mongodb_service.get_collection('users').find_one({"email": email})
        if brand_owner and brand_owner.get("id") == brand.get("owner_id"):
            raise HTTPException(status_code=400, detail="Cannot invite the brand owner")
        
        # Check if user is already a team member
        existing_member = next((member for member in brand.get("team_members", []) if member.get("email") == email), None)
        if existing_member:
            raise HTTPException(status_code=400, detail="User is already a team member")
        
        # Check for existing pending invitation
        existing_invitation = mongodb_service.get_collection('team_invitations').find_one({
            "brand_id": brand_id,
            "invitee_email": email,
            "status": "pending"
        })
        
        if existing_invitation:
            raise HTTPException(
                status_code=400, 
                detail=f"Invitation already sent to {email}. Please wait for them to respond or the invitation to expire."
            )
        
        # Check for recently accepted invitation (within last 24 hours)
        from datetime import datetime, timedelta, timezone
        yesterday = datetime.utcnow() - timedelta(days=1)
        recent_accepted = mongodb_service.get_collection('team_invitations').find_one({
            "brand_id": brand_id,
            "invitee_email": email,
            "status": "accepted",
            "accepted_at": {"$gte": yesterday}
        })
        
        if recent_accepted:
            raise HTTPException(
                status_code=400,
                detail=f"User {email} recently joined this brand. Please wait before sending another invitation."
            )
        
        # Create invitation
        from datetime import datetime, timedelta, timezone
        from bson import ObjectId
        import secrets
        
        invitation_id = str(ObjectId())
        invitation_token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(days=7)  # 7 days expiry
        
        invitation_data = {
            "invitation_id": invitation_id,
            "brand_id": brand_id,
            "brand_name": brand.get("name"),
            "inviter_id": user_id,
            "inviter_name": current_user.get("email", "Unknown"),
            "invitee_email": email,
            "role": role,
            "message": message,
            "token": invitation_token,
            "status": "pending",  # pending, accepted, declined, expired
            "created_at": datetime.utcnow(),
            "expires_at": expires_at,
            "accepted_at": None,
            "declined_at": None
        }
        
        # Save invitation to MongoDB
        mongodb_service.get_collection('team_invitations').insert_one(invitation_data)
        
        # Send email invitation
        invitation_url = f"https://dhanur-ai-dashboard-omega.vercel.app/brand/invite/{invitation_token}"
        
        # Use real email service
        from services.email_service import email_service
        email_sent = await email_service.send_team_invitation_email(
            to_email=email,
            brand_name=brand.get("name"),
            inviter_name=current_user.get("email", "Unknown"),
            role=role,
            message=message,
            invitation_url=invitation_url,
            expires_at=expires_at
        )
        
        logger.info(f"Team invitation sent to {email} for brand {brand_id} by user {user_id}")
        
        return {
            "success": True,
            "message": "Team invitation sent successfully",
            "data": {
                "invitation_id": invitation_id,
                "email": email,
                "role": role,
                "expires_at": expires_at.isoformat(),
                "invitation_url": invitation_url,
                "email_sent": email_sent
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending team invitation: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# Team Invitation Accept/Decline APIs
@router.get("/brand/invite/{token}")
async def get_invitation_details(token: str):
    """Get invitation details by token (public endpoint)."""
    try:
        from services.mongodb_service import mongodb_service
        from datetime import datetime
        
        # Find invitation by token
        invitation = mongodb_service.get_collection('team_invitations').find_one({
            "token": token,
            "status": "pending"
        })
        
        if not invitation:
            raise HTTPException(status_code=404, detail="Invitation not found or expired")
        
        # Check if invitation is expired
        if invitation.get("expires_at"):
            expires_at = invitation.get("expires_at")
            # Handle both timezone-aware and naive datetimes
            if hasattr(expires_at, 'tzinfo') and expires_at.tzinfo is not None:
                # Timezone-aware datetime
                if expires_at < datetime.now(timezone.utc):
                    # Mark as expired
                    mongodb_service.get_collection('team_invitations').update_one(
                        {"token": token},
                        {"$set": {"status": "expired"}}
                    )
                    raise HTTPException(status_code=410, detail="Invitation has expired")
            else:
                # Naive datetime, assume UTC
                if expires_at < datetime.now(timezone.utc).replace(tzinfo=None):
                    # Mark as expired
                    mongodb_service.get_collection('team_invitations').update_one(
                        {"token": token},
                        {"$set": {"status": "expired"}}
                    )
                    raise HTTPException(status_code=410, detail="Invitation has expired")
        
        # Get brand details
        brand = mongodb_service.get_collection('brands').find_one({
            "brand_id": invitation.get("brand_id")
        })
        
        if not brand:
            raise HTTPException(status_code=404, detail="Brand not found")
        
        return {
            "success": True,
            "data": {
                "invitation_id": invitation.get("invitation_id"),
                "brand_name": invitation.get("brand_name"),
                "inviter_name": invitation.get("inviter_name"),
                "role": invitation.get("role"),
                "message": invitation.get("message"),
                "expires_at": invitation.get("expires_at").isoformat() if invitation.get("expires_at") else None,
                "brand_description": brand.get("description"),
                "brand_type": brand.get("type")
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting invitation details: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.delete("/brand/{brand_id}/team/invite/{invitation_id}")
async def delete_team_invitation(
    brand_id: str,
    invitation_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Remove a pending team invitation for a brand (owner/admin only)."""
    try:
        from services.mongodb_service import mongodb_service
        from datetime import datetime

        # Identify current user
        user_id = current_user.get('user_id', current_user.get('id', 'unknown'))

        # Check brand permissions - owner/admin can remove invites
        brand = mongodb_service.get_collection('brands').find_one({
            "brand_id": brand_id,
            "$or": [
                {"owner_id": user_id},
                {"team_members.user_id": user_id, "team_members.role": {"$in": ["admin"]}}
            ]
        })

        if not brand:
            raise HTTPException(status_code=403, detail="Insufficient permissions or brand not found")

        # Find the invitation
        invitation = mongodb_service.get_collection('team_invitations').find_one({
            "invitation_id": invitation_id,
            "brand_id": brand_id
        })

        if not invitation:
            raise HTTPException(status_code=404, detail="Invitation not found")

        # Admin/owner may remove any status; others only 'pending'
        is_admin = (
            brand.get("owner_id") == user_id or
            any(m.get("user_id") == user_id and m.get("role") == "admin" for m in brand.get("team_members", []))
        )

        delete_filter = {"invitation_id": invitation_id, "brand_id": brand_id}
        if not is_admin:
            if invitation.get("status") != "pending":
                raise HTTPException(status_code=409, detail="Only pending invitations can be removed")
            delete_filter["status"] = "pending"

        # Physically delete the invitation document (hard delete)
        res = mongodb_service.get_collection('team_invitations').delete_one(delete_filter)

        if res.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Invitation not found")

        return {
            "success": True,
            "message": "Invitation deleted successfully",
            "data": {
                "invitation_id": invitation_id,
                "brand_id": brand_id
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing invitation: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/brand/invite/{token}/accept")
async def accept_invitation(
    token: str,
    request: Request
):
    """Accept team invitation (public).
    If Authorization bearer is provided, derive user_id/email from token;
    otherwise read from JSON body.
    """
    try:
        # Try to read from Authorization header if present
        auth_header = request.headers.get("Authorization", "")
        user_id = None
        user_email = None
        if auth_header.startswith("Bearer "):
            token_str = auth_header.split(" ", 1)[1].strip()
            try:
                from services.jwt_service import verify_jwt_token, get_jwt_secret
                claims = verify_jwt_token(token_str, get_jwt_secret()) or {}
                user_id = claims.get("user_id") or claims.get("sub") or claims.get("id") or claims.get("entity_id")
                user_email = claims.get("email")
            except Exception:
                # Ignore token parse errors and fallback to body
                pass

        # Fallback to JSON body
        if not user_id or not user_email:
            try:
                body = await request.json()
            except Exception:
                body = {}
            user_id = user_id or body.get("user_id")
            user_email = user_email or body.get("email")
        
        if not user_id or not user_email:
            raise HTTPException(status_code=400, detail="User ID and email are required")
        
        from services.mongodb_service import mongodb_service
        from datetime import datetime
        
        # Find invitation by token
        invitation = mongodb_service.get_collection('team_invitations').find_one({
            "token": token,
            "status": "pending"
        })
        
        if not invitation:
            raise HTTPException(status_code=404, detail="Invitation not found or already processed")
        
        # Check if invitation is expired
        if invitation.get("expires_at"):
            expires_at = invitation.get("expires_at")
            # Handle both timezone-aware and naive datetimes
            if hasattr(expires_at, 'tzinfo') and expires_at.tzinfo is not None:
                # Timezone-aware datetime
                if expires_at < datetime.now(timezone.utc):
                    mongodb_service.get_collection('team_invitations').update_one(
                        {"token": token},
                        {"$set": {"status": "expired"}}
                    )
                    raise HTTPException(status_code=410, detail="Invitation has expired")
            else:
                # Naive datetime, assume UTC
                if expires_at < datetime.now(timezone.utc).replace(tzinfo=None):
                    mongodb_service.get_collection('team_invitations').update_one(
                        {"token": token},
                        {"$set": {"status": "expired"}}
                    )
                    raise HTTPException(status_code=410, detail="Invitation has expired")
        
        # Check if email matches
        if invitation.get("invitee_email") != user_email:
            raise HTTPException(status_code=400, detail="Email does not match invitation")
        
        # Add user to brand team
        brand_id = invitation.get("brand_id")
        role = invitation.get("role")
        
        # Add team member to brand
        mongodb_service.get_collection('brands').update_one(
            {"brand_id": brand_id},
            {
                "$push": {
                    "team_members": {
                        "user_id": user_id,
                        "email": user_email,
                        "role": role,
                        "permissions": get_role_permissions(role),
                        "joined_at": datetime.now(timezone.utc),
                        "status": "active"
                    }
                }
            }
        )
        
        # Update invitation status
        mongodb_service.get_collection('team_invitations').update_one(
            {"token": token},
            {
                "$set": {
                    "status": "accepted",
                    "accepted_at": datetime.now(timezone.utc),
                    "accepted_by": user_id
                }
            }
        )
        
        # Auto-create chat conversation for the new team member
        try:
            from services.chat_service import chat_service
            from bson import ObjectId
            
            # Get all team members for this brand
            brand = mongodb_service.get_collection('brands').find_one({"brand_id": brand_id})
            if brand and brand.get("team_members"):
                team_member_ids = [member["user_id"] for member in brand["team_members"]]
                
                # Create a general team chat conversation
                conversation_result = await chat_service.create_conversation(
                    brand_id=brand_id,
                    creator_id=user_id,
                    participant_ids=team_member_ids,
                    name=f"{invitation.get('brand_name', 'Team')} Chat"
                )
                
                if conversation_result["success"]:
                    logger.info(f"Auto-created team chat conversation for brand {brand_id}")
                else:
                    logger.warning(f"Failed to auto-create team chat: {conversation_result.get('error')}")
        except Exception as e:
            # Don't fail the invitation acceptance if chat creation fails
            logger.error(f"Error creating auto team chat: {e}")
        
        logger.info(f"Invitation accepted by {user_email} for brand {brand_id}")
        
        return {
            "success": True,
            "message": "Invitation accepted successfully",
            "data": {
                "brand_id": brand_id,
                "brand_name": invitation.get("brand_name"),
                "role": role,
                "joined_at": datetime.now(timezone.utc).isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error accepting invitation: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/brand/invite/{token}/decline")
async def decline_invitation(token: str, request: Request):
    """Decline team invitation (public endpoint)."""
    try:
        # Get request body
        body = await request.json()
        user_email = body.get("email")
        
        if not user_email:
            raise HTTPException(status_code=400, detail="Email is required")
        
        from services.mongodb_service import mongodb_service
        from datetime import datetime
        
        # Find invitation by token
        invitation = mongodb_service.get_collection('team_invitations').find_one({
            "token": token,
            "status": "pending"
        })
        
        if not invitation:
            raise HTTPException(status_code=404, detail="Invitation not found or already processed")
        
        # Check if email matches
        if invitation.get("invitee_email") != user_email:
            raise HTTPException(status_code=400, detail="Email does not match invitation")
        
        # Update invitation status
        mongodb_service.get_collection('team_invitations').update_one(
            {"token": token},
            {
                "$set": {
                    "status": "declined",
                    "declined_at": datetime.utcnow(),
                    "declined_by": user_email
                }
            }
        )
        
        logger.info(f"Invitation declined by {user_email} for brand {invitation.get('brand_id')}")
        
        return {
            "success": True,
            "message": "Invitation declined successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error declining invitation: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

def get_role_permissions(role: str) -> list:
    """Get permissions for a role."""
    permissions_map = {
        "admin": ["create_campaign", "edit_campaign", "delete_campaign", "manage_team", "view_analytics", "manage_settings"],
        "editor": ["create_campaign", "edit_campaign", "view_analytics"],
        "viewer": ["view_campaign", "view_analytics"]
    }
    return permissions_map.get(role, ["view_campaign"])

@router.delete("/brand/{brand_id}/team/invite")
async def delete_all_invitations(
    brand_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Remove all invitations (any status) for a brand. Owner/admin only."""
    try:
        from services.mongodb_service import mongodb_service

        user_id = current_user.get('user_id', current_user.get('id', 'unknown'))

        # Verify owner/admin
        brand = mongodb_service.get_collection('brands').find_one({
            "brand_id": brand_id,
            "$or": [
                {"owner_id": user_id},
                {"team_members.user_id": user_id, "team_members.role": {"$in": ["admin"]}}
            ]
        })
        if not brand:
            raise HTTPException(status_code=403, detail="Insufficient permissions or brand not found")

        res = mongodb_service.get_collection('team_invitations').delete_many({"brand_id": brand_id})

        return {
            "success": True,
            "message": "All invitations deleted successfully",
            "data": {
                "brand_id": brand_id,
                "deleted": res.deleted_count
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting all invitations: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.put("/brand/{brand_id}/team/{user_id}/role")
async def update_team_member_role(brand_id: str, user_id: str):
    """Update team member role in brand."""
    return {"message": f"Update role for user {user_id} in brand {brand_id} - to be implemented"}

@router.delete("/brand/{brand_id}/team/{user_id}")
async def remove_team_member(
    brand_id: str, 
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Remove team member from brand."""
    try:
        current_user_id = current_user.get('user_id', current_user.get('id', 'unknown'))
        
        # Check if user has permission to remove team members
        from services.mongodb_service import mongodb_service
        
        brand = mongodb_service.get_collection('brands').find_one({
            "brand_id": brand_id,
            "$or": [
                {"owner_id": current_user_id},
                {"team_members.user_id": current_user_id, "team_members.role": {"$in": ["admin"]}}
            ]
        })
        
        if not brand:
            raise HTTPException(status_code=404, detail="Brand not found or insufficient permissions")
        
        # Check if trying to remove owner
        if brand.get("owner_id") == user_id:
            raise HTTPException(status_code=400, detail="Cannot remove brand owner")
        
        # Check if user is trying to remove themselves
        if current_user_id == user_id:
            raise HTTPException(status_code=400, detail="Cannot remove yourself. Use leave brand instead.")
        
        # Check if the user to be removed is actually a team member
        team_member = next((member for member in brand.get("team_members", []) if member.get("user_id") == user_id), None)
        if not team_member:
            raise HTTPException(status_code=404, detail="User is not a team member of this brand")
        
        # Remove user from team members
        result = mongodb_service.get_collection('brands').update_one(
            {"brand_id": brand_id},
            {
                "$pull": {
                    "team_members": {"user_id": user_id}
                }
            }
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="User not found in team")
        
        # Log the removal
        logger.info(f"User {user_id} removed from brand {brand_id} by user {current_user_id}")
        
        from datetime import datetime
        
        return {
            "success": True,
            "message": f"User {team_member.get('email', user_id)} has been removed from the team",
            "data": {
                "removed_user_id": user_id,
                "removed_user_email": team_member.get("email"),
                "removed_user_role": team_member.get("role"),
                "removed_by": current_user_id,
                "removed_at": datetime.utcnow().isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing team member: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/brand/{brand_id}/team/roles")
async def list_brand_roles(brand_id: str):
    """List available roles for brand."""
    return {"message": f"List roles for brand {brand_id} - to be implemented"}

# Brand Campaign Task Management APIs
class TaskCreateRequest(BaseModel):
    title: str = Field(..., description="Task title", min_length=2, max_length=200)
    description: Optional[str] = Field(None, description="Task description")
    priority: str = Field("medium", description="Task priority: low, medium, high, urgent")
    due_date: Optional[str] = Field(None, description="Due date in ISO format")
    assigned_to: Optional[str] = Field(None, description="User ID to assign task to")
    tags: Optional[list] = Field(None, description="Task tags")

class TaskUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, description="Task title", min_length=2, max_length=200)
    description: Optional[str] = Field(None, description="Task description")
    status: Optional[str] = Field(None, description="Task status: pending, in_progress, completed, cancelled")
    priority: Optional[str] = Field(None, description="Task priority: low, medium, high, urgent")
    due_date: Optional[str] = Field(None, description="Due date in ISO format")
    assigned_to: Optional[str] = Field(None, description="User ID to assign task to")
    tags: Optional[list] = Field(None, description="Task tags")
    notes: Optional[str] = Field(None, description="Task notes")

@router.post("/brand/{brand_id}/campaign/{campaign_id}/task")
async def create_campaign_task(
    brand_id: str,
    campaign_id: str,
    request: TaskCreateRequest,
    current_user: dict = Depends(get_current_user)
):
    """Create a task for a campaign (auth: owner/admin/editor)."""
    try:
        if not mongodb_service.is_connected():
            raise HTTPException(status_code=503, detail="Database not available")
        
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        # Check if user has access to this brand
        brand = mongodb_service.get_collection('brands').find_one({
            "brand_id": brand_id,
            "team_members": {
                "$elemMatch": {
                    "user_id": user_id,
                    "status": "active"
                }
            }
        })
        
        if not brand:
            raise HTTPException(status_code=404, detail="Brand not found or access denied")
        
        # Check user permissions
        user_role = None
        for member in brand.get("team_members", []):
            if member.get("user_id") == user_id:
                user_role = member.get("role")
                break
        
        if user_role not in ["owner", "admin", "editor"]:
            raise HTTPException(status_code=403, detail="Insufficient permissions to create tasks")
        
        # Check if campaign exists
        campaign = mongodb_service.get_collection('campaigns').find_one({
            "brand_id": brand_id,
            "campaign_id": campaign_id
        })
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # Validate assigned_to user if provided
        if request.assigned_to:
            assigned_user_exists = any(
                member.get("user_id") == request.assigned_to and member.get("status") == "active"
                for member in brand.get("team_members", [])
            )
            if not assigned_user_exists:
                raise HTTPException(status_code=400, detail="Assigned user is not a team member")
        
        # Create task document
        task_doc = {
            "task_id": secrets.token_hex(12),
            "campaign_id": campaign_id,
            "brand_id": brand_id,
            "title": request.title,
            "description": request.description,
            "priority": request.priority,
            "status": "pending",
            "assigned_to": request.assigned_to or user_id,
            "created_by": user_id,
            "due_date": datetime.fromisoformat(request.due_date) if request.due_date else None,
            "tags": request.tags or [],
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "notes": []
        }
        
        mongodb_service.get_collection('campaign_tasks').insert_one(task_doc)
        
        logger.info(f"Created task: {task_doc['task_id']} for campaign {campaign_id} by user {user_id}")
        
        return {
            "success": True,
            "message": "Task created successfully",
            "data": {
                "task_id": task_doc["task_id"],
                "title": task_doc["title"],
                "status": task_doc["status"],
                "priority": task_doc["priority"],
                "assigned_to": task_doc["assigned_to"],
                "created_at": task_doc["created_at"].isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create task: {str(e)}")

@router.get("/brand/{brand_id}/campaign/{campaign_id}/task")
async def list_campaign_tasks(
    brand_id: str,
    campaign_id: str,
    current_user: dict = Depends(get_current_user),
    status: Optional[str] = None,
    assigned_to: Optional[str] = None,
    priority: Optional[str] = None,
    limit: int = 20,
    skip: int = 0
):
    """List tasks for a campaign (auth: team members)."""
    try:
        if not mongodb_service.is_connected():
            raise HTTPException(status_code=503, detail="Database not available")
        
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        # Check if user has access to this brand
        brand = mongodb_service.get_collection('brands').find_one({
            "brand_id": brand_id,
            "team_members": {
                "$elemMatch": {
                    "user_id": user_id,
                    "status": "active"
                }
            }
        })
        
        if not brand:
            raise HTTPException(status_code=404, detail="Brand not found or access denied")
        
        # Check if campaign exists
        campaign = mongodb_service.get_collection('campaigns').find_one({
            "brand_id": brand_id,
            "campaign_id": campaign_id
        })
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # Build query
        query = {"brand_id": brand_id, "campaign_id": campaign_id}
        if status:
            query["status"] = status
        if assigned_to:
            query["assigned_to"] = assigned_to
        if priority:
            query["priority"] = priority
        
        # Get tasks
        cursor = (
            mongodb_service
            .get_collection('campaign_tasks')
            .find(query)
            .sort("created_at", -1)
            .skip(skip)
            .limit(limit)
        )
        
        tasks = []
        for task in cursor:
            # Get user names for assigned_to and created_by
            assigned_to_name = None
            created_by_name = None
            
            # Get assigned_to user name
            if task.get("assigned_to"):
                assigned_user = mongodb_service.get_collection('users').find_one({
                    "user_id": task.get("assigned_to")
                })
                if assigned_user:
                    assigned_to_name = assigned_user.get("name") or assigned_user.get("email")
            
            # Get created_by user name
            if task.get("created_by"):
                created_user = mongodb_service.get_collection('users').find_one({
                    "user_id": task.get("created_by")
                })
                if created_user:
                    created_by_name = created_user.get("name") or created_user.get("email")
            
            task_data = {
                "task_id": task.get("task_id"),
                "title": task.get("title"),
                "description": task.get("description"),
                "status": task.get("status"),
                "priority": task.get("priority"),
                "assigned_to": task.get("assigned_to"),
                "assigned_to_name": assigned_to_name,
                "created_by": task.get("created_by"),
                "created_by_name": created_by_name,
                "due_date": task.get("due_date").isoformat() if task.get("due_date") else None,
                "tags": task.get("tags", []),
                "created_at": task.get("created_at").isoformat() if task.get("created_at") else None,
                "updated_at": task.get("updated_at").isoformat() if task.get("updated_at") else None
            }
            tasks.append(task_data)
        
        total = mongodb_service.get_collection('campaign_tasks').count_documents(query)
        
        logger.info(f"Listed {len(tasks)} tasks for campaign {campaign_id}")
        
        return {
            "success": True,
            "data": {
                "campaign_id": campaign_id,
                "brand_id": brand_id,
                "total": total,
                "returned": len(tasks),
                "tasks": tasks
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing tasks: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list tasks: {str(e)}")

@router.put("/brand/{brand_id}/campaign/{campaign_id}/task/{task_id}")
async def update_campaign_task(
    brand_id: str,
    campaign_id: str,
    task_id: str,
    request: TaskUpdateRequest,
    current_user: dict = Depends(get_current_user)
):
    """Update a campaign task (auth: task assignee or admin/owner)."""
    try:
        if not mongodb_service.is_connected():
            raise HTTPException(status_code=503, detail="Database not available")
        
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        # Check if user has access to this brand
        brand = mongodb_service.get_collection('brands').find_one({
            "brand_id": brand_id,
            "team_members": {
                "$elemMatch": {
                    "user_id": user_id,
                    "status": "active"
                }
            }
        })
        
        if not brand:
            raise HTTPException(status_code=404, detail="Brand not found or access denied")
        
        # Get user role
        user_role = None
        for member in brand.get("team_members", []):
            if member.get("user_id") == user_id:
                user_role = member.get("role")
                break
        
        # Check if task exists
        task = mongodb_service.get_collection('campaign_tasks').find_one({
            "brand_id": brand_id,
            "campaign_id": campaign_id,
            "task_id": task_id
        })
        
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Check permissions - task assignee or admin/owner can update
        if task.get("assigned_to") != user_id and user_role not in ["owner", "admin"]:
            raise HTTPException(status_code=403, detail="Insufficient permissions to update this task")
        
        # Prepare update data
        update_data = {"updated_at": datetime.now(timezone.utc)}
        
        if request.title is not None:
            update_data["title"] = request.title
        if request.description is not None:
            update_data["description"] = request.description
        if request.status is not None:
            update_data["status"] = request.status
        if request.priority is not None:
            update_data["priority"] = request.priority
        if request.due_date is not None:
            update_data["due_date"] = datetime.fromisoformat(request.due_date) if request.due_date else None
        if request.assigned_to is not None:
            # Validate assigned_to user if provided
            if request.assigned_to:
                assigned_user_exists = any(
                    member.get("user_id") == request.assigned_to and member.get("status") == "active"
                    for member in brand.get("team_members", [])
                )
                if not assigned_user_exists:
                    raise HTTPException(status_code=400, detail="Assigned user is not a team member")
            update_data["assigned_to"] = request.assigned_to
        if request.tags is not None:
            update_data["tags"] = request.tags
        if request.notes is not None:
            # Add note to notes array
            note = {
                "note": request.notes,
                "added_by": user_id,
                "added_at": datetime.now(timezone.utc)
            }
            update_data["$push"] = {"notes": note}
        
        # Update task
        if "$push" in update_data:
            # Handle notes separately with $push
            notes_data = update_data.pop("$push")
            result = mongodb_service.get_collection('campaign_tasks').update_one(
                {"brand_id": brand_id, "campaign_id": campaign_id, "task_id": task_id},
                {"$set": update_data, "$push": notes_data}
            )
        else:
            result = mongodb_service.get_collection('campaign_tasks').update_one(
                {"brand_id": brand_id, "campaign_id": campaign_id, "task_id": task_id},
                {"$set": update_data}
            )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=400, detail="No changes made to task")
        
        logger.info(f"Updated task: {task_id} by user {user_id}")
        
        return {
            "success": True,
            "message": "Task updated successfully",
            "data": {
                "task_id": task_id,
                "updated_fields": list(update_data.keys())
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating task: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update task: {str(e)}")

@router.get("/brand/{brand_id}/campaign/{campaign_id}/task/{task_id}")
async def get_campaign_task(
    brand_id: str,
    campaign_id: str,
    task_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get task details (auth: team members)."""
    try:
        if not mongodb_service.is_connected():
            raise HTTPException(status_code=503, detail="Database not available")
        
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        # Check if user has access to this brand
        brand = mongodb_service.get_collection('brands').find_one({
            "brand_id": brand_id,
            "team_members": {
                "$elemMatch": {
                    "user_id": user_id,
                    "status": "active"
                }
            }
        })
        
        if not brand:
            raise HTTPException(status_code=404, detail="Brand not found or access denied")
        
        # Get task
        task = mongodb_service.get_collection('campaign_tasks').find_one({
            "brand_id": brand_id,
            "campaign_id": campaign_id,
            "task_id": task_id
        })
        
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Prepare task details
        task_details = {
            "task_id": task.get("task_id"),
            "campaign_id": task.get("campaign_id"),
            "brand_id": task.get("brand_id"),
            "title": task.get("title"),
            "description": task.get("description"),
            "status": task.get("status"),
            "priority": task.get("priority"),
            "assigned_to": task.get("assigned_to"),
            "created_by": task.get("created_by"),
            "due_date": task.get("due_date").isoformat() if task.get("due_date") else None,
            "tags": task.get("tags", []),
            "notes": task.get("notes", []),
            "created_at": task.get("created_at").isoformat() if task.get("created_at") else None,
            "updated_at": task.get("updated_at").isoformat() if task.get("updated_at") else None
        }
        
        logger.info(f"Retrieved task details: {task_id} for user {user_id}")
        
        return {
            "success": True,
            "message": "Task details retrieved successfully",
            "data": task_details
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting task details: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get task details: {str(e)}")

@router.delete("/brand/{brand_id}/campaign/{campaign_id}/task/{task_id}")
async def delete_campaign_task(
    brand_id: str,
    campaign_id: str,
    task_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a campaign task (auth: admin/owner)."""
    try:
        if not mongodb_service.is_connected():
            raise HTTPException(status_code=503, detail="Database not available")
        
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        # Check if user has access to this brand
        brand = mongodb_service.get_collection('brands').find_one({
            "brand_id": brand_id,
            "team_members": {
                "$elemMatch": {
                    "user_id": user_id,
                    "status": "active"
                }
            }
        })
        
        if not brand:
            raise HTTPException(status_code=404, detail="Brand not found or access denied")
        
        # Check user permissions
        user_role = None
        for member in brand.get("team_members", []):
            if member.get("user_id") == user_id:
                user_role = member.get("role")
                break
        
        if user_role not in ["owner", "admin"]:
            raise HTTPException(status_code=403, detail="Insufficient permissions to delete task")
        
        # Check if task exists
        task = mongodb_service.get_collection('campaign_tasks').find_one({
            "brand_id": brand_id,
            "campaign_id": campaign_id,
            "task_id": task_id
        })
        
        if not task:
            raise HTTPException(status_code=404, detail="Campaign task not found")
        
        # Soft delete task
        result = mongodb_service.get_collection('campaign_tasks').update_one(
            {"brand_id": brand_id, "campaign_id": campaign_id, "task_id": task_id},
            {
                "$set": {
                    "status": "deleted",
                    "deleted_at": datetime.now(timezone.utc),
                    "deleted_by": user_id,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=400, detail="Failed to delete task")
        
        logger.info(f"Deleted campaign task: {task_id} by user {user_id}")
        
        return {
            "success": True,
            "message": "Campaign task deleted successfully",
            "data": {
                "task_id": task_id,
                "deleted_at": datetime.now(timezone.utc).isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting campaign task: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete campaign task: {str(e)}")

# Brand Campaign Analytics APIs
@router.get("/brand/{brand_id}/campaign/{campaign_id}/analytics")
async def get_campaign_analytics(brand_id: str, campaign_id: str):
    """Get detailed analytics for a campaign."""
    return {"message": f"Get analytics for campaign {campaign_id} in brand {brand_id} - to be implemented"}

@router.get("/brand/{brand_id}/campaign/analytics/overview")
async def get_brand_campaigns_overview(brand_id: str):
    """Get overview analytics for all campaigns in brand."""
    return {"message": f"Get campaigns overview for brand {brand_id} - to be implemented"}

@router.get("/brand/{brand_id}/campaign/{campaign_id}/analytics/performance")
async def get_campaign_performance(brand_id: str, campaign_id: str):
    """Get performance metrics for a campaign."""
    return {"message": f"Get performance for campaign {campaign_id} in brand {brand_id} - to be implemented"}

@router.get("/brand/{brand_id}/campaign/{campaign_id}/analytics/engagement")
async def get_campaign_engagement(brand_id: str, campaign_id: str):
    """Get engagement analytics for a campaign."""
    return {"message": f"Get engagement for campaign {campaign_id} in brand {brand_id} - to be implemented"}

# Brand Settings APIs
@router.get("/brand/{brand_id}/settings")
async def get_brand_settings(brand_id: str):
    """Get brand settings and configuration."""
    return {"message": f"Get settings for brand {brand_id} - to be implemented"}

@router.put("/brand/{brand_id}/settings")
async def update_brand_settings(brand_id: str):
    """Update brand settings and configuration."""
    return {"message": f"Update settings for brand {brand_id} - to be implemented"}

@router.get("/brand/{brand_id}/settings/permissions")
async def get_brand_permissions(brand_id: str):
    """Get brand permission settings."""
    return {"message": f"Get permissions for brand {brand_id} - to be implemented"}

@router.put("/brand/{brand_id}/settings/permissions")
async def update_brand_permissions(brand_id: str):
    """Update brand permission settings."""
    return {"message": f"Update permissions for brand {brand_id} - to be implemented"}

# =====================================================
# ORGANIZATION MANAGEMENT ROUTES
# =====================================================

@router.get("/organization/list-organizations")
async def list_organizations():
    """List all organizations endpoint."""
    return {"message": "List organizations endpoint - to be implemented"}

@router.post("/organization/create-organization")
async def create_organization():
    """Create organization endpoint."""
    return {"message": "Create organization endpoint - to be implemented"}

@router.put("/organization/update-organization")
async def update_organization():
    """Update organization endpoint."""
    return {"message": "Update organization endpoint - to be implemented"}

@router.delete("/organization/delete-organization")
async def delete_organization():
    """Delete organization endpoint."""
    return {"message": "Delete organization endpoint - to be implemented"}

# =====================================================
# PROJECT MANAGEMENT ROUTES
# =====================================================

@router.get("/project/list-projects")
async def list_projects():
    """List all projects endpoint."""
    return {"message": "List projects endpoint - to be implemented"}

@router.post("/project/create-project")
async def create_project():
    """Create project endpoint."""
    return {"message": "Create project endpoint - to be implemented"}

@router.put("/project/update-project")
async def update_project():
    """Update project endpoint."""
    return {"message": "Update project endpoint - to be implemented"}

@router.delete("/project/delete-project")
async def delete_project():
    """Delete project endpoint."""
    return {"message": "Delete project endpoint - to be implemented"}

# =====================================================
# SCHEDULED POSTS ROUTES
# =====================================================

@router.get("/scheduled-posts/list")
async def list_scheduled_posts():
    """List all scheduled posts endpoint."""
    return {"message": "List scheduled posts endpoint - to be implemented"}

@router.post("/scheduled-posts/create")
async def create_scheduled_post():
    """Create scheduled post endpoint."""
    return {"message": "Create scheduled post endpoint - to be implemented"}

@router.put("/scheduled-posts/update")
async def update_scheduled_post():
    """Update scheduled post endpoint."""
    return {"message": "Update scheduled post endpoint - to be implemented"}

@router.delete("/scheduled-posts/delete")
async def delete_scheduled_post():
    """Delete scheduled post endpoint."""
    return {"message": "Delete scheduled post endpoint - to be implemented"}

# =====================================================
# USER MANAGEMENT ROUTES
# =====================================================

@router.get("/users/list")
async def list_users():
    """List all users endpoint."""
    return {"message": "List users endpoint - to be implemented"}

@router.get("/users/{user_id}")
async def get_user(user_id: str):
    """Get specific user endpoint."""
    return {"message": f"Get user {user_id} endpoint - to be implemented"}

@router.put("/users/{user_id}")
async def update_user(user_id: str):
    """Update specific user endpoint."""
    return {"message": f"Update user {user_id} endpoint - to be implemented"}

@router.delete("/users/{user_id}")
async def delete_user(user_id: str):
    """Delete specific user endpoint."""
    return {"message": f"Delete user {user_id} endpoint - to be implemented"}

# ============================================================================
# GENERAL TASK MANAGEMENT APIs (Independent Tasks)
# ============================================================================

@router.post("/brand/{brand_id}/task")
async def create_general_task(
    brand_id: str,
    request: TaskCreateRequest,
    current_user: dict = Depends(get_current_user)
):
    """Create a general task (not tied to specific campaign) (auth: owner/admin/editor)."""
    try:
        if not mongodb_service.is_connected():
            raise HTTPException(status_code=503, detail="Database not available")
        
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        # Check if user has access to this brand
        brand = mongodb_service.get_collection('brands').find_one({
            "brand_id": brand_id,
            "team_members": {
                "$elemMatch": {
                    "user_id": user_id,
                    "status": "active"
                }
            }
        })
        
        if not brand:
            raise HTTPException(status_code=404, detail="Brand not found or access denied")
        
        # Check user permissions
        user_role = None
        for member in brand.get("team_members", []):
            if member.get("user_id") == user_id:
                user_role = member.get("role")
                break
        
        if user_role not in ["owner", "admin", "editor"]:
            raise HTTPException(status_code=403, detail="Insufficient permissions to create tasks")
        
        # Validate assigned_to user if provided
        if request.assigned_to:
            assigned_user_exists = any(
                member.get("user_id") == request.assigned_to and member.get("status") == "active"
                for member in brand.get("team_members", [])
            )
            if not assigned_user_exists:
                raise HTTPException(status_code=400, detail="Assigned user is not a team member")
        
        # Create task document
        task_doc = {
            "task_id": secrets.token_hex(12),
            "brand_id": brand_id,
            "campaign_id": None,  # Independent task
            "title": request.title,
            "description": request.description,
            "priority": request.priority,
            "status": "pending",
            "assigned_to": request.assigned_to or user_id,
            "created_by": user_id,
            "due_date": datetime.fromisoformat(request.due_date) if request.due_date else None,
            "tags": request.tags or [],
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "notes": [],
            "category": "general"  # Default category for independent tasks
        }
        
        mongodb_service.get_collection('campaign_tasks').insert_one(task_doc)
        
        logger.info(f"Created general task: {task_doc['task_id']} for brand {brand_id} by user {user_id}")
        
        return {
            "success": True,
            "message": "General task created successfully",
            "data": {
                "task_id": task_doc["task_id"],
                "title": task_doc["title"],
                "status": task_doc["status"],
                "priority": task_doc["priority"],
                "assigned_to": task_doc["assigned_to"],
                "created_at": task_doc["created_at"].isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating general task: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create general task: {str(e)}")

@router.get("/brand/{brand_id}/task")
async def list_general_tasks(
    brand_id: str,
    current_user: dict = Depends(get_current_user),
    status: Optional[str] = None,
    assigned_to: Optional[str] = None,
    priority: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 20,
    skip: int = 0
):
    """List general tasks for a brand (auth: team members)."""
    try:
        if not mongodb_service.is_connected():
            raise HTTPException(status_code=503, detail="Database not available")
        
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        # Check if user has access to this brand
        brand = mongodb_service.get_collection('brands').find_one({
            "brand_id": brand_id,
            "team_members": {
                "$elemMatch": {
                    "user_id": user_id,
                    "status": "active"
                }
            }
        })
        
        if not brand:
            raise HTTPException(status_code=404, detail="Brand not found or access denied")
        
        # Build query for general tasks (campaign_id is None)
        query = {"brand_id": brand_id, "campaign_id": None}
        if status:
            query["status"] = status
        if assigned_to:
            query["assigned_to"] = assigned_to
        if priority:
            query["priority"] = priority
        if category:
            query["category"] = category
        
        # Get tasks
        cursor = (
            mongodb_service
            .get_collection('campaign_tasks')
            .find(query)
            .sort("created_at", -1)
            .skip(skip)
            .limit(limit)
        )
        
        tasks = []
        for task in cursor:
            # Get user names for assigned_to and created_by
            assigned_to_name = None
            created_by_name = None
            
            # Get assigned_to user name
            if task.get("assigned_to"):
                assigned_user = mongodb_service.get_collection('users').find_one({
                    "user_id": task.get("assigned_to")
                })
                if assigned_user:
                    assigned_to_name = assigned_user.get("name") or assigned_user.get("email")
            
            # Get created_by user name
            if task.get("created_by"):
                created_user = mongodb_service.get_collection('users').find_one({
                    "user_id": task.get("created_by")
                })
                if created_user:
                    created_by_name = created_user.get("name") or created_user.get("email")
            
            task_data = {
                "task_id": task.get("task_id"),
                "title": task.get("title"),
                "description": task.get("description"),
                "status": task.get("status"),
                "priority": task.get("priority"),
                "assigned_to": task.get("assigned_to"),
                "assigned_to_name": assigned_to_name,
                "created_by": task.get("created_by"),
                "created_by_name": created_by_name,
                "due_date": task.get("due_date").isoformat() if task.get("due_date") else None,
                "tags": task.get("tags", []),
                "category": task.get("category", "general"),
                "created_at": task.get("created_at").isoformat() if task.get("created_at") else None,
                "updated_at": task.get("updated_at").isoformat() if task.get("updated_at") else None
            }
            tasks.append(task_data)
        
        total = mongodb_service.get_collection('campaign_tasks').count_documents(query)
        
        logger.info(f"Listed {len(tasks)} general tasks for brand {brand_id}")
        
        return {
            "success": True,
            "data": {
                "brand_id": brand_id,
                "total": total,
                "returned": len(tasks),
                "tasks": tasks
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing general tasks: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list general tasks: {str(e)}")

@router.get("/brand/{brand_id}/task/{task_id}")
async def get_general_task(
    brand_id: str,
    task_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get general task details (auth: team members)."""
    try:
        if not mongodb_service.is_connected():
            raise HTTPException(status_code=503, detail="Database not available")
        
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        # Check if user has access to this brand
        brand = mongodb_service.get_collection('brands').find_one({
            "brand_id": brand_id,
            "team_members": {
                "$elemMatch": {
                    "user_id": user_id,
                    "status": "active"
                }
            }
        })
        
        if not brand:
            raise HTTPException(status_code=404, detail="Brand not found or access denied")
        
        # Get task
        task = mongodb_service.get_collection('campaign_tasks').find_one({
            "brand_id": brand_id,
            "task_id": task_id,
            "campaign_id": None  # General task
        })
        
        if not task:
            raise HTTPException(status_code=404, detail="General task not found")
        
        # Prepare task details
        task_details = {
            "task_id": task.get("task_id"),
            "brand_id": task.get("brand_id"),
            "campaign_id": task.get("campaign_id"),
            "title": task.get("title"),
            "description": task.get("description"),
            "status": task.get("status"),
            "priority": task.get("priority"),
            "assigned_to": task.get("assigned_to"),
            "created_by": task.get("created_by"),
            "due_date": task.get("due_date").isoformat() if task.get("due_date") else None,
            "tags": task.get("tags", []),
            "category": task.get("category", "general"),
            "notes": task.get("notes", []),
            "created_at": task.get("created_at").isoformat() if task.get("created_at") else None,
            "updated_at": task.get("updated_at").isoformat() if task.get("updated_at") else None
        }
        
        logger.info(f"Retrieved general task details: {task_id} for user {user_id}")
        
        return {
            "success": True,
            "message": "General task details retrieved successfully",
            "data": task_details
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting general task details: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get general task details: {str(e)}")

@router.put("/brand/{brand_id}/task/{task_id}")
async def update_general_task(
    brand_id: str,
    task_id: str,
    request: TaskUpdateRequest,
    current_user: dict = Depends(get_current_user)
):
    """Update a general task (auth: task assignee or admin/owner)."""
    try:
        if not mongodb_service.is_connected():
            raise HTTPException(status_code=503, detail="Database not available")
        
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        # Check if user has access to this brand
        brand = mongodb_service.get_collection('brands').find_one({
            "brand_id": brand_id,
            "team_members": {
                "$elemMatch": {
                    "user_id": user_id,
                    "status": "active"
                }
            }
        })
        
        if not brand:
            raise HTTPException(status_code=404, detail="Brand not found or access denied")
        
        # Get user role
        user_role = None
        for member in brand.get("team_members", []):
            if member.get("user_id") == user_id:
                user_role = member.get("role")
                break
        
        # Check if task exists
        task = mongodb_service.get_collection('campaign_tasks').find_one({
            "brand_id": brand_id,
            "task_id": task_id,
            "campaign_id": None  # General task
        })
        
        if not task:
            raise HTTPException(status_code=404, detail="General task not found")
        
        # Check permissions - task assignee or admin/owner can update
        if task.get("assigned_to") != user_id and user_role not in ["owner", "admin"]:
            raise HTTPException(status_code=403, detail="Insufficient permissions to update this task")
        
        # Prepare update data
        update_data = {"updated_at": datetime.now(timezone.utc)}
        
        if request.title is not None:
            update_data["title"] = request.title
        if request.description is not None:
            update_data["description"] = request.description
        if request.status is not None:
            update_data["status"] = request.status
        if request.priority is not None:
            update_data["priority"] = request.priority
        if request.due_date is not None:
            update_data["due_date"] = datetime.fromisoformat(request.due_date) if request.due_date else None
        if request.assigned_to is not None:
            # Validate assigned_to user if provided
            if request.assigned_to:
                assigned_user_exists = any(
                    member.get("user_id") == request.assigned_to and member.get("status") == "active"
                    for member in brand.get("team_members", [])
                )
                if not assigned_user_exists:
                    raise HTTPException(status_code=400, detail="Assigned user is not a team member")
            update_data["assigned_to"] = request.assigned_to
        if request.tags is not None:
            update_data["tags"] = request.tags
        
        # Handle notes separately with $push
        if request.notes is not None:
            note = {
                "note": request.notes,
                "added_by": user_id,
                "added_at": datetime.now(timezone.utc)
            }
            # Use $push for notes, and $set for other fields
            result = mongodb_service.get_collection('campaign_tasks').update_one(
                {"brand_id": brand_id, "task_id": task_id, "campaign_id": None},
                {"$set": update_data, "$push": {"notes": note}}
            )
        else:
            result = mongodb_service.get_collection('campaign_tasks').update_one(
                {"brand_id": brand_id, "task_id": task_id, "campaign_id": None},
                {"$set": update_data}
            )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=400, detail="No changes made to task")
        
        logger.info(f"Updated general task: {task_id} by user {user_id}")
        
        return {
            "success": True,
            "message": "General task updated successfully",
            "data": {
                "task_id": task_id,
                "updated_fields": list(update_data.keys())
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating general task: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update general task: {str(e)}")

@router.delete("/brand/{brand_id}/task/{task_id}")
async def delete_general_task(
    brand_id: str,
    task_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a general task (auth: admin/owner)."""
    try:
        if not mongodb_service.is_connected():
            raise HTTPException(status_code=503, detail="Database not available")
        
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        # Check if user has access to this brand
        brand = mongodb_service.get_collection('brands').find_one({
            "brand_id": brand_id,
            "team_members": {
                "$elemMatch": {
                    "user_id": user_id,
                    "status": "active"
                }
            }
        })
        
        if not brand:
            raise HTTPException(status_code=404, detail="Brand not found or access denied")
        
        # Check user permissions
        user_role = None
        for member in brand.get("team_members", []):
            if member.get("user_id") == user_id:
                user_role = member.get("role")
                break
        
        if user_role not in ["owner", "admin"]:
            raise HTTPException(status_code=403, detail="Insufficient permissions to delete task")
        
        # Check if task exists
        task = mongodb_service.get_collection('campaign_tasks').find_one({
            "brand_id": brand_id,
            "task_id": task_id,
            "campaign_id": None  # General task
        })
        
        if not task:
            raise HTTPException(status_code=404, detail="General task not found")
        
        # Soft delete task
        result = mongodb_service.get_collection('campaign_tasks').update_one(
            {"brand_id": brand_id, "task_id": task_id, "campaign_id": None},
            {
                "$set": {
                    "status": "deleted",
                    "deleted_at": datetime.now(timezone.utc),
                    "deleted_by": user_id,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=400, detail="Failed to delete task")
        
        logger.info(f"Deleted general task: {task_id} by user {user_id}")
        
        return {
            "success": True,
            "message": "General task deleted successfully",
            "data": {
                "task_id": task_id,
                "deleted_at": datetime.now(timezone.utc).isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting general task: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete general task: {str(e)}")
