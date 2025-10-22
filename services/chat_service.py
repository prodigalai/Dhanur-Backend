#!/usr/bin/env python3
"""
Chat Service for Content Crew Prodigal
WhatsApp-like chat system for brand teams
"""

import os
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from bson import ObjectId
from services.mongodb_service import mongodb_service
from models.chat_models import (
    ChatMessageRequest, ChatMessageResponse, ConversationResponse,
    MessageType, MessageStatus
)

logger = logging.getLogger(__name__)

class ChatService:
    """Service for managing chat conversations and messages."""
    
    def __init__(self):
        self.conversations_collection = "conversations"
        self.messages_collection = "chat_messages"
        self.users_collection = "users"
        self.brands_collection = "brands"
    
    async def create_conversation(self, brand_id: str, creator_id: str, participant_ids: List[str], name: Optional[str] = None) -> Dict[str, Any]:
        """Create a new conversation for a brand team."""
        try:
            if not mongodb_service.is_connected():
                return {"success": False, "error": "Database not available"}
            
            # Verify brand exists and user has access
            brand = mongodb_service.get_collection(self.brands_collection).find_one({"brand_id": brand_id})
            if not brand:
                return {"success": False, "error": "Brand not found"}
            
            # Add creator to participants if not already included
            all_participants = list(set([creator_id] + participant_ids))
            all_participants.sort()  # Sort for consistent comparison
            
            # Verify all participants are team members of the brand
            # Team members are stored as an array within the brand document
            team_members = brand.get("team_members", [])
            valid_participants = [member["user_id"] for member in team_members if member.get("user_id") in all_participants]
            
            if len(valid_participants) != len(all_participants):
                missing_participants = set(all_participants) - set(valid_participants)
                return {"success": False, "error": f"Some participants are not team members: {list(missing_participants)}"}
            
            # Check if conversation already exists with same participants
            existing_conversation = mongodb_service.get_collection(self.conversations_collection).find_one({
                "brand_id": brand_id,
                "participants": {"$all": all_participants, "$size": len(all_participants)},
                "is_active": True
            })
            
            if existing_conversation:
                logger.info(f"Conversation already exists for participants: {all_participants}")
                return {
                    "success": True, 
                    "conversation_id": existing_conversation["conversation_id"],
                    "message": "Conversation already exists"
                }
            
            # Create conversation
            conversation_id = str(ObjectId())
            conversation_data = {
                "conversation_id": conversation_id,
                "brand_id": brand_id,
                "brand_name": brand.get("name", "Unknown Brand"),
                "participants": all_participants,
                "name": name or f"Team Chat - {brand.get('name', 'Unknown Brand')}",
                "created_by": creator_id,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "is_active": True
            }
            
            mongodb_service.get_collection(self.conversations_collection).insert_one(conversation_data)
            
            logger.info(f"Created conversation {conversation_id} for brand {brand_id}")
            return {"success": True, "conversation_id": conversation_id}
            
        except Exception as e:
            logger.error(f"Error creating conversation: {e}")
            return {"success": False, "error": str(e)}
    
    async def send_message(self, conversation_id: str, sender_id: str, message_request: ChatMessageRequest) -> Dict[str, Any]:
        """Send a message to a conversation."""
        try:
            if not mongodb_service.is_connected():
                return {"success": False, "error": "Database not available"}
            
            # Verify conversation exists and sender is participant
            conversation = mongodb_service.get_collection(self.conversations_collection).find_one({
                "conversation_id": conversation_id,
                "participants": sender_id,
                "is_active": True
            })
            
            if not conversation:
                return {"success": False, "error": "Conversation not found or access denied"}
            
            # Get sender info
            sender = mongodb_service.get_collection(self.users_collection).find_one({"user_id": sender_id})
            if not sender:
                return {"success": False, "error": "Sender not found"}
            
            # Create message
            message_id = str(ObjectId())
            message_data = {
                "message_id": message_id,
                "conversation_id": conversation_id,
                "brand_id": conversation["brand_id"],
                "sender_id": sender_id,
                "sender_name": sender.get("name", "Unknown User"),
                "content": message_request.content,
                "message_type": message_request.message_type.value,
                "status": MessageStatus.SENT.value,
                "reply_to": message_request.reply_to,
                "metadata": message_request.metadata or {},
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "is_deleted": False
            }
            
            mongodb_service.get_collection(self.messages_collection).insert_one(message_data)
            
            # Update conversation last activity
            mongodb_service.get_collection(self.conversations_collection).update_one(
                {"conversation_id": conversation_id},
                {"$set": {"updated_at": datetime.now(timezone.utc)}}
            )
            
            logger.info(f"Message {message_id} sent to conversation {conversation_id}")
            return {"success": True, "message_id": message_id}
            
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_conversations(self, user_id: str, brand_id: Optional[str] = None) -> Dict[str, Any]:
        """Get conversations for a user, optionally filtered by brand."""
        try:
            if not mongodb_service.is_connected():
                return {"success": False, "error": "Database not available"}
            
            # Build query
            query = {
                "participants": user_id,
                "is_active": True
            }
            if brand_id:
                query["brand_id"] = brand_id
            
            # Get conversations
            conversations_cursor = mongodb_service.get_collection(self.conversations_collection).find(query).sort("updated_at", -1)
            conversations = []
            
            for conv in conversations_cursor:
                # Get last message
                last_message = mongodb_service.get_collection(self.messages_collection).find_one(
                    {"conversation_id": conv["conversation_id"], "is_deleted": False},
                    sort=[("created_at", -1)]
                )
                
                # Get participant details
                participants = []
                for participant_id in conv["participants"]:
                    user = mongodb_service.get_collection(self.users_collection).find_one({"user_id": participant_id})
                    if user:
                        participants.append({
                            "user_id": participant_id,
                            "name": user.get("name", "Unknown User"),
                            "email": user.get("email", ""),
                            "profile_picture": user.get("profile_picture")
                        })
                
                # Count unread messages
                unread_count = mongodb_service.get_collection(self.messages_collection).count_documents({
                    "conversation_id": conv["conversation_id"],
                    "sender_id": {"$ne": user_id},
                    "status": {"$in": [MessageStatus.SENT.value, MessageStatus.DELIVERED.value]},
                    "is_deleted": False
                })
                
                conversation_response = {
                    "conversation_id": conv["conversation_id"],
                    "brand_id": conv["brand_id"],
                    "brand_name": conv["brand_name"],
                    "participants": participants,
                    "last_message": self._format_message(last_message) if last_message else None,
                    "unread_count": unread_count,
                    "created_at": conv["created_at"],
                    "updated_at": conv["updated_at"]
                }
                
                conversations.append(conversation_response)
            
            return {"success": True, "conversations": conversations, "total": len(conversations)}
            
        except Exception as e:
            logger.error(f"Error getting conversations: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_messages(self, conversation_id: str, user_id: str, limit: int = 50, skip: int = 0) -> Dict[str, Any]:
        """Get messages from a conversation."""
        try:
            if not mongodb_service.is_connected():
                return {"success": False, "error": "Database not available"}
            
            # Verify user has access to conversation
            conversation = mongodb_service.get_collection(self.conversations_collection).find_one({
                "conversation_id": conversation_id,
                "participants": user_id,
                "is_active": True
            })
            
            if not conversation:
                return {"success": False, "error": "Conversation not found or access denied"}
            
            # Get messages
            messages_cursor = mongodb_service.get_collection(self.messages_collection).find(
                {"conversation_id": conversation_id, "is_deleted": False}
            ).sort("created_at", -1).skip(skip).limit(limit)
            
            messages = []
            for msg in messages_cursor:
                messages.append(self._format_message(msg))
            
            # Check if there are more messages
            total_messages = mongodb_service.get_collection(self.messages_collection).count_documents({
                "conversation_id": conversation_id,
                "is_deleted": False
            })
            
            has_more = (skip + len(messages)) < total_messages
            
            return {
                "success": True,
                "messages": messages,
                "total": total_messages,
                "has_more": has_more
            }
            
        except Exception as e:
            logger.error(f"Error getting messages: {e}")
            return {"success": False, "error": str(e)}
    
    async def mark_messages_read(self, conversation_id: str, user_id: str, message_ids: List[str]) -> Dict[str, Any]:
        """Mark messages as read."""
        try:
            if not mongodb_service.is_connected():
                return {"success": False, "error": "Database not available"}
            
            # Verify user has access to conversation
            conversation = mongodb_service.get_collection(self.conversations_collection).find_one({
                "conversation_id": conversation_id,
                "participants": user_id,
                "is_active": True
            })
            
            if not conversation:
                return {"success": False, "error": "Conversation not found or access denied"}
            
            # Mark messages as read
            result = mongodb_service.get_collection(self.messages_collection).update_many(
                {
                    "message_id": {"$in": message_ids},
                    "conversation_id": conversation_id,
                    "sender_id": {"$ne": user_id}  # Don't mark own messages as read
                },
                {
                    "$set": {
                        "status": MessageStatus.READ.value,
                        "updated_at": datetime.now(timezone.utc)
                    }
                }
            )
            
            logger.info(f"Marked {result.modified_count} messages as read in conversation {conversation_id}")
            return {"success": True, "updated_count": result.modified_count}
            
        except Exception as e:
            logger.error(f"Error marking messages as read: {e}")
            return {"success": False, "error": str(e)}
    
    def _format_message(self, msg: Dict[str, Any]) -> Dict[str, Any]:
        """Format message for response."""
        if not msg:
            return None
            
        return {
            "message_id": msg["message_id"],
            "conversation_id": msg["conversation_id"],
            "brand_id": msg["brand_id"],
            "sender_id": msg["sender_id"],
            "sender_name": msg["sender_name"],
            "content": msg["content"],
            "message_type": msg["message_type"],
            "status": msg["status"],
            "reply_to": msg.get("reply_to"),
            "metadata": msg.get("metadata", {}),
            "created_at": msg["created_at"],
            "updated_at": msg["updated_at"]
        }

# Global instance
chat_service = ChatService()
