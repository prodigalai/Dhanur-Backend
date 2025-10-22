#!/usr/bin/env python3
"""
Script to resend invitation with proper inviter name.
"""
import os
import sys
import asyncio
import requests
from datetime import datetime, timedelta, timezone

# Add the project root to Python path
sys.path.append('.')

from services.mongodb_service import mongodb_service
from services.jwt_service import create_jwt_token

def generate_jwt_for_user(user_id: str, email: str) -> str:
    """Generate JWT token for a user."""
    secret = os.getenv("JWT_SECRET_KEY", "hanur_super_secret_jwt_key_2024_make_it_long_and_secure")
    
    expires_delta = timedelta(hours=24)
    data = {
        "user_id": user_id,
        "email": email,
        "purpose": "access"
    }
    
    token = create_jwt_token(data, secret, expires_delta)
    return token

def resend_invitation():
    """Delete old invitation and resend with proper details."""
    
    # User details
    inviter_user_id = "dc9b07d3ee00e42b9343341699dec7a2"
    inviter_email = "nishchal@prodigalai.com"
    
    # Invitation details
    old_invitation_id = "be3b41e9e822be866065e03c"
    team_id = "65963a7fd00036c8e0397f77"
    invited_email = "devlead@prodigalai.com"
    
    print(f"🔑 Generating JWT token for {inviter_email}...")
    jwt_token = generate_jwt_for_user(inviter_user_id, inviter_email)
    print(f"✅ JWT Token generated: {jwt_token[:50]}...")
    
    print(f"\n🗑️ Deleting old invitation: {old_invitation_id}...")
    
    # Delete old invitation
    result = mongodb_service.get_collection('team_invitations').delete_one({
        "invitation_id": old_invitation_id
    })
    
    if result.deleted_count > 0:
        print(f"✅ Deleted old invitation")
    else:
        print(f"⚠️  Old invitation not found (may already be deleted)")
    
    print(f"\n📧 Sending new invitation via API...")
    
    # API endpoint
    api_url = f"http://localhost:8080/api/v2/teams/{team_id}/invite"
    
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "email": invited_email,
        "role": "member",
        "message": "Welcome to the Dhanur AI team! We're excited to have you on board.",
        "permissions": {
            "can_view_analytics": True,
            "can_manage_tasks": True,
            "can_invite": False,
            "can_manage_members": False,
            "can_manage_campaigns": False
        }
    }
    
    try:
        response = requests.post(api_url, json=payload, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Invitation sent successfully!")
            print(f"\n📋 Details:")
            print(f"   Invitation ID: {data['data']['invitation_id']}")
            print(f"   Team: {data['data']['team_name']}")
            print(f"   Invited: {data['data']['invited_email']}")
            print(f"   Role: {data['data']['role']}")
            print(f"   Expires: {data['data']['expires_at']}")
            print(f"\n📧 Invitation URL:")
            print(f"   https://dhanur-ai-dashboard-omega.vercel.app/teams/invitations/{data['data']['invitation_id']}/accept")
            return True
        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting invitation resend process...\n")
    
    try:
        # Connect to MongoDB
        if not mongodb_service.is_connected():
            print("❌ MongoDB not connected")
            sys.exit(1)
        
        print("✅ MongoDB connected\n")
        
        success = resend_invitation()
        
        if success:
            print("\n✅ Process completed successfully!")
        else:
            print("\n❌ Process failed!")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

