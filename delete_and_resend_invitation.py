#!/usr/bin/env python3
"""
Script to delete an invitation and resend it with proper inviter name.
"""
import os
import sys
from datetime import datetime, timedelta, timezone
import secrets

# Add the project root to Python path
sys.path.append('.')

from services.mongodb_service import mongodb_service

def delete_and_resend_invitation():
    """Delete the existing invitation and create a new one with proper details."""
    
    # Invitation details
    invitation_id_to_delete = "be3b41e9e822be866065e03c"
    team_id = "65963a7fd00036c8e0397f77"
    invited_email = "devlead@prodigalai.com"
    inviter_user_id = "dc9b07d3ee00e42b9343341699dec7a2"
    inviter_email = "nishchal@prodigalai.com"
    
    print(f"🔍 Looking for invitation: {invitation_id_to_delete}")
    
    # Get the existing invitation
    invitation = mongodb_service.get_collection('team_invitations').find_one({
        "invitation_id": invitation_id_to_delete
    })
    
    if invitation:
        print(f"✅ Found invitation for {invitation.get('invited_email')}")
        print(f"   Status: {invitation.get('status')}")
        print(f"   Team: {invitation.get('team_name')}")
        
        # Delete the invitation
        result = mongodb_service.get_collection('team_invitations').delete_one({
            "invitation_id": invitation_id_to_delete
        })
        
        if result.deleted_count > 0:
            print(f"🗑️  Deleted invitation: {invitation_id_to_delete}")
        else:
            print(f"❌ Failed to delete invitation")
            return False
    else:
        print(f"⚠️  Invitation not found: {invitation_id_to_delete}")
    
    # Get team details
    team = mongodb_service.get_collection('master_teams').find_one({
        "team_id": team_id
    })
    
    if not team:
        print(f"❌ Team not found: {team_id}")
        return False
    
    print(f"✅ Found team: {team.get('name')}")
    
    # Get inviter details
    inviter = mongodb_service.get_collection('users').find_one({
        "user_id": inviter_user_id
    })
    
    inviter_name = inviter.get("name") if inviter else "Nishchal"
    
    print(f"✅ Inviter: {inviter_name} ({inviter_email})")
    
    # Create new invitation with proper details
    new_invitation = {
        "invitation_id": secrets.token_hex(12),
        "team_id": team_id,
        "team_name": team.get("name"),
        "invited_email": invited_email,
        "invited_by": inviter_user_id,
        "invited_by_name": inviter_name,
        "invited_by_email": inviter_email,
        "role": "member",
        "permissions": {
            "can_view_analytics": True,
            "can_manage_tasks": True,
            "can_invite": False,
            "can_manage_members": False,
            "can_manage_campaigns": False
        },
        "message": "Welcome to the team!",
        "status": "pending",
        "expires_at": datetime.now(timezone.utc).replace(hour=23, minute=59, second=59) + timedelta(days=7),
        "created_at": datetime.now(timezone.utc)
    }
    
    # Insert new invitation
    mongodb_service.get_collection('team_invitations').insert_one(new_invitation)
    
    print(f"\n✅ Created new invitation!")
    print(f"   Invitation ID: {new_invitation['invitation_id']}")
    print(f"   Team: {new_invitation['team_name']}")
    print(f"   Invited: {new_invitation['invited_email']}")
    print(f"   Invited by: {new_invitation['invited_by_name']} ({new_invitation['invited_by_email']})")
    print(f"   Role: {new_invitation['role']}")
    print(f"   Expires: {new_invitation['expires_at']}")
    print(f"\n📧 Invitation URL:")
    print(f"   https://dhanur-ai-dashboard-omega.vercel.app/teams/invitations/{new_invitation['invitation_id']}/accept")
    
    return True

if __name__ == "__main__":
    print("🚀 Starting invitation deletion and resend process...\n")
    
    try:
        # Connect to MongoDB
        if not mongodb_service.is_connected():
            print("❌ MongoDB not connected")
            sys.exit(1)
        
        success = delete_and_resend_invitation()
        
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

