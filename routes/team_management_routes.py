#!/usr/bin/env python3
"""
Team Management Routes for Content Crew Prodigal
Master Team Management System
"""

import logging
import secrets
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel, Field
from datetime import datetime, timezone, timedelta
import secrets

from middleware.auth import get_current_user
from services.mongodb_service import mongodb_service
from services.email_service import email_service

logger = logging.getLogger(__name__)
router = APIRouter()

# Ensure collections exist on startup
def ensure_collections_exist():
    """Ensure required collections exist."""
    try:
        # Create collections if they don't exist
        collections = ['master_teams', 'team_invitations']
        for collection_name in collections:
            collection = mongodb_service.get_collection(collection_name)
            # Just accessing the collection creates it if it doesn't exist
            collection.find_one()
        logger.info("Team management collections ensured")
    except Exception as e:
        logger.error(f"Error ensuring collections: {e}")

# Call this on module import
ensure_collections_exist()

# =====================================================
# TEAM MANAGEMENT MODELS
# =====================================================

class TeamCreateRequest(BaseModel):
    name: str = Field(..., description="Team name", min_length=2, max_length=100)
    description: Optional[str] = Field(None, description="Team description", max_length=500)
    team_type: str = Field("master", description="Team type: master, project, department")
    permissions: Optional[Dict[str, Any]] = Field(None, description="Default permissions for team members")

class TeamUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, description="Team name", min_length=2, max_length=100)
    description: Optional[str] = Field(None, description="Team description", max_length=500)
    permissions: Optional[Dict[str, Any]] = Field(None, description="Team permissions")
    status: Optional[str] = Field(None, description="Team status: active, inactive, archived")

class TeamMemberInviteRequest(BaseModel):
    email: str = Field(..., description="Email of user to invite")
    role: str = Field("member", description="Role in team: admin, member, viewer")
    permissions: Optional[Dict[str, Any]] = Field(None, description="Custom permissions for this member")
    message: Optional[str] = Field(None, description="Personal message for invitation")

class TeamMemberUpdateRequest(BaseModel):
    role: Optional[str] = Field(None, description="New role: admin, member, viewer")
    permissions: Optional[Dict[str, Any]] = Field(None, description="Updated permissions")
    status: Optional[str] = Field(None, description="Member status: active, inactive, suspended")

class BrandAssignmentRequest(BaseModel):
    brand_id: str = Field(..., description="Brand ID to assign team to")
    role: str = Field("member", description="Role in brand: owner, admin, editor, viewer")
    permissions: Optional[Dict[str, Any]] = Field(None, description="Brand-specific permissions")

# =====================================================
# MASTER TEAM MANAGEMENT
# =====================================================

