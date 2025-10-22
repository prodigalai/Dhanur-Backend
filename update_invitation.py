#!/usr/bin/env python3
"""
Simple script to update invitation with inviter name.
"""
import sys
sys.path.append('.')

from services.mongodb_service import mongodb_service

def update_invitation():
    """Update invitation with inviter details."""
    
    invitation_id = "be3b41e9e822be866065e03c"
    inviter_user_id = "dc9b07d3ee00e42b9343341699dec7a2"
    
    print(f"🔍 Looking for invitation: {invitation_id}")
    
    # Get invitation
    invitation = mongodb_service.get_collection('team_invitations').find_one({
        "invitation_id": invitation_id
    })
    
    if not invitation:
        print(f"❌ Invitation not found!")
        return False
    
    print(f"✅ Found invitation for: {invitation.get('invited_email')}")
    print(f"   Current invited_by_name: {invitation.get('invited_by_name')}")
    
    # Get inviter details from users collection
    inviter = mongodb_service.get_collection('users').find_one({
        "user_id": inviter_user_id
    })
    
    if inviter:
        inviter_name = inviter.get("name", "Nishchal")
        inviter_email = inviter.get("email", "nishchal@prodigalai.com")
        print(f"✅ Found inviter: {inviter_name} ({inviter_email})")
    else:
        inviter_name = "Nishchal"
        inviter_email = "nishchal@prodigalai.com"
        print(f"⚠️  Inviter not found in DB, using default: {inviter_name}")
    
    # Update invitation
    result = mongodb_service.get_collection('team_invitations').update_one(
        {"invitation_id": invitation_id},
        {
            "$set": {
                "invited_by_name": inviter_name,
                "invited_by_email": inviter_email
            }
        }
    )
    
    if result.modified_count > 0:
        print(f"\n✅ Invitation updated successfully!")
        print(f"   invited_by_name: {inviter_name}")
        print(f"   invited_by_email: {inviter_email}")
        
        # Verify update
        updated_invitation = mongodb_service.get_collection('team_invitations').find_one({
            "invitation_id": invitation_id
        })
        print(f"\n✅ Verified:")
        print(f"   invited_by_name: {updated_invitation.get('invited_by_name')}")
        print(f"   invited_by_email: {updated_invitation.get('invited_by_email')}")
        
        return True
    else:
        print(f"❌ Failed to update invitation")
        return False

if __name__ == "__main__":
    print("🚀 Starting invitation update...\n")
    
    try:
        if not mongodb_service.is_connected():
            print("❌ MongoDB not connected")
            sys.exit(1)
        
        print("✅ MongoDB connected\n")
        
        success = update_invitation()
        
        if success:
            print("\n✅ Done! Invitation updated.")
            print("📧 Test the API now:")
            print("   GET https://dhanur-ai-10fd99bc9730.herokuapp.com/api/v2/teams/invitations/be3b41e9e822be866065e03c")
        else:
            print("\n❌ Update failed!")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

