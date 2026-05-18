"""Pydantic schemas for conversations."""

from datetime import datetime
from pydantic import BaseModel, Field
from typing import List, Optional


class MessageCreate(BaseModel):
    """Schema for creating a message."""

    sender: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., min_length=1, max_length=10000)


class MessageResponse(BaseModel):
    """Schema for message response."""

    id: int
    sender: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationCreate(BaseModel):
    """Schema for creating a conversation."""

    title: Optional[str] = None


class ConversationResponse(BaseModel):
    """Schema for conversation response."""

    id: int
    title: str
    created_at: datetime
    updated_at: datetime
    messages: List[MessageResponse] = []

    class Config:
        from_attributes = True


class ConversationSummaryResponse(BaseModel):
    """Schema for conversation summary (list view)."""

    id: int
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int


class ChatMessageRequest(BaseModel):
    """Request schema for sending a chat message."""

    user_message: str = Field(..., min_length=1, max_length=10000)


class ChatMessageResponse(BaseModel):
    """Response schema for chat message response."""

    user_message: str
    assistant_response: str
