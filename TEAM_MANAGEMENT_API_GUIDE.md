# 🚀 Team Management API Guide

## Complete Master Team Management System

### 🎯 Overview
This system allows you to create master teams and assign them to different brands with specific permissions. Perfect for managing multiple projects and teams across different brands.

---

## 📋 API Endpoints

### 1. **Create Master Team**
```http
POST /api/v2/teams/create
```

**Request Body:**
```json
{
  "name": "DhanurAI Master Team",
  "description": "Master team for managing all DhanurAI projects",
  "team_type": "master",
  "permissions": {
    "can_invite": true,
    "can_manage_members": true,
    "can_assign_brands": true,
    "can_create_projects": true,
    "can_view_analytics": true
  }
}
```

**Response:**
```json
{
  "success": true,
  "message": "Master team created successfully",
  "data": {
    "team_id": "2f33b1d41e852415252b6934",
    "name": "DhanurAI Master Team",
    "team_type": "master",
    "members_count": 1,
    "created_at": "2025-10-15T14:42:09.663283+00:00"
  }
}
```

---

### 2. **List All Teams**
```http
GET /api/v2/teams
```

**Query Parameters:**
- `team_type` (optional): Filter by team type
- `status` (optional): Filter by status (default: "active")

**Response:**
```json
{
  "success": true,
  "message": "Teams retrieved successfully",
  "data": {
    "teams": [
      {
        "team_id": "2f33b1d41e852415252b6934",
        "name": "DhanurAI Master Team",
        "description": "Master team for managing all DhanurAI projects",
        "team_type": "master",
        "owner_id": "68e9ea30495018434de0a0ec",
        "members_count": 1,
        "brand_assignments_count": 1,
        "user_role": "owner",
        "status": "active",
        "created_at": "2025-10-15T14:42:09.663000",
        "updated_at": "2025-10-15T14:42:09.663000"
      }
    ],
    "total": 1
  }
}
```

---

### 3. **Get Team Details**
```http
GET /api/v2/teams/{team_id}
```

**Response:**
```json
{
  "success": true,
  "message": "Team details retrieved successfully",
  "data": {
    "team_id": "2f33b1d41e852415252b6934",
    "name": "DhanurAI Master Team",
    "description": "Master team for managing all DhanurAI projects",
    "team_type": "master",
    "owner_id": "68e9ea30495018434de0a0ec",
    "permissions": {
      "can_invite": true,
      "can_manage_members": true,
      "can_assign_brands": true,
      "can_create_projects": true,
      "can_view_analytics": true
    },
    "members": [
      {
        "user_id": "68e9ea30495018434de0a0ec",
        "name": "Ashwini Nagargoje",
        "email": "ashwininagargoj703@gmail.com",
        "role": "owner",
        "permissions": {
          "can_invite": true,
          "can_manage_members": true,
          "can_assign_brands": true,
          "can_create_projects": true,
          "can_delete_team": true
        },
        "joined_at": "2025-10-15T14:42:09.663000",
        "status": "active"
      }
    ],
    "brand_assignments": [
      {
        "brand_id": "68ea3a010ea62ad7022bcf5b",
        "brand_name": "DhanurAI core",
        "role": "admin",
        "assigned_at": "2025-10-15T14:42:39.288000",
        "status": "active"
      }
    ],
    "user_role": "owner",
    "status": "active",
    "created_at": "2025-10-15T14:42:09.663000",
    "updated_at": "2025-10-15T14:42:39.288000"
  }
}
```

---

### 4. **Invite Team Member**
```http
POST /api/v2/teams/{team_id}/invite
```

**Request Body:**
```json
{
  "email": "newmember@example.com",
  "role": "member",
  "permissions": {
    "can_view_analytics": true,
    "can_manage_tasks": true
  },
  "message": "Welcome to our team! You'll have access to manage tasks and view analytics."
}
```

**Response:**
```json
{
  "success": true,
  "message": "Invitation sent successfully",
  "data": {
    "invitation_id": "0251ab8f2504ba804bd25b8d",
    "team_name": "DhanurAI Master Team",
    "invited_email": "newmember@example.com",
    "role": "member",
    "expires_at": "2025-10-22T23:59:59.627305+00:00"
  }
}
```

---

### 5. **Accept Team Invitation**
```http
POST /api/v2/teams/invitations/{invitation_id}/accept
```

**Response:**
```json
{
  "success": true,
  "message": "Successfully joined the team",
  "data": {
    "team_id": "2f33b1d41e852415252b6934",
    "team_name": "DhanurAI Master Team",
    "role": "member"
  }
}
```

---

### 6. **Assign Team to Brand**
```http
POST /api/v2/teams/{team_id}/assign-brand
```

**Request Body:**
```json
{
  "brand_id": "68ea3a010ea62ad7022bcf5b",
  "role": "admin",
  "permissions": {
    "can_manage_campaigns": true,
    "can_manage_tasks": true,
    "can_invite_members": true,
    "can_view_analytics": true
  }
}
```

