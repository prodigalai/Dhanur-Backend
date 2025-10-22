#!/usr/bin/env python3
"""
Chat Routes for Content Crew Prodigal
WhatsApp-like chat system for brand teams
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query, File, UploadFile
from typing import Optional, List
from middleware.auth import get_current_user
from services.chat_service import chat_service
from models.chat_models import (
    ChatMessageRequest, ChatMessageResponse, ConversationResponse,
    CreateConversationRequest, ConversationListResponse, MessageListResponse,
    SendMessageResponse, MarkReadRequest, TypingStatusRequest, TypingStatusResponse
)

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/conversation", response_model=ConversationResponse)
async def create_conversation(
    request: CreateConversationRequest,
    brand_id: str = Query(..., description="Brand ID for the conversation"),
    current_user: dict = Depends(get_current_user)
):
    """Create a new conversation for a brand team.
    
    Note: Team chat conversations are automatically created when:
    - A brand is created (for the owner)
    - A team member accepts an invitation (for all team members)
    
    This endpoint allows creating additional custom conversations.
    """
    try:
        logger.info(f"Creating conversation - brand_id: {brand_id}, request: {request}, user: {current_user}")
        
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        result = await chat_service.create_conversation(
            brand_id=brand_id,
            creator_id=user_id,
            participant_ids=request.participant_ids,
            name=request.name
        )
        
        logger.info(f"Chat service result: {result}")
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        # Get the created conversation
        conversations_result = await chat_service.get_conversations(user_id, brand_id)
        if conversations_result["success"]:
            for conv in conversations_result["conversations"]:
                if conv["conversation_id"] == result["conversation_id"]:
                    return conv
        
        raise HTTPException(status_code=500, detail="Failed to retrieve created conversation")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating conversation: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create conversation: {str(e)}")

@router.get("/conversations", response_model=ConversationListResponse)
async def get_conversations(
    brand_id: Optional[str] = Query(None, description="Filter by brand ID"),
    current_user: dict = Depends(get_current_user)
):
    """Get conversations for the current user."""
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        result = await chat_service.get_conversations(user_id, brand_id)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return ConversationListResponse(
            success=True,
            conversations=result["conversations"],
            total=result["total"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversations: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get conversations: {str(e)}")

@router.get("/conversation/{conversation_id}/messages", response_model=MessageListResponse)
async def get_messages(
    conversation_id: str,
    limit: int = Query(50, description="Number of messages to return"),
    skip: int = Query(0, description="Number of messages to skip"),
    current_user: dict = Depends(get_current_user)
):
    """Get messages from a conversation."""
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        result = await chat_service.get_messages(conversation_id, user_id, limit, skip)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return MessageListResponse(
            success=True,
            messages=result["messages"],
            total=result["total"],
            has_more=result["has_more"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting messages: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get messages: {str(e)}")

@router.post("/conversation/{conversation_id}/send", response_model=SendMessageResponse)
async def send_message(
    conversation_id: str,
    request: ChatMessageRequest,
    current_user: dict = Depends(get_current_user)
):
    """Send a message to a conversation."""
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        result = await chat_service.send_message(conversation_id, user_id, request)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        # Get the sent message
        messages_result = await chat_service.get_messages(conversation_id, user_id, 1, 0)
        if messages_result["success"] and messages_result["messages"]:
            message = messages_result["messages"][0]
            return SendMessageResponse(
                success=True,
                message=message,
                message_id=message["message_id"]
            )
        
        raise HTTPException(status_code=500, detail="Failed to retrieve sent message")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send message: {str(e)}")

@router.post("/conversation/send-to-user", response_model=SendMessageResponse)
async def send_message_to_user(
    request: ChatMessageRequest,
    target_user_id: str = Query(..., description="Target user ID to send message to"),
    brand_id: str = Query(..., description="Brand ID for the conversation"),
    current_user: dict = Depends(get_current_user)
):
    """Send a message to a specific user. Creates conversation automatically if it doesn't exist."""
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        # Check if both users are team members of the brand
        from services.mongodb_service import mongodb_service
        
        brand = mongodb_service.get_collection("brands").find_one({"brand_id": brand_id})
        if not brand:
            raise HTTPException(status_code=404, detail="Brand not found")
        
        team_members = [member["user_id"] for member in brand.get("team_members", [])]
        
        if user_id not in team_members:
            raise HTTPException(status_code=403, detail="You are not a member of this brand")
        
        if target_user_id not in team_members:
            raise HTTPException(status_code=403, detail="Target user is not a member of this brand")
        
        # Create or find conversation between these two users
        participants = sorted([user_id, target_user_id])
        
        # Check if conversation already exists
        existing_conversation = mongodb_service.get_collection("conversations").find_one({
            "brand_id": brand_id,
            "participants": {"$all": participants, "$size": len(participants)},
            "is_active": True
        })
        
        if existing_conversation:
            conversation_id = existing_conversation["conversation_id"]
        else:
            # Create new conversation
            create_result = await chat_service.create_conversation(
                brand_id=brand_id,
                creator_id=user_id,
                participant_ids=[target_user_id],
                name=f"Chat with {target_user_id}"
            )
            
            if not create_result["success"]:
                raise HTTPException(status_code=500, detail=f"Failed to create conversation: {create_result.get('error')}")
            
            conversation_id = create_result["conversation_id"]
        
        # Send message to the conversation
        result = await chat_service.send_message(conversation_id, user_id, request)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        # Get the sent message
        messages_result = await chat_service.get_messages(conversation_id, user_id, 1, 0)
        if messages_result["success"] and messages_result["messages"]:
            message = messages_result["messages"][0]
            return SendMessageResponse(
                success=True,
                message=message,
                message_id=message["message_id"]
            )
        
        raise HTTPException(status_code=500, detail="Failed to retrieve sent message")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending message to user: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send message: {str(e)}")

