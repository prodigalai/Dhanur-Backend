#!/usr/bin/env python3
"""
Fix invitation email for invitation 2afb78eb89577e9e4aaa3d4e
"""
import sys
sys.path.append('.')

from services.mongodb_service import mongodb_service

def fix_invitation_email():
    """Fix the invitation email."""
    
    invitation_id = "2afb78eb89577e9e4aaa3d4e"
    correct_email = "devlead@dhanurai.com"
    
    print(f"🔧 Fixing invitation: {invitation_id}\n")
    
    # Get invitation
    invitation = mongodb_service.get_collection('team_invitations').find_one({
        "invitation_id": invitation_id
    })
    
    if not invitation:
        print(f"❌ Invitation not found!")
        return
    
    print(f"📋 Current Details:")
    print(f"   Invitation ID: {invitation.get('invitation_id')}")
    print(f"   Team: {invitation.get('team_name')}")
    print(f"   Current Email: {invitation.get('invited_email')}")
    print(f"   Status: {invitation.get('status')}")
    
    # Update the invitation
    result = mongodb_service.get_collection('team_invitations').update_one(
        {"invitation_id": invitation_id},
        {"$set": {"invited_email": correct_email}}
    )
    
    if result.modified_count > 0:
        print(f"\n✅ Successfully updated invitation email to: {correct_email}")
        
        # Verify the update
        updated_invitation = mongodb_service.get_collection('team_invitations').find_one({
            "invitation_id": invitation_id
        })
        print(f"\n📋 Updated Details:")
        print(f"   Invitation ID: {updated_invitation.get('invitation_id')}")
        print(f"   Team: {updated_invitation.get('team_name')}")
        print(f"   New Email: {updated_invitation.get('invited_email')}")
        print(f"   Status: {updated_invitation.get('status')}")
        print(f"\n🎉 You can now accept the invitation!")
    else:
        print(f"\n⚠️ No changes made. Email might already be correct.")

if __name__ == "__main__":
    print("🔧 Fixing invitation email...\n")
    
    try:
        if not mongodb_service.is_connected():
            print("❌ MongoDB not connected")
            sys.exit(1)
        
        fix_invitation_email()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

