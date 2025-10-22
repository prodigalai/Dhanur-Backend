#!/usr/bin/env python3
"""
Send invitation email to devlead.
"""
import sys
import asyncio
sys.path.append('.')

from services.mongodb_service import mongodb_service
from services.email_service import email_service

async def send_invitation_email():
    """Find invitation and send email."""
    
    invited_email = "devlead@prodigalai.com"
    team_id = "65963a7fd00036c8e0397f77"
    
    print(f"🔍 Looking for invitation for {invited_email}...")
    
    # Find invitation
    invitation = mongodb_service.get_collection('team_invitations').find_one({
        "team_id": team_id,
        "invited_email": invited_email,
        "status": "pending"
    })
    
    if not invitation:
        print(f"❌ No pending invitation found for {invited_email}")
        print(f"\n📋 All invitations for this email:")
        all_invites = list(mongodb_service.get_collection('team_invitations').find({
            "invited_email": invited_email
        }))
        for inv in all_invites:
            print(f"   - {inv.get('invitation_id')} - Status: {inv.get('status')} - Team: {inv.get('team_name')}")
        return False
    
    print(f"✅ Found invitation: {invitation.get('invitation_id')}")
    print(f"   Team: {invitation.get('team_name')}")
    print(f"   Status: {invitation.get('status')}")
    print(f"   Invited by: {invitation.get('invited_by_name')} ({invitation.get('invited_by_email')})")
    
    # Check if email service is configured
    if not email_service.is_configured:
        print(f"\n⚠️  Email service is NOT configured!")
        print(f"   Emails cannot be sent without SMTP configuration.")
        print(f"\n📧 Manual invitation URL:")
        invitation_url = f"https://dhanur-ai-dashboard-omega.vercel.app/teams/invitations/{invitation.get('invitation_id')}/accept"
        print(f"   {invitation_url}")
        print(f"\n👉 Copy this URL and send it to {invited_email} manually!")
        return False
    
    print(f"\n✅ Email service is configured")
    print(f"   Sending invitation email...")
    
    # Send email
    invitation_url = f"https://dhanur-ai-dashboard-omega.vercel.app/teams/invitations/{invitation.get('invitation_id')}/accept"
    
    try:
        email_sent = await email_service.send_team_invitation_email(
            to_email=invited_email,
            brand_name=invitation.get('team_name'),
            inviter_name=invitation.get('invited_by_name', 'Team Admin'),
            role=invitation.get('role'),
            message=invitation.get('message', ''),
            invitation_url=invitation_url,
            expires_at=invitation.get('expires_at')
        )
        
        if email_sent:
            print(f"\n✅ Email sent successfully to {invited_email}!")
            return True
        else:
            print(f"\n❌ Failed to send email")
            print(f"\n📧 Manual invitation URL:")
            print(f"   {invitation_url}")
            return False
            
    except Exception as e:
        print(f"\n❌ Error sending email: {e}")
        print(f"\n📧 Manual invitation URL:")
        print(f"   {invitation_url}")
        return False

if __name__ == "__main__":
    print("📧 Sending invitation email...\n")
    
    try:
        if not mongodb_service.is_connected():
            print("❌ MongoDB not connected")
            sys.exit(1)
        
        print("✅ MongoDB connected\n")
        
        # Run async function
        success = asyncio.run(send_invitation_email())
        
        if success:
            print("\n✅ Done!")
        else:
            print("\n⚠️  Email not sent (see details above)")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

