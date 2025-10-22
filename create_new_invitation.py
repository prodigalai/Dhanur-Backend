#!/usr/bin/env python3
"""
Create a new invitation with proper inviter name.
"""
import sys
import secrets
from datetime import datetime, timedelta, timezone

sys.path.append('.')

from services.mongodb_service import mongodb_service

def create_new_invitation():
    """Create a new invitation with inviter details."""
    
    # Details
    team_id = "65963a7fd00036c8e0397f77"
    invited_email = "devlead@prodigalai.com"
    inviter_user_id = "dc9b07d3ee00e42b9343341699dec7a2"
    
    print(f"🔍 Checking team: {team_id}")
    
    # Get team
    team = mongodb_service.get_collection('master_teams').find_one({
        "team_id": team_id
    })
    
    if not team:
        print(f"❌ Team not found!")
        return False
    
    print(f"✅ Found team: {team.get('name')}")
    
    # Get inviter details
    inviter = mongodb_service.get_collection('users').find_one({
        "user_id": inviter_user_id
    })
    
    if inviter:
        inviter_name = inviter.get("name", "Nishchal")
        inviter_email = inviter.get("email", "nishchal@prodigalai.com")
        print(f"✅ Inviter: {inviter_name} ({inviter_email})")
    else:
        inviter_name = "Nishchal"
        inviter_email = "nishchal@prodigalai.com"
        print(f"⚠️  Using default inviter: {inviter_name}")
    
    # Check for existing pending invitations
    existing = mongodb_service.get_collection('team_invitations').find_one({
        "team_id": team_id,
        "invited_email": invited_email,
        "status": "pending"
    })
    
    if existing:
        print(f"\n⚠️  Found existing invitation: {existing.get('invitation_id')}")
        print(f"   Updating instead of creating new one...")
        
        # Update existing
        result = mongodb_service.get_collection('team_invitations').update_one(
            {"invitation_id": existing.get('invitation_id')},
            {
                "$set": {
                    "invited_by": inviter_user_id,
                    "invited_by_name": inviter_name,
                    "invited_by_email": inviter_email,
                    "expires_at": datetime.now(timezone.utc).replace(hour=23, minute=59, second=59) + timedelta(days=7),
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        
        if result.modified_count > 0:
            print(f"✅ Updated existing invitation!")
            print(f"\n📋 Invitation Details:")
            print(f"   Invitation ID: {existing.get('invitation_id')}")
            print(f"   Team: {team.get('name')}")
            print(f"   Invited: {invited_email}")
            print(f"   Invited by: {inviter_name} ({inviter_email})")
            print(f"\n📧 Invitation URL:")
            print(f"   https://dhanur-ai-dashboard-omega.vercel.app/teams/invitations/{existing.get('invitation_id')}/accept")
            return True
        else:
            print(f"❌ Failed to update")
            return False
    
    # Create new invitation
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
        "message": "Welcome to the Dhanur AI team!",
        "status": "pending",
        "expires_at": datetime.now(timezone.utc).replace(hour=23, minute=59, second=59) + timedelta(days=7),
        "created_at": datetime.now(timezone.utc)
    }
    
    # Insert
    mongodb_service.get_collection('team_invitations').insert_one(new_invitation)
    
    print(f"\n✅ Created new invitation!")
    print(f"\n📋 Invitation Details:")
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
    print("🚀 Creating new invitation...\n")
    
    try:
        if not mongodb_service.is_connected():
            print("❌ MongoDB not connected")
            sys.exit(1)
        
        print("✅ MongoDB connected\n")
        
        success = create_new_invitation()
        
        if success:
            print("\n✅ Done!")
        else:
            print("\n❌ Failed!")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