**Response:**
```json
{
  "success": true,
  "message": "Team successfully assigned to brand",
  "data": {
    "team_id": "2f33b1d41e852415252b6934",
    "brand_id": "68ea3a010ea62ad7022bcf5b",
    "brand_name": "DhanurAI core",
    "assigned_members": [
      {
        "user_id": "68e9ea30495018434de0a0ec",
        "role": "admin"
      }
    ],
    "total_assigned": 1
  }
}
```

---

### 7. **Get Team Brand Assignments**
```http
GET /api/v2/teams/{team_id}/brands
```

**Response:**
```json
{
  "success": true,
  "message": "Brand assignments retrieved successfully",
  "data": {
    "team_id": "2f33b1d41e852415252b6934",
    "team_name": "DhanurAI Master Team",
    "brand_assignments": [
      {
        "brand_id": "68ea3a010ea62ad7022bcf5b",
        "brand_name": "DhanurAI core",
        "brand_description": "Dhanur Core Team",
        "role": "admin",
        "assigned_at": "2025-10-15T14:42:39.288000",
        "status": "active"
      }
    ],
    "total_assignments": 1
  }
}
```

---

### 8. **Get Team Permissions**
```http
GET /api/v2/teams/{team_id}/permissions
```

**Response:**
```json
{
  "success": true,
  "message": "Permissions retrieved successfully",
  "data": {
    "team_id": "2f33b1d41e852415252b6934",
    "user_role": "owner",
    "user_permissions": {
      "can_invite": true,
      "can_manage_members": true,
      "can_assign_brands": true,
      "can_create_projects": true,
      "can_delete_team": true
    },
    "available_permissions": {
      "can_invite": "Invite new members to team",
      "can_manage_members": "Manage existing team members",
      "can_assign_brands": "Assign team to brands",
      "can_create_projects": "Create new projects",
      "can_delete_team": "Delete the team (owner only)",
      "can_edit_team": "Edit team details",
      "can_view_analytics": "View team analytics"
    }
  }
}
```

---

### 9. **Get Pending Invitations**
```http
GET /api/v2/teams/invitations/pending
```

**Response:**
```json
{
  "success": true,
  "message": "Pending invitations retrieved successfully",
  "data": {
    "invitations": [
      {
        "invitation_id": "0251ab8f2504ba804bd25b8d",
        "team_id": "2f33b1d41e852415252b6934",
        "team_name": "DhanurAI Master Team",
        "role": "member",
        "message": "Welcome to our team!",
        "invited_by": "68e9ea30495018434de0a0ec",
        "expires_at": "2025-10-22T23:59:59.627305+00:00",
        "created_at": "2025-10-15T14:42:39.288000"
      }
    ],
    "total": 1
  }
}
```

---

## 🔐 Authentication

All endpoints require JWT authentication:
```http
Authorization: Bearer <your_jwt_token>
```

---

## 🎯 Use Cases

### 1. **Create Master Team**
- Create a master team for your organization
- Set default permissions for all members
- Automatically become the owner

### 2. **Invite Team Members**
- Send email invitations to new members
- Set custom roles and permissions
- Include personal messages

### 3. **Assign to Brands**
- Assign entire team to specific brands
- Set brand-specific roles and permissions
- Manage multiple brand assignments

### 4. **Permission Management**
- Granular permission control
- Role-based access (owner, admin, member, viewer)
- Brand-specific permissions

---

## 🚀 Frontend Integration Examples

### **Create Team (React)**
```javascript
const createTeam = async (teamData) => {
  const response = await fetch('/api/v2/teams/create', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify(teamData)
  });
  return await response.json();
};
```

### **Assign Team to Brand (React)**
```javascript
const assignToBrand = async (teamId, brandId, role, permissions) => {
  const response = await fetch(`/api/v2/teams/${teamId}/assign-brand`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({
      brand_id: brandId,
      role: role,
      permissions: permissions
    })
  });
  return await response.json();
};
```

### **Invite Member (React)**
```javascript
const inviteMember = async (teamId, email, role, message) => {
  const response = await fetch(`/api/v2/teams/${teamId}/invite`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({
      email: email,
      role: role,
      message: message
    })
  });
  return await response.json();
};
```

---

## 📊 Database Collections

### **master_teams**
- Stores team information
- Contains members array
- Tracks brand assignments

### **team_invitations**
- Stores pending invitations
- Tracks invitation status
- Manages expiration

---

## ✅ Features

- ✅ **Master Team Creation**
- ✅ **Member Invitation System**
- ✅ **Brand Assignment Management**
- ✅ **Permission Control**
- ✅ **Role-based Access**
- ✅ **Invitation Expiration**
- ✅ **Team Analytics**
- ✅ **Multi-brand Support**

---

**🎉 Your complete team management system is ready!** 

Now you can create master teams, invite members, and assign them to different brands with specific permissions. Perfect for managing multiple projects and teams across your organization!
