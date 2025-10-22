# Role-Based UI Guide for Team Management

## Overview
This guide explains how to implement role-based UI differences between Owner, Admin, and Member users in the team dashboard.

## User Roles

### 👑 Owner
The creator of the team with full control.

### 👤 Admin  
Assigned by owner, can manage members but cannot delete team.

### 👥 Member
Regular team member with view-only access by default.

---

## API Endpoints

### 1. Get User Capabilities
```http
GET /api/v2/teams/{team_id}/capabilities
Authorization: Bearer {token}
```

**Response:**
```json
{
  "success": true,
  "message": "User capabilities retrieved successfully",
  "data": {
    "team_id": "abc123",
    "user_id": "user123",
    "user_role": "owner",
    "is_owner": true,
    "is_admin": false,
    "capabilities": {
      "can_invite_members": true,
      "can_remove_members": true,
      "can_update_member_roles": true,
      "can_delete_team": true,
      "can_edit_team_details": true,
      "can_assign_brands": true,
      "can_view_brand_assignments": true,
      "can_view_team_analytics": true,
      "can_view_team_details": true,
      "can_view_members_list": true,
      "can_view_performance_reports": true,
      "can_create_projects": true,
      "can_manage_team_settings": true,
      "can_view_pending_invitations": true,
      "can_cancel_invitations": true
    },
    "ui_hints": {
      "show_invite_button": true,
      "show_remove_member_button": true,
      "show_edit_role_button": true,
      "show_delete_team_button": true,
      "show_team_settings": true,
      "show_assign_brand_button": true,
      "show_analytics_tab": true,
      "show_performance_reports": true,
      "show_invite_management": true
    },
    "custom_permissions": {}
  }
}
```

---

## Frontend Implementation

### Step 1: Fetch User Capabilities on Page Load

```javascript
// On team dashboard load
const fetchUserCapabilities = async (teamId) => {
  const response = await fetch(
    `https://dhanur-ai-10fd99bc9730.herokuapp.com/api/v2/teams/${teamId}/capabilities`,
    {
      headers: {
        'Authorization': `Bearer ${userToken}`
      }
    }
  );
  
  const data = await response.json();
  return data.data;
};

// Store in state
const [capabilities, setCapabilities] = useState(null);

useEffect(() => {
  fetchUserCapabilities(teamId).then(setCapabilities);
}, [teamId]);
```

### Step 2: Conditional UI Rendering

```jsx
// Example: Invite Button
{capabilities?.ui_hints.show_invite_button && (
  <button onClick={handleInviteMember}>
    <PlusIcon /> Invite Member
  </button>
)}

// Example: Remove Member Button
{capabilities?.ui_hints.show_remove_member_button && (
  <button onClick={() => handleRemoveMember(memberId)}>
    <TrashIcon /> Remove
  </button>
)}

// Example: Team Settings Tab
{capabilities?.ui_hints.show_team_settings && (
  <Tab label="Settings" />
)}

// Example: Delete Team Button
{capabilities?.ui_hints.show_delete_team_button && (
  <button onClick={handleDeleteTeam} className="danger">
    <TrashIcon /> Delete Team
  </button>
)}
```

### Step 3: Role Badge Display

```jsx
// Show role badge next to user's name
const getRoleBadge = (userRole) => {
  const badges = {
    owner: { text: "Owner", color: "gold", icon: "👑" },
    admin: { text: "Admin", color: "blue", icon: "⭐" },
    member: { text: "Member", color: "gray", icon: "👤" }
  };
  
  const badge = badges[userRole] || badges.member;
  
  return (
    <span className={`badge badge-${badge.color}`}>
      {badge.icon} {badge.text}
    </span>
  );
};

// Usage
{getRoleBadge(capabilities?.user_role)}
```

---

## UI Differences by Role

### Owner Dashboard Features
✅ All features enabled
- Invite members button
- Remove members button
- Edit member roles dropdown
- Delete team button
- Team settings page
- Assign brands button
- Full analytics access
- Performance reports
- Pending invitations management

### Admin Dashboard Features
✅ Most features enabled (except delete team)
- Invite members button
- Remove members button (except owner)
- Edit member roles dropdown
- ❌ Delete team button (hidden)
- Team settings page
- Assign brands button
- Full analytics access
- Performance reports
- Pending invitations management

### Member Dashboard Features
❌ Management features disabled
- ❌ Invite members button (hidden)
- ❌ Remove members button (hidden)
- ❌ Edit member roles dropdown (hidden)
- ❌ Delete team button (hidden)
- ❌ Team settings page (hidden)
- ❌ Assign brands button (hidden)
- ✅ View team details
- ✅ View team members list
- ✅ Limited analytics (own performance only)
- ❌ Performance reports (hidden)
- ❌ Pending invitations (hidden)

---

## Example: Complete Team Dashboard Component

```jsx
import React, { useState, useEffect } from 'react';