@router.post("/teams/create", response_model=Dict[str, Any])
async def create_master_team(
    request: TeamCreateRequest,
    current_user: dict = Depends(get_current_user)
):
    """Create a master team."""
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        # Allow users to create multiple teams
        # No restriction on number of teams per user
        
        # Create team document
        team_doc = {
            "team_id": secrets.token_hex(12),
            "name": request.name,
            "description": request.description,
            "team_type": request.team_type,
            "owner_id": user_id,
            "permissions": request.permissions or {
                "can_invite": True,
                "can_manage_members": True,
                "can_assign_brands": True,
                "can_create_projects": True
            },
            "members": [{
                "user_id": user_id,
                "role": "owner",
                "permissions": {
                    "can_invite": True,
                    "can_manage_members": True,
                    "can_assign_brands": True,
                    "can_create_projects": True,
                    "can_delete_team": True
                },
                "joined_at": datetime.now(timezone.utc),
                "status": "active"
            }],
            "brand_assignments": [],
            "status": "active",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        
        mongodb_service.get_collection('master_teams').insert_one(team_doc)
        
        logger.info(f"Created master team: {team_doc['team_id']} by user {user_id}")
        
        return {
            "success": True,
            "message": "Master team created successfully",
            "data": {
                "team_id": team_doc["team_id"],
                "name": team_doc["name"],
                "team_type": team_doc["team_type"],
                "members_count": len(team_doc["members"]),
                "created_at": team_doc["created_at"].isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating master team: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create team: {str(e)}")

@router.get("/teams", response_model=Dict[str, Any])
async def list_user_teams(
    current_user: dict = Depends(get_current_user),
    team_type: Optional[str] = Query(None, description="Filter by team type"),
    status: Optional[str] = Query("active", description="Filter by status")
):
    """List all teams for the current user."""
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        # Build query
        query = {
            "$or": [
                {"owner_id": user_id},
                {"members.user_id": user_id}
            ]
        }
        
        if team_type:
            query["team_type"] = team_type
        if status:
            query["status"] = status
        
        # Get teams
        teams = list(mongodb_service.get_collection('master_teams').find(query))
        
        # Format response
        formatted_teams = []
        for team in teams:
            # Get user's role in this team
            user_role = "owner" if team.get("owner_id") == user_id else "member"
            if user_role == "member":
                for member in team.get("members", []):
                    if member.get("user_id") == user_id:
                        user_role = member.get("role", "member")
                        break
            
            formatted_teams.append({
                "team_id": team.get("team_id"),
                "name": team.get("name"),
                "description": team.get("description"),
                "team_type": team.get("team_type"),
                "owner_id": team.get("owner_id"),
                "members_count": len(team.get("members", [])),
                "brand_assignments_count": len(team.get("brand_assignments", [])),
                "user_role": user_role,
                "status": team.get("status"),
                "created_at": team.get("created_at").isoformat() if team.get("created_at") else None,
                "updated_at": team.get("updated_at").isoformat() if team.get("updated_at") else None
            })
        
        return {
            "success": True,
            "message": "Teams retrieved successfully",
            "data": {
                "teams": formatted_teams,
                "total": len(formatted_teams)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing teams: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list teams: {str(e)}")

@router.get("/teams/{team_id}", response_model=Dict[str, Any])
async def get_team_details(
    team_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get detailed information about a specific team."""
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        # Get team
        team = mongodb_service.get_collection('master_teams').find_one({
            "team_id": team_id,
            "$or": [
                {"owner_id": user_id},
                {"members.user_id": user_id}
            ]
        })
        
        if not team:
            raise HTTPException(status_code=404, detail="Team not found or access denied")
        
        # Get user's role
        user_role = "owner" if team.get("owner_id") == user_id else "member"
        if user_role == "member":
            for member in team.get("members", []):
                if member.get("user_id") == user_id:
                    user_role = member.get("role", "member")
                    break
        
        # Get member details with names
        members_with_names = []
        for member in team.get("members", []):
            user_info = mongodb_service.get_collection('users').find_one({
                "user_id": member.get("user_id")
            })
            
            member_info = {
                "user_id": member.get("user_id"),
                "name": user_info.get("name") if user_info else "Unknown User",
                "email": user_info.get("email") if user_info else "Unknown Email",
                "role": member.get("role"),
                "permissions": member.get("permissions", {}),
                "joined_at": member.get("joined_at").isoformat() if member.get("joined_at") else None,
                "status": member.get("status")
            }
            members_with_names.append(member_info)
        
        return {
            "success": True,
            "message": "Team details retrieved successfully",
            "data": {
                "team_id": team.get("team_id"),
                "name": team.get("name"),
                "description": team.get("description"),
                "team_type": team.get("team_type"),
                "owner_id": team.get("owner_id"),
                "permissions": team.get("permissions", {}),
                "members": members_with_names,
                "brand_assignments": team.get("brand_assignments", []),
                "user_role": user_role,
                "status": team.get("status"),
                "created_at": team.get("created_at").isoformat() if team.get("created_at") else None,
                "updated_at": team.get("updated_at").isoformat() if team.get("updated_at") else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting team details: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get team details: {str(e)}")

# =====================================================
# TEAM MEMBER MANAGEMENT
# =====================================================

@router.post("/teams/{team_id}/invite", response_model=Dict[str, Any])
async def invite_team_member(
    team_id: str,
    request: TeamMemberInviteRequest,
    current_user: dict = Depends(get_current_user)
):
    """Invite a user to join the team."""
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        # Check if user has permission to invite
        team = mongodb_service.get_collection('master_teams').find_one({
            "team_id": team_id,
            "$or": [
                {"owner_id": user_id},
                {"members": {"$elemMatch": {"user_id": user_id, "role": "admin"}}}
            ]
        })
        
        if not team:
            raise HTTPException(status_code=404, detail="Team not found or insufficient permissions")
        
        # Check if user is already a member
        existing_member = any(
            member.get("user_id") == request.email or 
            (mongodb_service.get_collection('users').find_one({"email": request.email}) and 
             member.get("user_id") == mongodb_service.get_collection('users').find_one({"email": request.email}).get("user_id"))
            for member in team.get("members", [])
        )
        
        if existing_member:
            raise HTTPException(status_code=400, detail="User is already a team member")
        
        # First, clean up any expired invitations for this email
        mongodb_service.get_collection('team_invitations').delete_many({
            "team_id": team_id,
            "invited_email": request.email,
            "status": "pending",
            "expires_at": {"$lte": datetime.now(timezone.utc)}
        })
        
        # Check if there's already a pending invitation for this email
        existing_invitation = mongodb_service.get_collection('team_invitations').find_one({
            "team_id": team_id,
            "invited_email": request.email,
            "status": "pending"
        })
        
        logger.info(f"Checking for existing invitation for {request.email} in team {team_id}")
        logger.info(f"Found existing invitation: {existing_invitation}")
        
        if existing_invitation:
            # Get inviter's name for update
            inviter = mongodb_service.get_collection('users').find_one({"user_id": user_id})
            inviter_name = inviter.get("name") if inviter else current_user.get("name", "Unknown User")
            inviter_email = inviter.get("email") if inviter else current_user.get("email", "")
            
            # Update existing invitation instead of creating duplicate
            update_data = {
                "role": request.role,
                "permissions": request.permissions or team.get("permissions", {}),
                "message": request.message,
                "invited_by": user_id,
                "invited_by_name": inviter_name,
                "invited_by_email": inviter_email,
                "expires_at": datetime.now(timezone.utc).replace(hour=23, minute=59, second=59) + timedelta(days=7),
                "updated_at": datetime.now(timezone.utc)
            }
            
            mongodb_service.get_collection('team_invitations').update_one(
                {"invitation_id": existing_invitation["invitation_id"]},
                {"$set": update_data}
            )
            
            # Send updated invitation email
            try:
                inviter_user = mongodb_service.get_collection('users').find_one({
                    "user_id": user_id
                })
                inviter_name = inviter_user.get("name") if inviter_user else "Team Admin"
                
                invitation_url = f"https://dhanur-ai-dashboard-omega.vercel.app/teams/invitations/{existing_invitation['invitation_id']}/accept"
                
                logger.info(f"Attempting to send updated team invitation email to {request.email}")
                logger.info(f"Email service configured: {email_service.is_configured}")
                
                email_sent = await email_service.send_team_invitation_email(
                    to_email=request.email,
                    brand_name=team.get("name"),
                    inviter_name=inviter_name,
                    role=request.role,
                    message=request.message or "",
                    invitation_url=invitation_url,
                    expires_at=update_data["expires_at"]
                )
                
                logger.info(f"Updated email sending result: {email_sent}")
                
                if email_sent:
                    logger.info(f"Updated team invitation email sent to {request.email}")
                else:
                    logger.warning(f"Failed to send updated invitation email to {request.email}")
            except Exception as e:
                logger.error(f"Error sending updated invitation email: {e}")
            
            return {
                "success": True,
                "message": "Invitation updated successfully",
                "data": {
                    "invitation_id": existing_invitation["invitation_id"],
                    "team_name": team.get("name"),
                    "invited_email": request.email,
                    "role": request.role,
                    "expires_at": update_data["expires_at"].isoformat(),
                    "email_sent": True,
                    "updated": True
                }
            }
        
        # Get inviter's name
        inviter = mongodb_service.get_collection('users').find_one({"user_id": user_id})
        inviter_name = inviter.get("name") if inviter else current_user.get("name", "Unknown User")
        inviter_email = inviter.get("email") if inviter else current_user.get("email", "")
        
        # Create invitation
        invitation_doc = {
            "invitation_id": secrets.token_hex(12),
            "team_id": team_id,
            "team_name": team.get("name"),
            "invited_email": request.email,
            "invited_by": user_id,
            "invited_by_name": inviter_name,
            "invited_by_email": inviter_email,
            "role": request.role,
            "permissions": request.permissions or team.get("permissions", {}),
            "message": request.message,
            "status": "pending",
            "expires_at": datetime.now(timezone.utc).replace(hour=23, minute=59, second=59) + timedelta(days=7),
            "created_at": datetime.now(timezone.utc)
        }
        
        mongodb_service.get_collection('team_invitations').insert_one(invitation_doc)
        
        # Send invitation email
        try:
            # Get inviter name
            inviter_user = mongodb_service.get_collection('users').find_one({
                "user_id": user_id
            })
            inviter_name = inviter_user.get("name") if inviter_user else "Team Admin"
            
            # Create invitation URL
            invitation_url = f"https://dhanur-ai-dashboard-omega.vercel.app/teams/invitations/{invitation_doc['invitation_id']}/accept"
            
            # Send email
            logger.info(f"Attempting to send team invitation email to {request.email}")
            logger.info(f"Email service configured: {email_service.is_configured}")
            
            email_sent = await email_service.send_team_invitation_email(
                to_email=request.email,
                brand_name=team.get("name"),
                inviter_name=inviter_name,
                role=request.role,
                message=request.message or "",
                invitation_url=invitation_url,
                expires_at=invitation_doc["expires_at"]
            )
            
            logger.info(f"Email sending result: {email_sent}")
            
            if email_sent:
                logger.info(f"Team invitation email sent to {request.email}")
            else:
                logger.warning(f"Failed to send invitation email to {request.email}")
                
        except Exception as e:
            logger.error(f"Error sending invitation email: {e}")
            # Don't fail the invitation if email fails
        
        logger.info(f"Created team invitation: {invitation_doc['invitation_id']} for {request.email}")
        
        return {
            "success": True,
            "message": "Invitation sent successfully",
            "data": {
                "invitation_id": invitation_doc["invitation_id"],
                "team_name": team.get("name"),
                "invited_email": request.email,
                "role": request.role,
                "expires_at": invitation_doc["expires_at"].isoformat(),
                "email_sent": True
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error inviting team member: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to invite member: {str(e)}")

@router.post("/teams/invitations/{invitation_id}/accept", response_model=Dict[str, Any])
async def accept_team_invitation(
    invitation_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Accept a team invitation."""
    try:
        # Debug logging
        logger.info(f"Accept invitation request - invitation_id: {invitation_id}")
        logger.info(f"Current user data: {current_user}")
        
        # Try multiple ways to get user_id for compatibility
        user_id = (
            current_user.get("user_id") or 
            current_user.get("id") or 
            current_user.get("sub") or 
            current_user.get("entity_id")
        )
        user_email = current_user.get("email")
        
        logger.info(f"Extracted user_id: {user_id}, email: {user_email}")
        
        if not user_id:
            logger.error(f"No user_id found in current_user: {current_user}")
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        # Get invitation
        logger.info(f"Looking for invitation with ID: {invitation_id}")
        invitation = mongodb_service.get_collection('team_invitations').find_one({
            "invitation_id": invitation_id,
            "status": "pending"
        })
        
        if not invitation:
            # Check if invitation exists but with different status
            all_invitations = list(mongodb_service.get_collection('team_invitations').find({
                "invitation_id": invitation_id
            }))
            logger.error(f"No pending invitation found. All invitations with this ID: {all_invitations}")
            raise HTTPException(status_code=404, detail="Invitation not found or expired")
        
        logger.info(f"Found invitation: {invitation}")
        
        # Check if invitation is for this user
        if invitation.get("invited_email") != user_email:
            raise HTTPException(status_code=403, detail="This invitation is not for you")
        
        # Check if invitation is expired
        if invitation.get("expires_at"):
            expires_at = invitation.get("expires_at")
            # Handle both timezone-aware and naive datetimes
            if hasattr(expires_at, 'tzinfo') and expires_at.tzinfo is not None:
                # Timezone-aware datetime
                if expires_at < datetime.now(timezone.utc):
                    raise HTTPException(status_code=400, detail="Invitation has expired")
            else:
                # Naive datetime, assume UTC
                if expires_at < datetime.now(timezone.utc).replace(tzinfo=None):
                    raise HTTPException(status_code=400, detail="Invitation has expired")
        
        # Add user to team
        team_id = invitation.get("team_id")
        logger.info(f"Looking for team with ID: {team_id}")
        team = mongodb_service.get_collection('master_teams').find_one({
            "team_id": team_id
        })
        
        if not team:
            logger.error(f"Team not found with ID: {team_id}")
            raise HTTPException(status_code=404, detail="Team not found")
        
        logger.info(f"Found team: {team.get('name', 'Unknown')}")
        
        # Add member to team
        new_member = {
            "user_id": user_id,
            "role": invitation.get("role"),
            "permissions": invitation.get("permissions", {}),
            "joined_at": datetime.now(timezone.utc),
            "status": "active"
        }
        
        logger.info(f"Adding member to team: {new_member}")
        
        # Add member to team
        team_update_result = mongodb_service.get_collection('master_teams').update_one(
            {"team_id": team_id},
            {"$push": {"members": new_member}}
        )
        
        if team_update_result.modified_count == 0:
            logger.error(f"Failed to add member to team {team_id}")
            raise HTTPException(status_code=500, detail="Failed to add member to team")
        
        logger.info(f"Successfully added member to team {team_id}")
        
        # Update invitation status
        invitation_update_result = mongodb_service.get_collection('team_invitations').update_one(
            {"invitation_id": invitation_id},
            {"$set": {"status": "accepted", "accepted_at": datetime.now(timezone.utc)}}
        )
        
        if invitation_update_result.modified_count == 0:
            logger.error(f"Failed to update invitation status for {invitation_id}")
            # Don't fail here as the member was already added to the team
        
        logger.info(f"User {user_id} accepted invitation to team {invitation.get('team_id')}")
        
        return {
            "success": True,
            "message": "Successfully joined the team",
            "data": {
                "team_id": invitation.get("team_id"),
                "team_name": invitation.get("team_name"),
                "role": invitation.get("role")
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error accepting invitation: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to accept invitation: {str(e)}")

@router.post("/teams/invitations/{invitation_id}/decline", response_model=Dict[str, Any])
async def decline_team_invitation(
    invitation_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Decline a team invitation."""
    try:
        # Debug logging
        logger.info(f"Decline invitation request - invitation_id: {invitation_id}")
        logger.info(f"Current user data: {current_user}")
        
        # Try multiple ways to get user_id for compatibility
        user_id = (
            current_user.get("user_id") or 
            current_user.get("id") or 
            current_user.get("sub") or 
            current_user.get("entity_id")
        )
        user_email = current_user.get("email")
        
        logger.info(f"Extracted user_id: {user_id}, email: {user_email}")
        
        if not user_id:
            logger.error(f"No user_id found in current_user: {current_user}")
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        # Get invitation
        logger.info(f"Looking for invitation with ID: {invitation_id}")
        invitation = mongodb_service.get_collection('team_invitations').find_one({
            "invitation_id": invitation_id,
            "status": "pending"
        })
        
        if not invitation:
            # Check if invitation exists but with different status
            all_invitations = list(mongodb_service.get_collection('team_invitations').find({
                "invitation_id": invitation_id
            }))
            logger.error(f"No pending invitation found. All invitations with this ID: {all_invitations}")
            raise HTTPException(status_code=404, detail="Invitation not found or already processed")
        
        logger.info(f"Found invitation: {invitation}")
        
        # Check if invitation is for this user
        if invitation.get("invited_email") != user_email:
            raise HTTPException(status_code=403, detail="This invitation is not for you")
        
        # Update invitation status to declined
        invitation_update_result = mongodb_service.get_collection('team_invitations').update_one(
            {"invitation_id": invitation_id},
            {"$set": {"status": "declined", "declined_at": datetime.now(timezone.utc), "declined_by": user_id}}
        )
        
        if invitation_update_result.modified_count == 0:
            logger.error(f"Failed to update invitation status for {invitation_id}")
            raise HTTPException(status_code=500, detail="Failed to decline invitation")
        
        logger.info(f"User {user_id} declined invitation to team {invitation.get('team_id')}")
        
        return {
            "success": True,
            "message": "Invitation declined successfully",
            "data": {
                "team_id": invitation.get("team_id"),
                "team_name": invitation.get("team_name"),
                "role": invitation.get("role")
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error declining invitation: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to decline invitation: {str(e)}")

# =====================================================
# DEBUG ENDPOINTS
# =====================================================

@router.get("/debug/user-info")
async def debug_user_info(current_user: dict = Depends(get_current_user)):
    """Debug endpoint to check JWT token parsing."""
    return {
        "success": True,
        "current_user": current_user,
        "user_id": current_user.get("user_id"),
        "email": current_user.get("email"),
        "all_keys": list(current_user.keys()) if current_user else []
    }

@router.get("/teams/invitations/{invitation_id}", response_model=Dict[str, Any])
async def get_team_invitation(
    invitation_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get team invitation details."""
    try:
        # Debug logging
        logger.info(f"Get invitation request - invitation_id: {invitation_id}")
        logger.info(f"Current user data: {current_user}")
        
        # Try multiple ways to get user_id for compatibility
        user_id = (
            current_user.get("user_id") or 
            current_user.get("id") or 
            current_user.get("sub") or 
            current_user.get("entity_id")
        )
        user_email = current_user.get("email")
        
        logger.info(f"Extracted user_id: {user_id}, email: {user_email}")
        
        if not user_id:
            logger.error(f"No user_id found in current_user: {current_user}")
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        # Get invitation
        logger.info(f"Looking for invitation with ID: {invitation_id}")
        invitation = mongodb_service.get_collection('team_invitations').find_one({
            "invitation_id": invitation_id
        })
        
        if not invitation:
            # Check if invitation exists but with different status
            all_invitations = list(mongodb_service.get_collection('team_invitations').find({
                "invitation_id": invitation_id
            }))
            logger.error(f"No invitation found. All invitations with this ID: {all_invitations}")
            return {
                "success": False,
                "message": "Invitation not found",
                "invitation_id": invitation_id
            }
        
        logger.info(f"Found invitation: {invitation}")
        
        # Get inviter's name if not present in invitation (for backward compatibility)
        invited_by_name = invitation.get("invited_by_name")
        if not invited_by_name and invitation.get("invited_by"):
            inviter = mongodb_service.get_collection('users').find_one({
                "user_id": invitation.get("invited_by")
            })
            invited_by_name = inviter.get("name") if inviter else "Unknown User"
        
        # Check if invitation is for this user (just log, don't block viewing)
        is_for_user = invitation.get("invited_email") == user_email
        if not is_for_user:
            logger.warning(f"Email mismatch: invitation for {invitation.get('invited_email')}, user email: {user_email}")
        
        # Check if invitation is expired
        is_expired = False
        if invitation.get("expires_at"):
            expires_at = invitation.get("expires_at")
            # Handle both timezone-aware and naive datetimes
            if hasattr(expires_at, 'tzinfo') and expires_at.tzinfo is not None:
                # Timezone-aware datetime
                is_expired = expires_at < datetime.now(timezone.utc)
            else:
                # Naive datetime, assume UTC
                is_expired = expires_at < datetime.now(timezone.utc).replace(tzinfo=None)
        
        # Get team info
        team_id = invitation.get("team_id")
        logger.info(f"Looking for team with ID: {team_id}")
        team = mongodb_service.get_collection('master_teams').find_one({
            "team_id": team_id
        })
        
        team_info = None
        if team:
            logger.info(f"Found team: {team.get('name', 'Unknown')}")
            team_info = {
                "team_id": team.get("team_id"),
                "name": team.get("name"),
                "description": team.get("description"),
                "member_count": len(team.get("members", [])),
                "created_at": team.get("created_at").isoformat() if team.get("created_at") else None
            }
        else:
            logger.warning(f"Team not found with ID: {team_id}")
        
        return {
            "success": True,
            "invitation": {
                "invitation_id": invitation.get("invitation_id"),
                "team_id": invitation.get("team_id"),
                "team_name": invitation.get("team_name"),
                "invited_email": invitation.get("invited_email"),
                "role": invitation.get("role"),
                "permissions": invitation.get("permissions", {}),
                "status": invitation.get("status"),
                "created_at": invitation.get("created_at").isoformat() if invitation.get("created_at") else None,
                "expires_at": invitation.get("expires_at").isoformat() if invitation.get("expires_at") else None,
                "invited_by": invitation.get("invited_by"),
                "invited_by_name": invited_by_name,
                "invited_by_email": invitation.get("invited_by_email")
            },
            "team_info": team_info,
            "is_expired": is_expired,
            "is_for_user": is_for_user,
            "can_accept": invitation.get("status") == "pending" and not is_expired and is_for_user
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting invitation: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get invitation: {str(e)}")

@router.get("/teams/invitations", response_model=Dict[str, Any])
async def get_user_invitations(
    current_user: dict = Depends(get_current_user),
    status: Optional[str] = Query(None, description="Filter by invitation status: pending, accepted, declined, expired"),
    limit: int = Query(50, description="Number of invitations to return")
):
    """Get all invitations for the current user."""
    try:
        user_id = (
            current_user.get("user_id") or 
            current_user.get("id") or 
            current_user.get("sub") or 
            current_user.get("entity_id")
        )
        user_email = current_user.get("email")
        
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        # Build query
        query = {"invited_email": user_email}
        if status:
            query["status"] = status
        
        # Get invitations
        invitations = list(mongodb_service.get_collection('team_invitations').find(query).sort("created_at", -1).limit(limit))
        
        # Process invitations
        processed_invitations = []
        for invitation in invitations:
            # Check if expired
            is_expired = False
            if invitation.get("expires_at"):
                expires_at = invitation.get("expires_at")
                # Handle both timezone-aware and naive datetimes
                if hasattr(expires_at, 'tzinfo') and expires_at.tzinfo is not None:
                    # Timezone-aware datetime
                    is_expired = expires_at < datetime.now(timezone.utc)
                else:
                    # Naive datetime, assume UTC
                    is_expired = expires_at < datetime.now(timezone.utc).replace(tzinfo=None)
            
            processed_invitations.append({
                "invitation_id": invitation.get("invitation_id"),
                "team_id": invitation.get("team_id"),
                "team_name": invitation.get("team_name"),
                "role": invitation.get("role"),
                "permissions": invitation.get("permissions", {}),
                "status": invitation.get("status"),
                "created_at": invitation.get("created_at").isoformat() if invitation.get("created_at") else None,
                "expires_at": invitation.get("expires_at").isoformat() if invitation.get("expires_at") else None,
                "invited_by": invitation.get("invited_by"),
                "invited_by_name": invitation.get("invited_by_name"),
                "is_expired": is_expired,
                "can_accept": invitation.get("status") == "pending" and not is_expired
            })
        
        return {
            "success": True,
            "invitations": processed_invitations,
            "total": len(processed_invitations),
            "filters": {
                "status": status,
                "limit": limit
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user invitations: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get invitations: {str(e)}")

@router.get("/debug/invitation/{invitation_id}")
async def debug_invitation(invitation_id: str):
    """Debug endpoint to check invitation data."""
    try:
        invitation = mongodb_service.get_collection('team_invitations').find_one({
            "invitation_id": invitation_id
        })
        
        if not invitation:
            return {
                "success": False,
                "message": "Invitation not found",
                "invitation_id": invitation_id
            }
        
        return {
            "success": True,
            "invitation": invitation,
            "status": invitation.get("status"),
            "expires_at": invitation.get("expires_at"),
            "invited_email": invitation.get("invited_email")
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@router.get("/teams/invitations/{invitation_id}/public")
async def get_team_invitation_public(invitation_id: str):
    """Get team invitation details without authentication (for public access)."""
    try:
        logger.info(f"Public invitation request - invitation_id: {invitation_id}")
        
        # Get invitation
        invitation = mongodb_service.get_collection('team_invitations').find_one({
            "invitation_id": invitation_id
        })
        
        if not invitation:
            return {
                "success": False,
                "message": "Invitation not found",
                "invitation_id": invitation_id
            }
        
        # Get inviter's name if not present in invitation (for backward compatibility)
        invited_by_name = invitation.get("invited_by_name")
        if not invited_by_name and invitation.get("invited_by"):
            inviter = mongodb_service.get_collection('users').find_one({
                "user_id": invitation.get("invited_by")
            })
            invited_by_name = inviter.get("name") if inviter else "Unknown User"
        
        # Get team info
        team = mongodb_service.get_collection('master_teams').find_one({
            "team_id": invitation.get("team_id")
        })
        
        team_info = None
        if team:
            team_info = {
                "team_id": team.get("team_id"),
                "name": team.get("name"),
                "description": team.get("description"),
                "member_count": len(team.get("members", []))
            }
        
        # Check if expired
        is_expired = False
        if invitation.get("expires_at"):
            expires_at = invitation.get("expires_at")
            # Handle both timezone-aware and naive datetimes
            if hasattr(expires_at, 'tzinfo') and expires_at.tzinfo is not None:
                # Timezone-aware datetime
                is_expired = expires_at < datetime.now(timezone.utc)
            else:
                # Naive datetime, assume UTC
                is_expired = expires_at < datetime.now(timezone.utc).replace(tzinfo=None)
        
        return {
            "success": True,
            "invitation": {
                "invitation_id": invitation.get("invitation_id"),
                "team_id": invitation.get("team_id"),
                "team_name": invitation.get("team_name"),
                "role": invitation.get("role"),
                "status": invitation.get("status"),
                "expires_at": invitation.get("expires_at").isoformat() if invitation.get("expires_at") else None,
                "is_expired": is_expired,
                "invited_by": invitation.get("invited_by"),
                "invited_by_name": invited_by_name,
                "invited_by_email": invitation.get("invited_by_email")
            },
            "team_info": team_info
        }
        
    except Exception as e:
        logger.error(f"Error in public invitation endpoint: {e}")
        return {
            "success": False,
            "error": str(e)
        }

# =====================================================
# TEAM PERFORMANCE & ANALYTICS APIs
# =====================================================

@router.get("/teams/{team_id}/performance/trends", response_model=Dict[str, Any])
async def get_team_performance_trends(
    team_id: str,
    time_range: str = Query("last_30_days", description="Time range: last_7_days, last_30_days, last_90_days"),
    current_user: dict = Depends(get_current_user)
):
    """Get team performance trends over time."""
    try:
        user_id = (
            current_user.get("user_id") or 
            current_user.get("id") or 
            current_user.get("sub") or 
            current_user.get("entity_id")
        )
        
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        # Get team info
        team = mongodb_service.get_collection('master_teams').find_one({"team_id": team_id})
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")
        
        # Calculate time range
        from datetime import datetime, timedelta
        now = datetime.now(timezone.utc)
        
        if time_range == "last_7_days":
            start_date = now - timedelta(days=7)
        elif time_range == "last_30_days":
            start_date = now - timedelta(days=30)
        elif time_range == "last_90_days":
            start_date = now - timedelta(days=90)
        else:
            start_date = now - timedelta(days=30)
        
        # Get performance data (mock data for now - replace with real calculations)
        team_performance = [
            {
                "team": team.get("name", "Unknown Team"),
                "performance": 85,
                "trend": "up",
                "period": time_range,
                "previous_period": 78,
                "change_percentage": 8.97
            }
        ]
        
        # Get metrics
        members = team.get("members", [])
        total_tasks = 150  # Mock data
        completed_tasks = 128  # Mock data
        completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        
        return {
            "success": True,
            "data": {
                "team_performance": team_performance,
                "time_range": time_range,
                "metrics": {
                    "total_tasks": total_tasks,
                    "completed_tasks": completed_tasks,
                    "completion_rate": round(completion_rate, 2),
                    "average_response_time": "2.5 hours"
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting team performance trends: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get performance trends: {str(e)}")

@router.get("/teams/{team_id}/performance/individual", response_model=Dict[str, Any])
async def get_individual_performance(
    team_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get individual performance metrics for team members."""
    try:
        user_id = (
            current_user.get("user_id") or 
            current_user.get("id") or 
            current_user.get("sub") or 
            current_user.get("entity_id")
        )
        
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        # Get team info
        team = mongodb_service.get_collection('master_teams').find_one({"team_id": team_id})
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")
        
        # Get team members
        members = team.get("members", [])
        
        # Get individual performance data (mock data for now)
        individual_performance = []
        total_performance = 0
        
        for member in members:
            # Mock performance calculation
            performance = 70 + (hash(member.get("user_id", "")) % 30)  # Random between 70-100
            
            individual_performance.append({
                "user_id": member.get("user_id"),
                "name": member.get("name", "Unknown User"),
                "email": member.get("email", ""),
                "performance": performance,
                "trend": "up" if performance > 80 else "down" if performance < 70 else "stable",
                "tasks": {
                    "total": 20 + (hash(member.get("user_id", "")) % 15),
                    "completed": int(20 + (hash(member.get("user_id", "")) % 15) * (performance / 100)),
                    "pending": int((20 + (hash(member.get("user_id", "")) % 15)) * (1 - performance / 100))
                },
                "last_activity": (datetime.now(timezone.utc) - timedelta(hours=hash(member.get("user_id", "")) % 48)).isoformat(),
                "role": member.get("role", "Member"),
                "avatar": f"https://ui-avatars.com/api/?name={member.get('name', 'U')}&background=random"
            })
            
            total_performance += performance
        
        # Calculate summary
        average_performance = total_performance / len(members) if members else 0
        top_performer = max(individual_performance, key=lambda x: x["performance"]) if individual_performance else None
        needs_improvement = len([m for m in individual_performance if m["performance"] < 70])
        
        return {
            "success": True,
            "data": {
                "individual_performance": individual_performance,
                "summary": {
                    "total_members": len(members),
                    "average_performance": round(average_performance, 1),
                    "top_performer": top_performer["name"] if top_performer else "N/A",
                    "needs_improvement": needs_improvement
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting individual performance: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get individual performance: {str(e)}")

@router.get("/teams/{team_id}/invitations/performance", response_model=Dict[str, Any])
async def get_invite_performance(
    team_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get formal invite performance metrics."""
    try:
        user_id = (
            current_user.get("user_id") or 
            current_user.get("id") or 
            current_user.get("sub") or 
            current_user.get("entity_id")
        )
        
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        # Get team info
        team = mongodb_service.get_collection('master_teams').find_one({"team_id": team_id})
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")
        
        # Get invitation data
        invitations = list(mongodb_service.get_collection('team_invitations').find({
            "team_id": team_id
        }))
        
        # Calculate invite stats
        total_invites = len(invitations)
        accepted_invites = len([inv for inv in invitations if inv.get("status") == "accepted"])
        pending_invites = len([inv for inv in invitations if inv.get("status") == "pending"])
        declined_invites = len([inv for inv in invitations if inv.get("status") == "declined"])
        
        acceptance_rate = (accepted_invites / total_invites * 100) if total_invites > 0 else 0
        
        # Get recent invitations
        recent_invitations = []
        for inv in invitations[-10:]:  # Last 10 invitations
            response_time = None
            if inv.get("accepted_at") and inv.get("created_at"):
                response_time = (inv["accepted_at"] - inv["created_at"]).total_seconds() / 3600  # hours
            
            recent_invitations.append({
                "invitation_id": inv.get("invitation_id"),
                "member_name": inv.get("invited_by_name", "Unknown"),
                "email": inv.get("invited_email"),
                "role": inv.get("role", "Member"),
                "status": inv.get("status", "pending").title(),
                "sent_date": inv.get("created_at").isoformat() if inv.get("created_at") else None,
                "response_date": inv.get("accepted_at").isoformat() if inv.get("accepted_at") else None,
                "response_time": f"{response_time:.1f} hours" if response_time else None,
                "invited_by": inv.get("invited_by_name", "Unknown")
            })
        
        return {
            "success": True,
            "data": {
                "invite_stats": {
                    "total_invites_sent": total_invites,
                    "accepted_invites": accepted_invites,
                    "pending_invites": pending_invites,
                    "declined_invites": declined_invites,
                    "acceptance_rate": round(acceptance_rate, 2),
                    "average_response_time": "1.2 days"  # Mock data
                },
                "recent_invitations": recent_invitations,
                "performance_metrics": {
                    "invite_success_rate": round(acceptance_rate, 2),
                    "avg_time_to_accept": "1.2 days",
                    "avg_time_to_decline": "3.5 days",
                    "most_common_role": "Member"
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting invite performance: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get invite performance: {str(e)}")

@router.get("/teams/{team_id}/performance/overview", response_model=Dict[str, Any])
async def get_team_performance_overview(
    team_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get comprehensive team performance overview."""
    try:
        user_id = (
            current_user.get("user_id") or 
            current_user.get("id") or 
            current_user.get("sub") or 
            current_user.get("entity_id")
        )
        
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        # Get team info
        team = mongodb_service.get_collection('master_teams').find_one({"team_id": team_id})
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")
        
        members = team.get("members", [])
        active_members = len([m for m in members if m.get("status") == "active"])
        
        # Calculate performance metrics
        total_tasks = 150  # Mock data
        completed_tasks = 128  # Mock data
        completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        
        # Performance breakdown
        excellent = len([m for m in members if hash(m.get("user_id", "")) % 100 > 90])
        good = len([m for m in members if 70 <= hash(m.get("user_id", "")) % 100 <= 90])
        average = len([m for m in members if 50 <= hash(m.get("user_id", "")) % 100 < 70])
        needs_improvement = len([m for m in members if hash(m.get("user_id", "")) % 100 < 50])
        
        return {
            "success": True,
            "data": {
                "team_overview": {
                    "team_name": team.get("name", "Unknown Team"),
                    "total_members": len(members),
                    "active_members": active_members,
                    "performance_score": round(completion_rate, 0),
                    "trend": "up",
                    "last_updated": datetime.now(timezone.utc).isoformat()
                },
                "key_metrics": {
                    "tasks_completed": completed_tasks,
                    "tasks_pending": total_tasks - completed_tasks,
                    "completion_rate": round(completion_rate, 2),
                    "average_response_time": "2.5 hours",
                    "team_engagement": 92
                },
                "performance_breakdown": {
                    "excellent": excellent,
                    "good": good,
                    "average": average,
                    "needs_improvement": needs_improvement
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting team performance overview: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get performance overview: {str(e)}")

@router.get("/teams/{team_id}/analytics/dashboard", response_model=Dict[str, Any])
async def get_team_analytics_dashboard(
    team_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get comprehensive team analytics dashboard data."""
    try:
        user_id = (
            current_user.get("user_id") or 
            current_user.get("id") or 
            current_user.get("sub") or 
            current_user.get("entity_id")
        )
        
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        # Get all teams for comparison
        all_teams = list(mongodb_service.get_collection('master_teams').find({}))
        
        # Calculate dashboard metrics
        total_teams = len(all_teams)
        total_members = sum(len(team.get("members", [])) for team in all_teams)
        active_members = sum(len([m for m in team.get("members", []) if m.get("status") == "active"]) for team in all_teams)
        
        # Mock performance trends
        weekly_trends = [
            {"week": "Week 1", "performance": 75},
            {"week": "Week 2", "performance": 78},
            {"week": "Week 3", "performance": 82},
            {"week": "Week 4", "performance": 85}
        ]
        
        monthly_trends = [
            {"month": "Oct 2023", "performance": 70},
            {"month": "Nov 2023", "performance": 75},
            {"month": "Dec 2023", "performance": 78},
            {"month": "Jan 2024", "performance": 85}
        ]
        
        # Team comparison data
        team_comparison = []
        for team in all_teams:
            members = team.get("members", [])
            performance = 70 + (hash(team.get("team_id", "")) % 30)  # Mock performance
            
            team_comparison.append({
                "team_id": team.get("team_id"),
                "team_name": team.get("name", "Unknown Team"),
                "performance": performance,
                "members_count": len(members),
                "trend": "up" if performance > 80 else "down" if performance < 70 else "stable"
            })
        
        return {
            "success": True,
            "data": {
                "dashboard_metrics": {
                    "total_teams": total_teams,
                    "total_members": total_members,
                    "active_members": active_members,
                    "average_performance": 78.5,
                    "this_month_growth": 12.5
                },
                "performance_trends": {
                    "weekly": weekly_trends,
                    "monthly": monthly_trends
                },
                "team_comparison": team_comparison
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting analytics dashboard: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get analytics dashboard: {str(e)}")

@router.get("/teams/{team_id}/reports/performance", response_model=Dict[str, Any])
async def get_performance_reports(
    team_id: str,
    format: str = Query("json", description="Report format: json, csv"),
    time_range: str = Query("last_30_days", description="Time range for report"),
    current_user: dict = Depends(get_current_user)
):
    """Get team performance reports."""
    try:
        user_id = (
            current_user.get("user_id") or 
            current_user.get("id") or 
            current_user.get("sub") or 
            current_user.get("entity_id")
        )
        
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        # Get team info
        team = mongodb_service.get_collection('master_teams').find_one({"team_id": team_id})
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")
        
        # Generate report data
        report_data = {
            "team_name": team.get("name", "Unknown Team"),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "time_range": time_range,
            "summary": {
                "total_members": len(team.get("members", [])),
                "performance_score": 85,
                "completion_rate": 78.5,
                "engagement_level": "High"
            },
            "detailed_metrics": {
                "tasks_completed": 128,
                "tasks_pending": 22,
                "average_response_time": "2.5 hours",
                "team_satisfaction": 4.2
            }
        }
        
        if format == "csv":
            # Convert to CSV format
            csv_data = f"Team Name,Generated At,Performance Score,Completion Rate\n"
            csv_data += f"{report_data['team_name']},{report_data['generated_at']},{report_data['summary']['performance_score']},{report_data['summary']['completion_rate']}\n"
            
            return {
                "success": True,
                "data": {
                    "format": "csv",
                    "content": csv_data,
                    "filename": f"team_performance_report_{team_id}_{datetime.now().strftime('%Y%m%d')}.csv"
                }
            }
        else:
            return {
                "success": True,
                "data": report_data
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating performance report: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")

@router.post("/teams/{team_id}/reports/generate", response_model=Dict[str, Any])
async def generate_performance_report(
    team_id: str,
    request: Dict[str, Any] = Body(...),
    current_user: dict = Depends(get_current_user)
):
    """Generate a custom performance report."""
    try:
        user_id = (
            current_user.get("user_id") or 
            current_user.get("id") or 
            current_user.get("sub") or 
            current_user.get("entity_id")
        )
        
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        # Get team info
        team = mongodb_service.get_collection('master_teams').find_one({"team_id": team_id})
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")
        
        # Generate custom report based on request parameters
        report_id = f"report_{team_id}_{int(datetime.now().timestamp())}"
        
        # Store report generation request
        report_data = {
            "report_id": report_id,
            "team_id": team_id,
            "generated_by": user_id,
            "parameters": request,
            "status": "generating",
            "created_at": datetime.now(timezone.utc),
            "estimated_completion": (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
        }
        
        # Store in database (you might want to create a reports collection)
        # mongodb_service.get_collection('performance_reports').insert_one(report_data)
        
        return {
            "success": True,
            "message": "Report generation started",
            "data": {
                "report_id": report_id,
                "status": "generating",
                "estimated_completion": report_data["estimated_completion"]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating custom report: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate custom report: {str(e)}")

@router.get("/teams/{team_id}/members/{member_id}/activity", response_model=Dict[str, Any])
async def get_member_activity(
    team_id: str,
    member_id: str,
    days: int = Query(30, description="Number of days to look back"),
    current_user: dict = Depends(get_current_user)
):
    """Get individual member activity details."""
    try:
        user_id = (
            current_user.get("user_id") or 
            current_user.get("id") or 
            current_user.get("sub") or 
            current_user.get("entity_id")
        )
        
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        # Get team info
        team = mongodb_service.get_collection('master_teams').find_one({"team_id": team_id})
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")
        
        # Check if member exists in team
        member = next((m for m in team.get("members", []) if m.get("user_id") == member_id), None)
        if not member:
            raise HTTPException(status_code=404, detail="Member not found in team")
        
        # Generate mock activity data
        activities = []
        for i in range(days):
            activity_date = datetime.now(timezone.utc) - timedelta(days=i)
            activities.append({
                "date": activity_date.isoformat(),
                "tasks_completed": hash(f"{member_id}{i}") % 5,
                "hours_active": 2 + (hash(f"{member_id}{i}") % 6),
                "meetings_attended": hash(f"{member_id}{i}") % 3,
                "messages_sent": 5 + (hash(f"{member_id}{i}") % 15)
            })
        
        # Calculate summary
        total_tasks = sum(a["tasks_completed"] for a in activities)
        total_hours = sum(a["hours_active"] for a in activities)
        total_meetings = sum(a["meetings_attended"] for a in activities)
        total_messages = sum(a["messages_sent"] for a in activities)
        
        return {
            "success": True,
            "data": {
                "member": {
                    "user_id": member_id,
                    "name": member.get("name", "Unknown User"),
                    "email": member.get("email", ""),
                    "role": member.get("role", "Member")
                },
                "activity_summary": {
                    "period_days": days,
                    "total_tasks_completed": total_tasks,
                    "total_hours_active": total_hours,
                    "total_meetings_attended": total_meetings,
                    "total_messages_sent": total_messages,
                    "average_daily_tasks": round(total_tasks / days, 1),
                    "average_daily_hours": round(total_hours / days, 1)
                },
                "daily_activities": activities
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting member activity: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get member activity: {str(e)}")

@router.get("/teams/{team_id}/members/activity/summary", response_model=Dict[str, Any])
async def get_team_activity_summary(
    team_id: str,
    days: int = Query(7, description="Number of days to look back"),
    current_user: dict = Depends(get_current_user)
):
    """Get team-wide activity summary."""
    try:
        user_id = (
            current_user.get("user_id") or 
            current_user.get("id") or 
            current_user.get("sub") or 
            current_user.get("entity_id")
        )
        
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        # Get team info
        team = mongodb_service.get_collection('master_teams').find_one({"team_id": team_id})
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")
        
        members = team.get("members", [])
        
        # Generate team activity summary
        team_activity = {
            "team_name": team.get("name", "Unknown Team"),
            "period_days": days,
            "total_members": len(members),
            "active_members": len([m for m in members if m.get("status") == "active"]),
            "total_tasks_completed": 0,
            "total_hours_logged": 0,
            "total_meetings": 0,
            "total_messages": 0,
            "most_active_member": None,
            "least_active_member": None
        }
        
        member_activities = []
        for member in members:
            member_tasks = sum(hash(f"{member.get('user_id', '')}{i}") % 5 for i in range(days))
            member_hours = sum(2 + (hash(f"{member.get('user_id', '')}{i}") % 6) for i in range(days))
            
            member_activities.append({
                "user_id": member.get("user_id"),
                "name": member.get("name", "Unknown User"),
                "tasks_completed": member_tasks,
                "hours_active": member_hours,
                "activity_score": member_tasks + member_hours
            })
            
            team_activity["total_tasks_completed"] += member_tasks
            team_activity["total_hours_logged"] += member_hours
        
        # Find most and least active members
        if member_activities:
            most_active = max(member_activities, key=lambda x: x["activity_score"])
            least_active = min(member_activities, key=lambda x: x["activity_score"])
            
            team_activity["most_active_member"] = most_active["name"]
            team_activity["least_active_member"] = least_active["name"]
        
        return {
            "success": True,
            "data": {
                "team_activity": team_activity,
                "member_activities": member_activities
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting team activity summary: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get team activity summary: {str(e)}")

# =====================================================
# BRAND ASSIGNMENT MANAGEMENT
# =====================================================

@router.post("/teams/{team_id}/assign-brand", response_model=Dict[str, Any])
async def assign_team_to_brand(
    team_id: str,
    request: BrandAssignmentRequest,
    current_user: dict = Depends(get_current_user)
):
    """Assign team members to a brand with specific roles."""
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        # Check if user has permission to assign brands
        team = mongodb_service.get_collection('master_teams').find_one({
            "team_id": team_id,
            "$or": [
                {"owner_id": user_id},
                {"members": {"$elemMatch": {"user_id": user_id, "role": "admin"}}}
            ]
        })
        
        if not team:
            raise HTTPException(status_code=404, detail="Team not found or insufficient permissions")
        
        # Check if brand exists and user has access
        brand = mongodb_service.get_collection('brands').find_one({
            "brand_id": request.brand_id,
            "$or": [
                {"owner_id": user_id},
                {"team_members.user_id": user_id}
            ]
        })
        
        if not brand:
            raise HTTPException(status_code=404, detail="Brand not found or access denied")
        
        # Assign each team member to the brand
        assigned_members = []
        for member in team.get("members", []):
            if member.get("status") == "active":
                # Add to brand team members
                brand_member = {
                    "user_id": member.get("user_id"),
                    "role": request.role,
                    "permissions": request.permissions or member.get("permissions", {}),
                    "assigned_by": user_id,
                    "assigned_at": datetime.now(timezone.utc),
                    "status": "active"
                }
                
                # Update or insert brand member
                mongodb_service.get_collection('brands').update_one(
                    {
                        "brand_id": request.brand_id,
                        "team_members.user_id": {"$ne": member.get("user_id")}
                    },
                    {"$push": {"team_members": brand_member}}
                )
                
                # Update existing member if exists
                mongodb_service.get_collection('brands').update_one(
                    {
                        "brand_id": request.brand_id,
                        "team_members.user_id": member.get("user_id")
                    },
                    {
                        "$set": {
                            "team_members.$.role": request.role,
                            "team_members.$.permissions": request.permissions or member.get("permissions", {}),
                            "team_members.$.assigned_by": user_id,
                            "team_members.$.assigned_at": datetime.now(timezone.utc),
                            "team_members.$.status": "active"
                        }
                    }
                )
                
                assigned_members.append({
                    "user_id": member.get("user_id"),
                    "role": request.role
                })
        
        # Update team's brand assignments
        assignment = {
            "brand_id": request.brand_id,
            "brand_name": brand.get("name"),
            "role": request.role,
            "assigned_by": user_id,
            "assigned_at": datetime.now(timezone.utc),
            "status": "active"
        }
        
        mongodb_service.get_collection('master_teams').update_one(
            {"team_id": team_id},
            {
                "$push": {"brand_assignments": assignment},
                "$set": {"updated_at": datetime.now(timezone.utc)}
            }
        )
        
        logger.info(f"Assigned team {team_id} to brand {request.brand_id} with {len(assigned_members)} members")
        
        return {
            "success": True,
            "message": "Team successfully assigned to brand",
            "data": {
                "team_id": team_id,
                "brand_id": request.brand_id,
                "brand_name": brand.get("name"),
                "assigned_members": assigned_members,
                "total_assigned": len(assigned_members)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error assigning team to brand: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to assign team: {str(e)}")

@router.get("/teams/{team_id}/brands", response_model=Dict[str, Any])
async def get_team_brand_assignments(
    team_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get all brand assignments for a team."""
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        # Check if user has access to team
        team = mongodb_service.get_collection('master_teams').find_one({
            "team_id": team_id,
            "$or": [
                {"owner_id": user_id},
                {"members.user_id": user_id}
            ]
        })
        
        if not team:
            raise HTTPException(status_code=404, detail="Team not found or access denied")
        
        # Get brand details for assignments
        brand_assignments = []
        for assignment in team.get("brand_assignments", []):
            brand = mongodb_service.get_collection('brands').find_one({
                "brand_id": assignment.get("brand_id")
            })
            
            if brand:
                brand_assignments.append({
                    "brand_id": assignment.get("brand_id"),
                    "brand_name": brand.get("name"),
                    "brand_description": brand.get("description"),
                    "role": assignment.get("role"),
                    "assigned_at": assignment.get("assigned_at").isoformat() if assignment.get("assigned_at") else None,
                    "status": assignment.get("status")
                })
        
        return {
            "success": True,
            "message": "Brand assignments retrieved successfully",
            "data": {
                "team_id": team_id,
                "team_name": team.get("name"),
                "brand_assignments": brand_assignments,
                "total_assignments": len(brand_assignments)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting team brand assignments: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get brand assignments: {str(e)}")

# =====================================================
# TEAM MANAGEMENT UTILITIES
# =====================================================

@router.get("/teams/{team_id}/permissions", response_model=Dict[str, Any])
async def get_team_permissions(
    team_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get available permissions for team management."""
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        # Check if user has access to team
        team = mongodb_service.get_collection('master_teams').find_one({
            "team_id": team_id,
            "$or": [
                {"owner_id": user_id},
                {"members.user_id": user_id}
            ]
        })
        
        if not team:
            raise HTTPException(status_code=404, detail="Team not found or access denied")
        
        # Get user's role and permissions
        user_role = "owner" if team.get("owner_id") == user_id else "member"
        user_permissions = {}
        
        if user_role == "member":
            for member in team.get("members", []):
                if member.get("user_id") == user_id:
                    user_role = member.get("role", "member")
                    user_permissions = member.get("permissions", {})
                    break
        
        return {
            "success": True,
            "message": "Permissions retrieved successfully",
            "data": {
                "team_id": team_id,
                "user_role": user_role,
                "user_permissions": user_permissions,
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
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting team permissions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get permissions: {str(e)}")

@router.get("/teams/{team_id}/capabilities", response_model=Dict[str, Any])
async def get_user_capabilities(
    team_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get user's capabilities in this team (what they can and cannot do)."""
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        # Check if user has access to team
        team = mongodb_service.get_collection('master_teams').find_one({
            "team_id": team_id,
            "$or": [
                {"owner_id": user_id},
                {"members.user_id": user_id}
            ]
        })
        
        if not team:
            raise HTTPException(status_code=404, detail="Team not found or access denied")
        
        # Get user's role
        is_owner = team.get("owner_id") == user_id
        user_role = "owner" if is_owner else "member"
        member_permissions = {}
        
        if not is_owner:
            for member in team.get("members", []):
                if member.get("user_id") == user_id:
                    user_role = member.get("role", "member")
                    member_permissions = member.get("permissions", {})
                    break
        
        # Define capabilities based on role
        is_admin = user_role == "admin"
        is_regular_member = user_role == "member" or user_role == "viewer"
        
        # Calculate capabilities
        capabilities = {
            # Team management
            "can_invite_members": is_owner or is_admin or member_permissions.get("can_invite", False),
            "can_remove_members": is_owner or is_admin or member_permissions.get("can_manage_members", False),
            "can_update_member_roles": is_owner or is_admin or member_permissions.get("can_manage_members", False),
            "can_delete_team": is_owner,
            "can_edit_team_details": is_owner or is_admin,
            
            # Brand management
            "can_assign_brands": is_owner or is_admin or member_permissions.get("can_assign_brands", False),
            "can_view_brand_assignments": True,  # All members can view
            
            # Analytics & Viewing
            "can_view_team_analytics": is_owner or is_admin or member_permissions.get("can_view_analytics", True),
            "can_view_team_details": True,  # All members can view
            "can_view_members_list": True,  # All members can view
            "can_view_performance_reports": is_owner or is_admin,
            
            # Projects
            "can_create_projects": is_owner or is_admin or member_permissions.get("can_create_projects", False),
            
            # Settings
            "can_manage_team_settings": is_owner or is_admin,
            
            # Invitations
            "can_view_pending_invitations": is_owner or is_admin,
            "can_cancel_invitations": is_owner or is_admin
        }
        
        # UI display hints
        ui_hints = {
            "show_invite_button": capabilities["can_invite_members"],
            "show_remove_member_button": capabilities["can_remove_members"],
            "show_edit_role_button": capabilities["can_update_member_roles"],
            "show_delete_team_button": capabilities["can_delete_team"],
            "show_team_settings": capabilities["can_manage_team_settings"],
            "show_assign_brand_button": capabilities["can_assign_brands"],
            "show_analytics_tab": capabilities["can_view_team_analytics"],
            "show_performance_reports": capabilities["can_view_performance_reports"],
            "show_invite_management": capabilities["can_view_pending_invitations"]
        }
        
        return {
            "success": True,
            "message": "User capabilities retrieved successfully",
            "data": {
                "team_id": team_id,
                "user_id": user_id,
                "user_role": user_role,
                "is_owner": is_owner,
                "is_admin": is_admin,
                "capabilities": capabilities,
                "ui_hints": ui_hints,
                "custom_permissions": member_permissions
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user capabilities: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get capabilities: {str(e)}")

@router.post("/teams/{team_id}/cleanup-all-pending", response_model=Dict[str, Any])
async def cleanup_all_pending_invitations(
    team_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Clean up all pending invitations for the team."""
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        # Get team
        team = mongodb_service.get_collection('master_teams').find_one({
            "team_id": team_id,
            "members": {"$elemMatch": {"user_id": user_id, "role": {"$in": ["admin", "owner"]}}}
        })
        
        if not team:
            raise HTTPException(status_code=404, detail="Team not found or insufficient permissions")
        
        # Delete all pending invitations for this team
        result = mongodb_service.get_collection('team_invitations').delete_many({
            "team_id": team_id,
            "status": "pending"
        })
        
        return {
            "success": True,
            "message": f"Cleaned up {result.deleted_count} pending invitations",
            "data": {
                "deleted_count": result.deleted_count,
                "team_id": team_id,
                "team_name": team.get("name")
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cleaning up pending invitations: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clean up invitations: {str(e)}")

@router.post("/teams/{team_id}/cleanup-duplicates", response_model=Dict[str, Any])
async def cleanup_duplicate_invitations(
    team_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Clean up duplicate invitations for the team."""
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        # Get team
        team = mongodb_service.get_collection('master_teams').find_one({
            "team_id": team_id,
            "members": {"$elemMatch": {"user_id": user_id, "role": {"$in": ["admin", "owner"]}}}
        })
        
        if not team:
            raise HTTPException(status_code=404, detail="Team not found or insufficient permissions")
        
        # Get all pending invitations for this team
        invitations = list(mongodb_service.get_collection('team_invitations').find({
            "team_id": team_id,
            "status": "pending"
        }))
        
        # Group by email and keep only the latest one
        email_groups = {}
        for invitation in invitations:
            email = invitation.get("invited_email")
            if email not in email_groups:
                email_groups[email] = []
            email_groups[email].append(invitation)
        
        deleted_count = 0
        for email, email_invitations in email_groups.items():
            if len(email_invitations) > 1:
                # Sort by created_at and keep the latest
                email_invitations.sort(key=lambda x: x.get("created_at", datetime.min), reverse=True)
                latest = email_invitations[0]
                
                # Delete the rest
                for invitation in email_invitations[1:]:
                    mongodb_service.get_collection('team_invitations').delete_one({
                        "invitation_id": invitation["invitation_id"]
                    })
                    deleted_count += 1
        
        return {
            "success": True,
            "message": f"Cleaned up {deleted_count} duplicate invitations",
            "data": {
                "deleted_count": deleted_count,
                "remaining_invitations": len(invitations) - deleted_count
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cleaning up duplicates: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clean up duplicates: {str(e)}")

@router.get("/teams/invitations/pending", response_model=Dict[str, Any])
async def get_pending_invitations(
    current_user: dict = Depends(get_current_user)
):
    """Get pending invitations for the current user with detailed information."""
    try:
        user_email = current_user.get("email")
        if not user_email:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        # Get pending invitations
        invitations = list(mongodb_service.get_collection('team_invitations').find({
            "invited_email": user_email,
            "status": "pending",
            "expires_at": {"$gt": datetime.now(timezone.utc)}
        }))
        
        # Format response with detailed information
        formatted_invitations = []
        for invitation in invitations:
            team = mongodb_service.get_collection('master_teams').find_one({
                "team_id": invitation.get("team_id")
            })
            
            if team:
                # Get invited by user details
                invited_by_user = mongodb_service.get_collection('users').find_one({
                    "user_id": invitation.get("invited_by")
                })
                
                formatted_invitations.append({
                    "invitation_id": invitation.get("invitation_id"),
                    "team_id": invitation.get("team_id"),
                    "team_name": invitation.get("team_name"),
                    "team_description": team.get("description"),
                    "email": invitation.get("invited_email"),
                    "role": invitation.get("role"),
                    "permissions": invitation.get("permissions", {}),
                    "message": invitation.get("message"),
                    "invited_by": invitation.get("invited_by"),
                    "invited_by_name": invited_by_user.get("name") if invited_by_user else "Unknown User",
                    "invited_by_email": invited_by_user.get("email") if invited_by_user else "Unknown Email",
                    "expires_at": invitation.get("expires_at").isoformat() if invitation.get("expires_at") else None,
                    "created_at": invitation.get("created_at").isoformat() if invitation.get("created_at") else None,
                    "status": invitation.get("status"),
                    "team_type": team.get("team_type"),
                    "team_status": team.get("status")
                })
        
        return {
            "success": True,
            "message": "Pending invitations retrieved successfully",
            "data": {
                "invitations": formatted_invitations,
                "total": len(formatted_invitations),
                "summary": {
                    "total_pending": len(formatted_invitations),
                    "expires_soon": len([inv for inv in formatted_invitations 
                                       if invitation.get("expires_at") and 
                                       datetime.fromisoformat(inv["expires_at"].replace('Z', '+00:00')) < 
                                       datetime.now(timezone.utc) + timedelta(days=1)])
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting pending invitations: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get invitations: {str(e)}")

@router.get("/teams/{team_id}/all-members", response_model=Dict[str, Any])
async def get_all_team_members_status(
    team_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get all team members with their status - active, pending, invited, etc."""
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        # Check if user has access to team
        team = mongodb_service.get_collection('master_teams').find_one({
            "team_id": team_id,
            "$or": [
                {"owner_id": user_id},
                {"members.user_id": user_id}
            ]
        })
        
        if not team:
            raise HTTPException(status_code=404, detail="Team not found or access denied")
        
        # Get all active members
        active_members = []
        for member in team.get("members", []):
            user_info = mongodb_service.get_collection('users').find_one({
                "user_id": member.get("user_id")
            })
            
            member_details = {
                "user_id": member.get("user_id"),
                "name": user_info.get("name") if user_info else "Unknown User",
                "email": user_info.get("email") if user_info else "Unknown Email",
                "role": member.get("role"),
                "permissions": member.get("permissions", {}),
                "joined_at": member.get("joined_at").isoformat() if member.get("joined_at") else None,
                "status": "active",
                "member_type": "active",
                "profile_picture": user_info.get("profile_picture") if user_info else None
            }
            active_members.append(member_details)
        
        # Get all invitations for this team
        invitations = list(mongodb_service.get_collection('team_invitations').find({
            "team_id": team_id
        }))
        
        # Process invitations
        pending_invitations = []
        expired_invitations = []
        accepted_invitations = []
        
        for invitation in invitations:
            invitation_data = {
                "invitation_id": invitation.get("invitation_id"),
                "email": invitation.get("invited_email"),
                "role": invitation.get("role"),
                "permissions": invitation.get("permissions", {}),
                "message": invitation.get("message"),
                "invited_by": invitation.get("invited_by"),
                "created_at": invitation.get("created_at").isoformat() if invitation.get("created_at") else None,
                "expires_at": invitation.get("expires_at").isoformat() if invitation.get("expires_at") else None,
                "status": invitation.get("status")
            }
            
            if invitation.get("status") == "accepted":
                accepted_invitations.append(invitation_data)
            elif invitation.get("status") == "pending":
                # Fix datetime comparison issue
                expires_at = invitation.get("expires_at")
                if expires_at:
                    # Ensure both datetimes are timezone-aware
                    if expires_at.tzinfo is None:
                        expires_at = expires_at.replace(tzinfo=timezone.utc)
                    current_time = datetime.now(timezone.utc)
                    if expires_at > current_time:
                        pending_invitations.append(invitation_data)
                    else:
                        expired_invitations.append(invitation_data)
                else:
                    expired_invitations.append(invitation_data)
            else:
                expired_invitations.append(invitation_data)
        
        return {
            "success": True,
            "message": "All team members status retrieved successfully",
            "data": {
                "team_id": team_id,
                "team_name": team.get("name"),
                "active_members": active_members,
                "pending_invitations": pending_invitations,
                "expired_invitations": expired_invitations,
                "accepted_invitations": accepted_invitations,
                "summary": {
                    "total_active": len(active_members),
                    "total_pending": len(pending_invitations),
                    "total_expired": len(expired_invitations),
                    "total_accepted": len(accepted_invitations),
                    "total_invitations": len(invitations)
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting all team members status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get team members status: {str(e)}")

@router.get("/teams/{team_id}/test", response_model=Dict[str, Any])
async def test_team_endpoint(
    team_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Test endpoint to check if routes are working."""
    return {
        "success": True,
        "message": "Test endpoint working",
        "data": {
            "team_id": team_id,
            "user_id": current_user.get("user_id")
        }
    }

@router.get("/teams/{team_id}/members", response_model=Dict[str, Any])
async def get_team_members(
    team_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get all members of a specific team."""
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        # Check if user has access to team
        team = mongodb_service.get_collection('master_teams').find_one({
            "team_id": team_id,
            "$or": [
                {"owner_id": user_id},
                {"members.user_id": user_id}
            ]
        })
        
        if not team:
            raise HTTPException(status_code=404, detail="Team not found or access denied")
        
        # Get member details with names
        members_with_details = []
        for member in team.get("members", []):
            try:
                user_info = mongodb_service.get_collection('users').find_one({
                    "user_id": member.get("user_id")
                })
                
                member_details = {
                    "user_id": member.get("user_id"),
                    "name": user_info.get("name") if user_info else "Unknown User",
                    "email": user_info.get("email") if user_info else "Unknown Email",
                    "role": member.get("role"),
                    "permissions": member.get("permissions", {}),
                    "joined_at": member.get("joined_at").isoformat() if member.get("joined_at") else None,
                    "status": member.get("status"),
                    "profile_picture": user_info.get("profile_picture") if user_info else None
                }
                members_with_details.append(member_details)
            except Exception as e:
                logger.error(f"Error getting user info for member {member.get('user_id')}: {e}")
                # Add member with minimal info if user lookup fails
                member_details = {
                    "user_id": member.get("user_id"),
                    "name": "Unknown User",
                    "email": "Unknown Email",
                    "role": member.get("role"),
                    "permissions": member.get("permissions", {}),
                    "joined_at": member.get("joined_at").isoformat() if member.get("joined_at") else None,
                    "status": member.get("status"),
                    "profile_picture": None
                }
                members_with_details.append(member_details)
        
        return {
            "success": True,
            "message": "Team members retrieved successfully",
            "data": {
                "team_id": team_id,
                "team_name": team.get("name"),
                "members": members_with_details,
                "total_members": len(members_with_details),
                "active_members": len([m for m in members_with_details if m.get("status") == "active"])
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting team members: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get team members: {str(e)}")

@router.put("/teams/{team_id}/members/{user_id}", response_model=Dict[str, Any])
async def update_team_member(
    team_id: str,
    user_id: str,
    request: TeamMemberUpdateRequest,
    current_user: dict = Depends(get_current_user)
):
    """Update a team member's role and permissions."""
    try:
        current_user_id = current_user.get("user_id")
        if not current_user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        # Check if current user has permission to manage members
        team = mongodb_service.get_collection('master_teams').find_one({
            "team_id": team_id,
            "$or": [
                {"owner_id": current_user_id},
                {"members": {"$elemMatch": {"user_id": current_user_id, "role": "admin"}}}
            ]
        })
        
        if not team:
            raise HTTPException(status_code=404, detail="Team not found or insufficient permissions")
        
        # Check if target user is a member
        member_exists = any(
            member.get("user_id") == user_id 
            for member in team.get("members", [])
        )
        
        if not member_exists:
            raise HTTPException(status_code=404, detail="User is not a member of this team")
        
        # Update member
        update_data = {}
        if request.role:
            update_data["members.$.role"] = request.role
        if request.permissions:
            update_data["members.$.permissions"] = request.permissions
        if request.status:
            update_data["members.$.status"] = request.status
        
        if update_data:
            update_data["updated_at"] = datetime.now(timezone.utc)
            
            mongodb_service.get_collection('master_teams').update_one(
                {
                    "team_id": team_id,
                    "members.user_id": user_id
                },
                {"$set": update_data}
            )
        
        logger.info(f"Updated team member {user_id} in team {team_id} by user {current_user_id}")
        
        return {
            "success": True,
            "message": "Team member updated successfully",
            "data": {
                "team_id": team_id,
                "user_id": user_id,
                "updated_fields": list(update_data.keys())
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating team member: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update team member: {str(e)}")

@router.delete("/teams/{team_id}/members/{user_id}", response_model=Dict[str, Any])
async def remove_team_member(
    team_id: str,
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Remove a member from the team."""
    try:
        current_user_id = current_user.get("user_id")
        if not current_user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        # Check if current user has permission to manage members
        team = mongodb_service.get_collection('master_teams').find_one({
            "team_id": team_id,
            "$or": [
                {"owner_id": current_user_id},
                {"members": {"$elemMatch": {"user_id": current_user_id, "role": "admin"}}}
            ]
        })
        
        if not team:
            raise HTTPException(status_code=404, detail="Team not found or insufficient permissions")
        
        # Check if target user is a member
        member_exists = any(
            member.get("user_id") == user_id 
            for member in team.get("members", [])
        )
        
        if not member_exists:
            raise HTTPException(status_code=404, detail="User is not a member of this team")
        
        # Don't allow owner to remove themselves
        if team.get("owner_id") == user_id:
            raise HTTPException(status_code=400, detail="Team owner cannot be removed")
        
        # Remove member
        mongodb_service.get_collection('master_teams').update_one(
            {"team_id": team_id},
            {
                "$pull": {"members": {"user_id": user_id}},
                "$set": {"updated_at": datetime.now(timezone.utc)}
            }
        )
        
        logger.info(f"Removed team member {user_id} from team {team_id} by user {current_user_id}")
        
        return {
            "success": True,
            "message": "Team member removed successfully",
            "data": {
                "team_id": team_id,
                "user_id": user_id
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing team member: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to remove team member: {str(e)}")
