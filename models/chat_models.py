#!/usr/bin/env python3
"""
Chat Models for Content Crew Prodigal
WhatsApp-like chat system for brand teams
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class MessageType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    FILE = "file"
    SYSTEM = "system"

class MessageStatus(str, Enum):
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"

class ChatMessageRequest(BaseModel):
    """Request model for sending a chat message."""
    content: str = Field(..., description="Message content")
    message_type: MessageType = Field(default=MessageType.TEXT, description="Type of message")
    reply_to: Optional[str] = Field(None, description="ID of message being replied to")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional message metadata")

class ChatMessageResponse(BaseModel):
    """Response model for chat messages."""
    message_id: str
    conversation_id: str
    brand_id: str
    sender_id: str
    sender_name: str
    content: str
    message_type: MessageType
    status: MessageStatus
    reply_to: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

class ConversationResponse(BaseModel):
    """Response model for conversations."""
    conversation_id: str
    brand_id: str
    brand_name: str
    participants: List[Dict[str, Any]]
    last_message: Optional[ChatMessageResponse] = None
    unread_count: int = 0
    created_at: datetime
    updated_at: datetime

class CreateConversationRequest(BaseModel):
    """Request model for creating a conversation."""
    participant_ids: List[str] = Field(..., description="List of user IDs to include in conversation")
    name: Optional[str] = Field(None, description="Optional conversation name")

class ConversationListResponse(BaseModel):
    """Response model for listing conversations."""
    success: bool
    conversations: List[ConversationResponse]
    total: int

class MessageListResponse(BaseModel):
    """Response model for listing messages in a conversation."""
    success: bool
    messages: List[ChatMessageResponse]
    total: int
    has_more: bool

class SendMessageResponse(BaseModel):
    """Response model for sending a message."""
    success: bool
    message: ChatMessageResponse
    message_id: str

class MarkReadRequest(BaseModel):
    """Request model for marking messages as read."""
    message_ids: List[str] = Field(..., description="List of message IDs to mark as read")

class TypingStatusRequest(BaseModel):
    """Request model for typing status."""
    is_typing: bool = Field(..., description="Whether user is currently typing")

class TypingStatusResponse(BaseModel):
    """Response model for typing status."""
    success: bool
    user_id: str
    user_name: str
    is_typing: bool
    conversation_id: str