const TeamDashboard = ({ teamId }) => {
  const [capabilities, setCapabilities] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchCapabilities = async () => {
      try {
        const response = await fetch(
          `https://dhanur-ai-10fd99bc9730.herokuapp.com/api/v2/teams/${teamId}/capabilities`,
          {
            headers: {
              'Authorization': `Bearer ${localStorage.getItem('token')}`
            }
          }
        );
        const data = await response.json();
        setCapabilities(data.data);
      } catch (error) {
        console.error('Failed to fetch capabilities:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchCapabilities();
  }, [teamId]);

  if (loading) return <div>Loading...</div>;

  return (
    <div className="team-dashboard">
      {/* Header with role badge */}
      <div className="dashboard-header">
        <h1>Team Dashboard</h1>
        <RoleBadge role={capabilities?.user_role} />
      </div>

      {/* Action buttons - shown based on capabilities */}
      <div className="action-buttons">
        {capabilities?.ui_hints.show_invite_button && (
          <button onClick={handleInvite}>
            Invite Member
          </button>
        )}
        
        {capabilities?.ui_hints.show_assign_brand_button && (
          <button onClick={handleAssignBrand}>
            Assign Brand
          </button>
        )}
        
        {capabilities?.ui_hints.show_team_settings && (
          <button onClick={handleSettings}>
            Team Settings
          </button>
        )}
      </div>

      {/* Tabs - shown based on capabilities */}
      <div className="tabs">
        <Tab label="Overview" />
        <Tab label="Members" />
        
        {capabilities?.ui_hints.show_analytics_tab && (
          <Tab label="Analytics" />
        )}
        
        {capabilities?.ui_hints.show_performance_reports && (
          <Tab label="Reports" />
        )}
        
        {capabilities?.ui_hints.show_invite_management && (
          <Tab label="Invitations" />
        )}
        
        {capabilities?.ui_hints.show_team_settings && (
          <Tab label="Settings" />
        )}
      </div>

      {/* Members list with role-based actions */}
      <div className="members-list">
        {members.map(member => (
          <div key={member.user_id} className="member-card">
            <div className="member-info">
              <img src={member.avatar} alt={member.name} />
              <div>
                <h3>{member.name}</h3>
                <p>{member.email}</p>
                <RoleBadge role={member.role} />
              </div>
            </div>
            
            <div className="member-actions">
              {capabilities?.ui_hints.show_edit_role_button && (
                <button onClick={() => handleEditRole(member)}>
                  Edit Role
                </button>
              )}
              
              {capabilities?.ui_hints.show_remove_member_button && 
               member.role !== 'owner' && (
                <button onClick={() => handleRemove(member)}>
                  Remove
                </button>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Danger zone - only for owner */}
      {capabilities?.ui_hints.show_delete_team_button && (
        <div className="danger-zone">
          <h2>Danger Zone</h2>
          <button 
            className="danger-button" 
            onClick={handleDeleteTeam}
          >
            Delete Team
          </button>
        </div>
      )}
    </div>
  );
};

export default TeamDashboard;
```

---

## API Endpoint Summary

| Endpoint | Owner | Admin | Member |
|----------|-------|-------|--------|
| `GET /teams/{team_id}` | ✅ Full details | ✅ Full details | ✅ Basic details |
| `GET /teams/{team_id}/capabilities` | ✅ | ✅ | ✅ |
| `POST /teams/{team_id}/invite` | ✅ | ✅ | ❌ |
| `DELETE /teams/{team_id}/members/{user_id}` | ✅ | ✅ (not owner) | ❌ |
| `PUT /teams/{team_id}/members/{user_id}` | ✅ | ✅ | ❌ |
| `DELETE /teams/{team_id}` | ✅ | ❌ | ❌ |
| `POST /teams/{team_id}/assign-brand` | ✅ | ✅ | ❌ |
| `GET /teams/{team_id}/performance/*` | ✅ Full | ✅ Full | ✅ Own only |

---

## Testing

### Test as Owner
```bash
# Login as owner
TOKEN="owner_jwt_token_here"

# Get capabilities
curl -X GET \
  "https://dhanur-ai-10fd99bc9730.herokuapp.com/api/v2/teams/{team_id}/capabilities" \
  -H "Authorization: Bearer $TOKEN"
```

### Test as Member
```bash
# Login as member
TOKEN="member_jwt_token_here"

# Get capabilities (should show limited access)
curl -X GET \
  "https://dhanur-ai-10fd99bc9730.herokuapp.com/api/v2/teams/{team_id}/capabilities" \
  -H "Authorization: Bearer $TOKEN"
```

---

## Key Points

1. **Always fetch capabilities first** before rendering UI
2. **Use `ui_hints`** for simple show/hide decisions
3. **Use `capabilities`** for more complex permission checks
4. **Show appropriate error messages** when users try unauthorized actions
5. **Update capabilities** after role changes
6. **Cache capabilities** but refresh on navigation or role updates

---

## Error Handling

```javascript
// If user tries action without permission
if (!capabilities?.capabilities.can_invite_members) {
  toast.error("You don't have permission to invite members");
  return;
}

// If API returns 403
catch (error) {
  if (error.status === 403) {
    toast.error("Access denied. You don't have permission for this action.");
  }
}
```

---

## Support

For issues or questions:
- Check API response for detailed error messages
- Verify JWT token is valid and not expired
- Ensure user is authenticated before calling endpoints
- Check team_id is correct



