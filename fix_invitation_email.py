#!/usr/bin/env python3
"""
Fix invitation email to match logged-in user.
"""
import sys
sys.path.append('.')

from services.mongodb_service import mongodb_service

def fix_invitation_email():
    """Update invitation email."""
    
    invitation_id = "d0ce93707015d95a18b60501"
    correct_email = "devlead@dhanurai.com"
    
    print(f"🔍 Looking for invitation: {invitation_id}\n")
    
    # Get invitation
    invitation = mongodb_service.get_collection('team_invitations').find_one({
        "invitation_id": invitation_id
    })
    
    if not invitation:
        print(f"❌ Invitation not found!")
        return False
    
    print(f"📋 Current Details:")
    print(f"   Invited Email: {invitation.get('invited_email')}")
    print(f"   Team: {invitation.get('team_name')}")
    print(f"   Status: {invitation.get('status')}")
    
    print(f"\n🔧 Updating email to: {correct_email}")
    
    # Update invitation
    result = mongodb_service.get_collection('team_invitations').update_one(
        {"invitation_id": invitation_id},
        {"$set": {"invited_email": correct_email}}
    )
    
    if result.modified_count > 0:
        print(f"✅ Invitation updated successfully!")
        
        # Verify
        updated = mongodb_service.get_collection('team_invitations').find_one({
            "invitation_id": invitation_id
        })
        
        print(f"\n✅ Verified:")
        print(f"   Invited Email: {updated.get('invited_email')}")
        print(f"\n👉 Now try accepting the invitation again!")
        print(f"   POST https://dhanur-ai-10fd99bc9730.herokuapp.com/api/v2/teams/invitations/{invitation_id}/accept")
        
        return True
    else:
        print(f"❌ Failed to update (no changes made)")
        return False

if __name__ == "__main__":
    print("🔧 Fixing invitation email...\n")
    
    try:
        if not mongodb_service.is_connected():
            print("❌ MongoDB not connected")
            sys.exit(1)
        
        print("✅ MongoDB connected\n")
        
        success = fix_invitation_email()
        
        if success:
            print("\n✅ Done! Invitation fixed.")
        else:
            print("\n❌ Fix failed!")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

