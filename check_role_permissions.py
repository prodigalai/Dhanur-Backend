#!/usr/bin/env python3
"""
Check what capabilities owner vs member have
"""
import sys
sys.path.append('.')

def check_permissions():
    """Check role-based permissions."""
    
    print("🔐 TEAM ROLE PERMISSIONS\n")
    print("=" * 60)
    
    print("\n👑 OWNER CAPABILITIES:")
    owner_perms = [
        "✅ Invite new members",
        "✅ Remove members",
        "✅ Update member roles",
        "✅ Delete team",
        "✅ Assign team to brands",
        "✅ View all team analytics",
        "✅ Update team details",
        "✅ View team members list",
        "✅ Manage team settings"
    ]
    for perm in owner_perms:
        print(f"   {perm}")
    
    print("\n👤 ADMIN CAPABILITIES:")
    admin_perms = [
        "✅ Invite new members",
        "✅ Remove members (except owner)",
        "✅ Update member roles",
        "❌ Delete team",
        "✅ Assign team to brands",
        "✅ View team analytics",
        "✅ Update team details",
        "✅ View team members list",
        "✅ Manage team settings"
    ]
    for perm in admin_perms:
        print(f"   {perm}")
    
    print("\n👥 MEMBER CAPABILITIES:")
    member_perms = [
        "❌ Invite new members",
        "❌ Remove members",
        "❌ Update member roles",
        "❌ Delete team",
        "❌ Assign team to brands",
        "✅ View team details",
        "✅ View team members list",
        "✅ View own analytics",
        "❌ Manage team settings"
    ]
    for perm in member_perms:
        print(f"   {perm}")
    
    print("\n" + "=" * 60)
    print("\n📋 CURRENT API ENDPOINTS WITH PERMISSION CHECKS:\n")
    
    endpoints = [
        {
            "endpoint": "POST /teams/{team_id}/invite",
            "required_role": "owner or admin",
            "description": "Invite member to team"
        },
        {
            "endpoint": "DELETE /teams/{team_id}/members/{user_id}",
            "required_role": "owner or admin",
            "description": "Remove member from team"
        },
        {
            "endpoint": "PUT /teams/{team_id}/members/{user_id}",
            "required_role": "owner or admin",
            "description": "Update member role/permissions"
        },
        {
            "endpoint": "POST /teams/{team_id}/assign-brand",
            "required_role": "owner or admin",
            "description": "Assign team to brand"
        },
        {
            "endpoint": "GET /teams/{team_id}",
            "required_role": "any member",
            "description": "View team details"
        },
        {
            "endpoint": "GET /teams/{team_id}/members",
            "required_role": "any member",
            "description": "View team members"
        }
    ]
    
    for ep in endpoints:
        print(f"\n   🔹 {ep['endpoint']}")
        print(f"      Role Required: {ep['required_role']}")
        print(f"      Description: {ep['description']}")
    
    print("\n" + "=" * 60)
    print("\n💡 RECOMMENDATION FOR FRONTEND:\n")
    print("   1. Call GET /teams/{team_id} to get user_role")
    print("   2. Based on user_role, show/hide buttons:")
    print("      - If role = 'owner': Show all management buttons")
    print("      - If role = 'admin': Show member management buttons")
    print("      - If role = 'member': Hide all management buttons")
    print("   3. Use user_permissions object for granular control")
    print("\n" + "=" * 60)

if __name__ == "__main__":
    check_permissions()



