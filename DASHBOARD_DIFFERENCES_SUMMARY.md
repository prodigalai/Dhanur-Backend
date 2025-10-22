# Team Dashboard: Owner vs Member Differences

## 🎯 Quick Summary

**Owner** aur **Member** ka dashboard **bilkul alag** hoga based on their role and permissions.

---

## 📊 Visual Differences

### 👑 OWNER Dashboard
```
┌──────────────────────────────────────────────────┐
│  Team Dashboard            [Owner 👑]            │
├──────────────────────────────────────────────────┤
│                                                  │
│  [+ Invite Member]  [Assign Brand]  [Settings]  │
│                                                  │
│  Tabs:                                          │
│  Overview | Members | Analytics | Reports |     │
│  Invitations | Settings                         │
│                                                  │
│  Members List:                                  │
│  ┌────────────────────────────────────────┐    │
│  │ John Doe (Admin)    [Edit] [Remove]   │    │
│  │ Jane Smith (Member) [Edit] [Remove]   │    │
│  └────────────────────────────────────────┘    │
│                                                  │
│  ⚠️ Danger Zone                                 │
│  [Delete Team] [Transfer Ownership]            │
│                                                  │
└──────────────────────────────────────────────────┘
```

### 👥 MEMBER Dashboard
```
┌──────────────────────────────────────────────────┐
│  Team Dashboard            [Member 👤]           │
├──────────────────────────────────────────────────┤
│                                                  │
│  (No action buttons shown)                      │
│                                                  │
│  Tabs:                                          │
│  Overview | Members                             │
│                                                  │
│  Members List:                                  │
│  ┌────────────────────────────────────────┐    │
│  │ John Doe (Owner)    👑                 │    │
│  │ Jane Smith (Admin)  ⭐                 │    │
│  │ You (Member)        👤                 │    │
│  └────────────────────────────────────────┘    │
│                                                  │
│  (No management options shown)                  │
│                                                  │
└──────────────────────────────────────────────────┘
```

---

## 🔐 Capability Matrix

| Feature | Owner 👑 | Admin 👤 | Member 👥 |
|---------|---------|---------|-----------|
| **Team Management** |
| Invite Members | ✅ | ✅ | ❌ |
| Remove Members | ✅ | ✅ (not owner) | ❌ |
| Edit Member Roles | ✅ | ✅ | ❌ |
| Delete Team | ✅ | ❌ | ❌ |
| Edit Team Details | ✅ | ✅ | ❌ |
| **Brand Management** |
| Assign Brands | ✅ | ✅ | ❌ |
| View Brand Assignments | ✅ | ✅ | ✅ |
| **Analytics** |
| View Team Analytics | ✅ Full | ✅ Full | ✅ Limited |
| View Performance Reports | ✅ | ✅ | ❌ |
| Generate Reports | ✅ | ✅ | ❌ |
| **Settings** |
| Team Settings | ✅ | ✅ | ❌ |
| Manage Invitations | ✅ | ✅ | ❌ |
| View Pending Invites | ✅ | ✅ | ❌ |

---

## 🎨 UI Elements to Show/Hide

### Always Show (All Roles)
- Team name and description
- Members list (read-only for members)
- Team overview stats
- Own profile in team

### Show for Owner & Admin Only
- `[+ Invite Member]` button
- `[Remove]` button next to members
- `[Edit Role]` dropdown
- `[Assign Brand]` button
- `Settings` tab
- `Invitations` tab
- `Reports` tab

### Show for Owner Only
- `[Delete Team]` button
- `[Transfer Ownership]` option
- Team danger zone section

---

## 🔌 New API Endpoint

### Get User Capabilities
```http
GET /api/v2/teams/{team_id}/capabilities
Authorization: Bearer {your_token}
```

**Response Example (Owner):**
```json
{
  "success": true,
  "data": {
    "user_role": "owner",
    "is_owner": true,
    "is_admin": false,
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
    }
  }
}
```

**Response Example (Member):**
```json
{
  "success": true,
  "data": {
    "user_role": "member",
    "is_owner": false,
    "is_admin": false,
    "ui_hints": {
      "show_invite_button": false,
      "show_remove_member_button": false,
      "show_edit_role_button": false,
      "show_delete_team_button": false,
      "show_team_settings": false,
      "show_assign_brand_button": false,
      "show_analytics_tab": true,
      "show_performance_reports": false,
      "show_invite_management": false
    }
  }
}
```

---

## 💻 Frontend Implementation

### Step 1: Fetch Capabilities
```javascript
const { data: capabilities } = await fetch(
  `/api/v2/teams/${teamId}/capabilities`,
  { headers: { 'Authorization': `Bearer ${token}` }}
).then(r => r.json());
```

### Step 2: Use in UI
```jsx
// Simple conditional rendering
{capabilities?.ui_hints.show_invite_button && (
  <button>Invite Member</button>
)}

// Role badge
<Badge color={
  capabilities.is_owner ? 'gold' : 
  capabilities.is_admin ? 'blue' : 
  'gray'
}>
  {capabilities.user_role}
</Badge>
```

---

## ✅ Already Fixed

1. ✅ Invitation email mismatch issue fixed
2. ✅ Role-based permission checks implemented
3. ✅ New `/capabilities` endpoint created
4. ✅ Documentation created

---

## 📝 To Do (Frontend)

1. [ ] Call `/capabilities` endpoint on team page load
2. [ ] Store capabilities in state/context
3. [ ] Hide/show UI elements based on `ui_hints`
4. [ ] Display role badge next to user name
5. [ ] Show appropriate error messages for unauthorized actions
6. [ ] Add role indicator in team cards list

---

## 🧪 Testing

### Test URLs
```bash
# Production
https://dhanur-ai-10fd99bc9730.herokuapp.com/api/v2/teams/{team_id}/capabilities

# Example team_id: Use your actual team ID from the database
```

### Test as Different Roles
1. Login as owner → Should see all buttons
2. Login as member → Should see limited view
3. Try to invite as member → Should get 403 error

---

## 🚀 Deployment Status

- ✅ Backend changes ready
- ✅ API endpoints available
- ⏳ Frontend integration pending

---

## 📞 Support

Issues ho to batao:
1. Token valid hai?
2. Team ID correct hai?
3. User email match kar rahi hai invitation ke saath?

---

**Key Point:** Frontend ko bas `/capabilities` endpoint call karke `ui_hints` use karni hai. Saare permissions backend se automatically aayenge! 🎯



