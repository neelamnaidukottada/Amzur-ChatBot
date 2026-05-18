"""Database models for users and conversations."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from app.core.database import Base


class User(Base):
    """User model for authentication."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=True)
    hashed_password = Column(String(255), nullable=True)  # Nullable for OAuth-only users
    is_active = Column(Boolean, default=True)
    
    # OAuth fields
    google_id = Column(String(255), unique=True, nullable=True, index=True)
    google_email = Column(String(255), nullable=True)
    auth_provider = Column(String(50), default="email")  # 'email', 'google', etc.
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    research_digests = relationship("ResearchDigest", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, provider={self.auth_provider})>"


class Conversation(Base):
    """Conversation model for storing chat history."""

    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(255), nullable=True, default="New Chat")
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    research_digests = relationship("ResearchDigest", back_populates="conversation", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Conversation(id={self.id}, user_id={self.user_id})>"


class Message(Base):
    """Message model for storing individual messages in a conversation."""

    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False, index=True)
    sender = Column(String(50), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")

    def __repr__(self) -> str:
        return f"<Message(id={self.id}, conversation_id={self.conversation_id}, sender={self.sender})>"


class ResearchDigest(Base):
    """Persisted research digest results linked to a conversation."""

    __tablename__ = "research_digests"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    query = Column(Text, nullable=False)
    filters_json = Column(Text, nullable=True)
    result_json = Column(Text, nullable=False)
    decision = Column(String(64), nullable=False)
    high_quality_papers_found = Column(Integer, nullable=False, default=0)
    total_unique_papers_scanned = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    conversation = relationship("Conversation", back_populates="research_digests")
    user = relationship("User", back_populates="research_digests")

    def __repr__(self) -> str:
        return f"<ResearchDigest(id={self.id}, conversation_id={self.conversation_id}, decision={self.decision})>"