@router.post("/conversation/{conversation_id}/read")
async def mark_messages_read(
    conversation_id: str,
    request: MarkReadRequest,
    current_user: dict = Depends(get_current_user)
):
    """Mark messages as read."""
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        result = await chat_service.mark_messages_read(conversation_id, user_id, request.message_ids)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return {
            "success": True,
            "message": f"Marked {result['updated_count']} messages as read",
            "updated_count": result["updated_count"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking messages as read: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to mark messages as read: {str(e)}")

@router.get("/conversation/{conversation_id}/info")
async def get_conversation_info(
    conversation_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get conversation information."""
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        # Get conversation details
        from services.mongodb_service import mongodb_service
        conversation = mongodb_service.get_collection("conversations").find_one({
            "conversation_id": conversation_id,
            "participants": user_id,
            "is_active": True
        })
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Get participant details
        participants = []
        for participant_id in conversation["participants"]:
            user = mongodb_service.get_collection("users").find_one({"user_id": participant_id})
            if user:
                participants.append({
                    "user_id": participant_id,
                    "name": user.get("name", "Unknown User"),
                    "email": user.get("email", ""),
                    "profile_picture": user.get("profile_picture"),
                    "is_online": False  # TODO: Implement online status
                })
        
        return {
            "success": True,
            "conversation_id": conversation_id,
            "brand_id": conversation["brand_id"],
            "brand_name": conversation["brand_name"],
            "name": conversation["name"],
            "participants": participants,
            "created_at": conversation["created_at"],
            "updated_at": conversation["updated_at"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation info: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get conversation info: {str(e)}")

@router.post("/conversation/{conversation_id}/typing")
async def update_typing_status(
    conversation_id: str,
    request: TypingStatusRequest,
    current_user: dict = Depends(get_current_user)
):
    """Update typing status in a conversation."""
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        # Get user info
        from services.mongodb_service import mongodb_service
        user = mongodb_service.get_collection("users").find_one({"user_id": user_id})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # TODO: Implement real-time typing status broadcasting
        # For now, just return success
        
        return TypingStatusResponse(
            success=True,
            user_id=user_id,
            user_name=user.get("name", "Unknown User"),
            is_typing=request.is_typing,
            conversation_id=conversation_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating typing status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update typing status: {str(e)}")

@router.delete("/conversation/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a conversation (soft delete)."""
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        # Verify user is participant
        from services.mongodb_service import mongodb_service
        conversation = mongodb_service.get_collection("conversations").find_one({
            "conversation_id": conversation_id,
            "participants": user_id,
            "is_active": True
        })
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Soft delete conversation
        from datetime import datetime, timezone
        mongodb_service.get_collection("conversations").update_one(
            {"conversation_id": conversation_id},
            {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc)}}
        )
        
        logger.info(f"Conversation {conversation_id} deleted by user {user_id}")
        
        return {
            "success": True,
            "message": "Conversation deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting conversation: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete conversation: {str(e)}")

@router.put("/message/{message_id}/edit")
async def edit_message(
    message_id: str,
    request: ChatMessageRequest,
    current_user: dict = Depends(get_current_user)
):
    """Edit a message (only by sender within time limit)."""
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        from services.mongodb_service import mongodb_service
        from datetime import datetime, timezone, timedelta
        
        # Get the message
        message = mongodb_service.get_collection("messages").find_one({"message_id": message_id})
        if not message:
            raise HTTPException(status_code=404, detail="Message not found")
        
        # Check if user is the sender
        if message.get("sender_id") != user_id:
            raise HTTPException(status_code=403, detail="You can only edit your own messages")
        
        # Check if message is within edit time limit (15 minutes)
        message_time = message.get("created_at")
        if isinstance(message_time, str):
            message_time = datetime.fromisoformat(message_time.replace('Z', '+00:00'))
        
        time_limit = datetime.now(timezone.utc) - timedelta(minutes=15)
        if message_time < time_limit:
            raise HTTPException(status_code=400, detail="Message can only be edited within 15 minutes")
        
        # Update the message
        update_data = {
            "content": request.content,
            "message_type": request.message_type.value,
            "updated_at": datetime.now(timezone.utc),
            "is_edited": True,
            "edited_at": datetime.now(timezone.utc)
        }
        
        if request.reply_to:
            update_data["reply_to"] = request.reply_to
        if request.metadata:
            update_data["metadata"] = request.metadata
        
        result = mongodb_service.get_collection("messages").update_one(
            {"message_id": message_id},
            {"$set": update_data}
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=400, detail="Failed to edit message")
        
        # Get updated message
        updated_message = mongodb_service.get_collection("messages").find_one({"message_id": message_id})
        
        logger.info(f"Message {message_id} edited by user {user_id}")
        
        return {
            "success": True,
            "message": "Message edited successfully",
            "data": {
                "message_id": message_id,
                "content": updated_message["content"],
                "is_edited": updated_message.get("is_edited", False),
                "edited_at": updated_message.get("edited_at")
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error editing message: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to edit message: {str(e)}")

@router.delete("/message/{message_id}")
async def delete_message(
    message_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a message (soft delete for everyone, hard delete for sender)."""
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        from services.mongodb_service import mongodb_service
        from datetime import datetime, timezone
        
        # Get the message
        message = mongodb_service.get_collection("messages").find_one({"message_id": message_id})
        if not message:
            raise HTTPException(status_code=404, detail="Message not found")
        
        # Check if user is the sender
        is_sender = message.get("sender_id") == user_id
        
        if is_sender:
            # Hard delete for sender (remove from database)
            result = mongodb_service.get_collection("messages").delete_one({"message_id": message_id})
            if result.deleted_count == 0:
                raise HTTPException(status_code=400, detail="Failed to delete message")
            
            logger.info(f"Message {message_id} hard deleted by sender {user_id}")
            
            return {
                "success": True,
                "message": "Message deleted successfully",
                "deleted_for": "everyone"
            }
        else:
            # Soft delete for others (mark as deleted for this user)
            result = mongodb_service.get_collection("messages").update_one(
                {"message_id": message_id},
                {
                    "$addToSet": {"deleted_for": user_id},
                    "$set": {"updated_at": datetime.now(timezone.utc)}
                }
            )
            
            if result.modified_count == 0:
                raise HTTPException(status_code=400, detail="Failed to delete message")
            
            logger.info(f"Message {message_id} soft deleted for user {user_id}")
            
            return {
                "success": True,
                "message": "Message deleted for you",
                "deleted_for": "you"
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting message: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete message: {str(e)}")

@router.post("/message/{message_id}/react")
async def react_to_message(
    message_id: str,
    reaction: str = Query(..., description="Reaction emoji (e.g., 👍, ❤️, 😂)"),
    current_user: dict = Depends(get_current_user)
):
    """Add or remove reaction to a message."""
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        from services.mongodb_service import mongodb_service
        from datetime import datetime, timezone
        
        # Get the message
        message = mongodb_service.get_collection("messages").find_one({"message_id": message_id})
        if not message:
            raise HTTPException(status_code=404, detail="Message not found")
        
        # Check if user already reacted with this emoji
        existing_reactions = message.get("reactions", {})
        user_reactions = existing_reactions.get(user_id, [])
        
        if reaction in user_reactions:
            # Remove reaction
            user_reactions.remove(reaction)
            if not user_reactions:
                # Remove user from reactions if no reactions left
                del existing_reactions[user_id]
            else:
                existing_reactions[user_id] = user_reactions
        else:
            # Add reaction
            if user_id not in existing_reactions:
                existing_reactions[user_id] = []
            existing_reactions[user_id].append(reaction)
        
        # Update message with reactions
        result = mongodb_service.get_collection("messages").update_one(
            {"message_id": message_id},
            {
                "$set": {
                    "reactions": existing_reactions,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=400, detail="Failed to update reaction")
        
        logger.info(f"User {user_id} reacted '{reaction}' to message {message_id}")
        
        return {
            "success": True,
            "message": "Reaction updated successfully",
            "reactions": existing_reactions,
            "user_reactions": existing_reactions.get(user_id, [])
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reacting to message: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to react to message: {str(e)}")

@router.get("/message/{message_id}/reactions")
async def get_message_reactions(
    message_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get all reactions for a message."""
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        from services.mongodb_service import mongodb_service
        
        # Get the message
        message = mongodb_service.get_collection("messages").find_one({"message_id": message_id})
        if not message:
            raise HTTPException(status_code=404, detail="Message not found")
        
        reactions = message.get("reactions", {})
        
        # Get user details for reactions
        reaction_details = []
        for user_id_react, emojis in reactions.items():
            user = mongodb_service.get_collection("users").find_one({"user_id": user_id_react})
            if user:
                reaction_details.append({
                    "user_id": user_id_react,
                    "user_name": user.get("name", "Unknown User"),
                    "reactions": emojis
                })
        
        return {
            "success": True,
            "message_id": message_id,
            "reactions": reaction_details,
            "total_reactions": sum(len(emojis) for emojis in reactions.values())
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting message reactions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get message reactions: {str(e)}")

@router.post("/message/{message_id}/forward")
async def forward_message(
    message_id: str,
    target_conversation_id: str = Query(..., description="Target conversation ID to forward to"),
    current_user: dict = Depends(get_current_user)
):
    """Forward a message to another conversation."""
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        from services.mongodb_service import mongodb_service
        from datetime import datetime, timezone
        import secrets
        
        # Get the original message
        original_message = mongodb_service.get_collection("messages").find_one({"message_id": message_id})
        if not original_message:
            raise HTTPException(status_code=404, detail="Original message not found")
        
        # Check if user has access to target conversation
        target_conversation = mongodb_service.get_collection("conversations").find_one({
            "conversation_id": target_conversation_id,
            "participants": user_id,
            "is_active": True
        })
        if not target_conversation:
            raise HTTPException(status_code=404, detail="Target conversation not found or access denied")
        
        # Create forwarded message
        forwarded_message = {
            "message_id": secrets.token_hex(12),
            "conversation_id": target_conversation_id,
            "brand_id": target_conversation["brand_id"],
            "sender_id": user_id,
            "sender_name": original_message.get("sender_name", "Unknown User"),
            "content": f"Forwarded: {original_message['content']}",
            "message_type": original_message.get("message_type", "text"),
            "status": "sent",
            "is_forwarded": True,
            "forwarded_from": message_id,
            "original_sender": original_message.get("sender_id"),
            "original_sender_name": original_message.get("sender_name"),
            "metadata": {
                "forwarded_at": datetime.now(timezone.utc).isoformat(),
                "original_message_id": message_id,
                "original_conversation_id": original_message.get("conversation_id")
            },
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        
        # Insert forwarded message
        mongodb_service.get_collection("messages").insert_one(forwarded_message)
        
        # Update conversation last message
        mongodb_service.get_collection("conversations").update_one(
            {"conversation_id": target_conversation_id},
            {
                "$set": {
                    "last_message": forwarded_message,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        
        logger.info(f"Message {message_id} forwarded to conversation {target_conversation_id} by user {user_id}")
        
        return {
            "success": True,
            "message": "Message forwarded successfully",
            "data": {
                "forwarded_message_id": forwarded_message["message_id"],
                "target_conversation_id": target_conversation_id
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error forwarding message: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to forward message: {str(e)}")

@router.post("/cleanup-duplicates")
async def cleanup_duplicate_conversations(
    brand_id: str = Query(..., description="Brand ID to clean up duplicates for"),
    current_user: dict = Depends(get_current_user)
):
    """Clean up duplicate conversations for a brand (admin only)."""
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        # Check if user is admin/owner of the brand
        from services.mongodb_service import mongodb_service
        from datetime import datetime, timezone
        
        brand = mongodb_service.get_collection("brands").find_one({"brand_id": brand_id})
        if not brand:
            raise HTTPException(status_code=404, detail="Brand not found")
        
        # Check if user is owner or admin
        is_owner = brand.get("owner_id") == user_id
        is_admin = any(member.get("user_id") == user_id and member.get("role") in ["admin", "owner"] 
                      for member in brand.get("team_members", []))
        
        if not (is_owner or is_admin):
            raise HTTPException(status_code=403, detail="Only brand owners and admins can clean up duplicates")
        
        # Get all conversations for this brand
        conversations = list(mongodb_service.get_collection("conversations").find({
            "brand_id": brand_id,
            "is_active": True
        }))
        
        # Group conversations by participants
        participant_groups = {}
        for conv in conversations:
            participants_key = tuple(sorted(conv.get("participants", [])))
            if participants_key not in participant_groups:
                participant_groups[participants_key] = []
            participant_groups[participants_key].append(conv)
        
        # Keep only the oldest conversation in each group, delete others
        deleted_count = 0
        for participants, convs in participant_groups.items():
            if len(convs) > 1:
                # Sort by created_at, keep the oldest
                convs.sort(key=lambda x: x.get("created_at", datetime.min))
                to_delete = convs[1:]  # All except the first (oldest)
                
                for conv in to_delete:
                    mongodb_service.get_collection("conversations").update_one(
                        {"conversation_id": conv["conversation_id"]},
                        {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc)}}
                    )
                    deleted_count += 1
                    logger.info(f"Soft deleted duplicate conversation {conv['conversation_id']}")
        
        return {
            "success": True,
            "message": f"Cleaned up {deleted_count} duplicate conversations",
            "deleted_count": deleted_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cleaning up duplicate conversations: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clean up duplicates: {str(e)}")

# File upload endpoint temporarily disabled due to python-multipart dependency
# @router.post("/upload/file")
# async def upload_file(...):
#     """Upload a file to a conversation."""
#     pass

@router.get("/search")
async def search_messages(
    query: str = Query(..., description="Search query"),
    brand_id: str = Query(..., description="Brand ID to search in"),
    conversation_id: Optional[str] = Query(None, description="Specific conversation to search in"),
    limit: int = Query(20, description="Number of results to return"),
    skip: int = Query(0, description="Number of results to skip"),
    current_user: dict = Depends(get_current_user)
):
    """Search messages in conversations."""
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        from services.mongodb_service import mongodb_service
        
        # Build search query
        search_query = {
            "brand_id": brand_id,
            "content": {"$regex": query, "$options": "i"},  # Case-insensitive search
            "deleted_for": {"$ne": user_id}  # Exclude messages deleted for this user
        }
        
        if conversation_id:
            search_query["conversation_id"] = conversation_id
        else:
            # Only search in conversations user is part of
            user_conversations = mongodb_service.get_collection("conversations").find({
                "brand_id": brand_id,
                "participants": user_id,
                "is_active": True
            })
            conversation_ids = [conv["conversation_id"] for conv in user_conversations]
            search_query["conversation_id"] = {"$in": conversation_ids}
        
        # Search messages
        messages = list(mongodb_service.get_collection("messages").find(search_query)
            .sort("created_at", -1)
            .skip(skip)
            .limit(limit))
        
        # Get conversation details for each message
        results = []
        for message in messages:
            conv = mongodb_service.get_collection("conversations").find_one({
                "conversation_id": message["conversation_id"]
            })
            
            results.append({
                "message_id": message["message_id"],
                "conversation_id": message["conversation_id"],
                "conversation_name": conv.get("name", "Chat") if conv else "Unknown",
                "sender_id": message["sender_id"],
                "sender_name": message["sender_name"],
                "content": message["content"],
                "message_type": message["message_type"],
                "created_at": message["created_at"],
                "highlight": query  # For frontend highlighting
            })
        
        total = mongodb_service.get_collection("messages").count_documents(search_query)
        
        logger.info(f"Search query '{query}' returned {len(results)} results for user {user_id}")
        
        return {
            "success": True,
            "query": query,
            "results": results,
            "total": total,
            "returned": len(results),
            "has_more": (skip + len(results)) < total
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching messages: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to search messages: {str(e)}")

@router.post("/message/{message_id}/pin")
async def pin_message(
    message_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Pin a message in a conversation."""
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        from services.mongodb_service import mongodb_service
        from datetime import datetime, timezone
        
        # Get the message
        message = mongodb_service.get_collection("messages").find_one({"message_id": message_id})
        if not message:
            raise HTTPException(status_code=404, detail="Message not found")
        
        # Check if user has access to conversation
        conversation = mongodb_service.get_collection("conversations").find_one({
            "conversation_id": message["conversation_id"],
            "participants": user_id,
            "is_active": True
        })
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found or access denied")
        
        # Check if message is already pinned
        pinned_messages = conversation.get("pinned_messages", [])
        if message_id in pinned_messages:
            # Unpin the message
            pinned_messages.remove(message_id)
            action = "unpinned"
        else:
            # Pin the message
            pinned_messages.append(message_id)
            action = "pinned"
        
        # Update conversation
        mongodb_service.get_collection("conversations").update_one(
            {"conversation_id": message["conversation_id"]},
            {
                "$set": {
                    "pinned_messages": pinned_messages,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        
        logger.info(f"Message {message_id} {action} by user {user_id}")
        
        return {
            "success": True,
            "message": f"Message {action} successfully",
            "action": action,
            "pinned_messages": pinned_messages
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error pinning message: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to pin message: {str(e)}")

@router.get("/conversation/{conversation_id}/pinned")
async def get_pinned_messages(
    conversation_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get pinned messages for a conversation."""
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        from services.mongodb_service import mongodb_service
        
        # Check if user has access to conversation
        conversation = mongodb_service.get_collection("conversations").find_one({
            "conversation_id": conversation_id,
            "participants": user_id,
            "is_active": True
        })
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found or access denied")
        
        # Get pinned message IDs
        pinned_message_ids = conversation.get("pinned_messages", [])
        
        # Get pinned messages
        pinned_messages = list(mongodb_service.get_collection("messages").find({
            "message_id": {"$in": pinned_message_ids},
            "deleted_for": {"$ne": user_id}  # Exclude messages deleted for this user
        }).sort("created_at", -1))
        
        logger.info(f"Retrieved {len(pinned_messages)} pinned messages for conversation {conversation_id}")
        
        return {
            "success": True,
            "conversation_id": conversation_id,
            "pinned_messages": pinned_messages,
            "total": len(pinned_messages)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting pinned messages: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get pinned messages: {str(e)}")

@router.post("/message/{message_id}/star")
async def star_message(
    message_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Star/unstar a message."""
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        from services.mongodb_service import mongodb_service
        from datetime import datetime, timezone
        
        # Get the message
        message = mongodb_service.get_collection("messages").find_one({"message_id": message_id})
        if not message:
            raise HTTPException(status_code=404, detail="Message not found")
        
        # Check if user has access to conversation
        conversation = mongodb_service.get_collection("conversations").find_one({
            "conversation_id": message["conversation_id"],
            "participants": user_id,
            "is_active": True
        })
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found or access denied")
        
        # Check if message is already starred by user
        starred_by = message.get("starred_by", [])
        
        if user_id in starred_by:
            # Unstar the message
            starred_by.remove(user_id)
            action = "unstarred"
        else:
            # Star the message
            starred_by.append(user_id)
            action = "starred"
        
        # Update message
        mongodb_service.get_collection("messages").update_one(
            {"message_id": message_id},
            {
                "$set": {
                    "starred_by": starred_by,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        
        logger.info(f"Message {message_id} {action} by user {user_id}")
        
        return {
            "success": True,
            "message": f"Message {action} successfully",
            "action": action,
            "starred_by": starred_by
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starring message: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to star message: {str(e)}")

@router.get("/starred-messages")
async def get_starred_messages(
    brand_id: str = Query(..., description="Brand ID to get starred messages from"),
    limit: int = Query(20, description="Number of results to return"),
    skip: int = Query(0, description="Number of results to skip"),
    current_user: dict = Depends(get_current_user)
):
    """Get starred messages for a user."""
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        from services.mongodb_service import mongodb_service
        
        # Get starred messages
        starred_messages = list(mongodb_service.get_collection("messages").find({
            "brand_id": brand_id,
            "starred_by": user_id,
            "deleted_for": {"$ne": user_id}  # Exclude messages deleted for this user
        }).sort("created_at", -1).skip(skip).limit(limit))
        
        # Get conversation details for each message
        results = []
        for message in starred_messages:
            conv = mongodb_service.get_collection("conversations").find_one({
                "conversation_id": message["conversation_id"]
            })
            
            results.append({
                "message_id": message["message_id"],
                "conversation_id": message["conversation_id"],
                "conversation_name": conv.get("name", "Chat") if conv else "Unknown",
                "sender_id": message["sender_id"],
                "sender_name": message["sender_name"],
                "content": message["content"],
                "message_type": message["message_type"],
                "created_at": message["created_at"],
                "starred_at": message.get("updated_at")
            })
        
        total = mongodb_service.get_collection("messages").count_documents({
            "brand_id": brand_id,
            "starred_by": user_id,
            "deleted_for": {"$ne": user_id}
        })
        
        logger.info(f"Retrieved {len(results)} starred messages for user {user_id}")
        
        return {
            "success": True,
            "starred_messages": results,
            "total": total,
            "returned": len(results),
            "has_more": (skip + len(results)) < total
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting starred messages: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get starred messages: {str(e)}")

@router.put("/user/status")
async def update_user_status(
    status: str = Query(..., description="User status (online, offline, away, busy)"),
    current_user: dict = Depends(get_current_user)
):
    """Update user online status."""
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        from services.mongodb_service import mongodb_service
        from datetime import datetime, timezone
        
        # Update user status
        mongodb_service.get_collection("users").update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "status": status,
                    "last_seen": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        
        logger.info(f"User {user_id} status updated to {status}")
        
        return {
            "success": True,
            "message": "Status updated successfully",
            "status": status,
            "last_seen": datetime.now(timezone.utc).isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update status: {str(e)}")

@router.get("/user/{user_id}/status")
async def get_user_status(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get user online status and last seen."""
    try:
        current_user_id = current_user.get("user_id")
        if not current_user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        from services.mongodb_service import mongodb_service
        
        # Get user status
        user = mongodb_service.get_collection("users").find_one({"user_id": user_id})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "success": True,
            "user_id": user_id,
            "name": user.get("name", "Unknown User"),
            "status": user.get("status", "offline"),
            "last_seen": user.get("last_seen"),
            "is_online": user.get("status") == "online"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get user status: {str(e)}")
