#!/usr/bin/env python3
"""
Check invitation details.
"""
import sys
sys.path.append('.')

from services.mongodb_service import mongodb_service

def check_invitation():
    """Check invitation details."""
    
    invitation_id = "2afb78eb89577e9e4aaa3d4e"
    logged_in_email = "devlead@dhanurai.com"
    
    print(f"🔍 Checking invitation: {invitation_id}\n")
    
    # Get invitation
    invitation = mongodb_service.get_collection('team_invitations').find_one({
        "invitation_id": invitation_id
    })
    
    if not invitation:
        print(f"❌ Invitation not found!")
        return
    
    print(f"📋 Invitation Details:")
    print(f"   Invitation ID: {invitation.get('invitation_id')}")
    print(f"   Team: {invitation.get('team_name')}")
    print(f"   Invited Email: {invitation.get('invited_email')}")
    print(f"   Status: {invitation.get('status')}")
    print(f"   Role: {invitation.get('role')}")
    print(f"   Invited by: {invitation.get('invited_by_name')} ({invitation.get('invited_by_email')})")
    
    print(f"\n👤 Logged-in User:")
    print(f"   Email: {logged_in_email}")
    
    print(f"\n🔐 Access Check:")
    if invitation.get('invited_email') == logged_in_email:
        print(f"   ✅ Email matches! User can accept this invitation.")
    else:
        print(f"   ❌ Email mismatch!")
        print(f"      Invited: {invitation.get('invited_email')}")
        print(f"      Logged-in: {logged_in_email}")
        print(f"      👉 This is why you're getting 403 Forbidden!")
        
        print(f"\n💡 Solutions:")
        print(f"   1. Login with email: {invitation.get('invited_email')}")
        print(f"   2. OR create a new invitation for: {logged_in_email}")

if __name__ == "__main__":
    print("🔍 Checking invitation...\n")
    
    try:
        if not mongodb_service.is_connected():
            print("❌ MongoDB not connected")
            sys.exit(1)
        
        check_invitation()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

