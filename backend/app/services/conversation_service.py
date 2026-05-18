"""Conversation service for managing chat history."""

from typing import List
from datetime import datetime
import re
from sqlalchemy.orm import Session
from app.core.models import Conversation, Message, User
from app.schemas.conversation import ConversationCreate, ConversationResponse, ConversationSummaryResponse


class ConversationService:
    """Service for conversation management."""

    @staticmethod
    def create_conversation(db: Session, user_id: int, title: str = None) -> Conversation:
        """
        Create a new conversation.
        
        Args:
            db: Database session.
            user_id: User ID.
            title: Conversation title (optional).
            
        Returns:
            Created conversation.
        """
        conversation = Conversation(
            user_id=user_id,
            title=title or "New Chat",
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        return conversation

    @staticmethod
    def generate_title_from_message(message: str, max_length: int = 50) -> str:
        """
        Generate a short title from a message.
        
        Args:
            message: The message to generate title from.
            max_length: Maximum length of generated title.
            
        Returns:
            Generated title.
        """
        # Remove extra whitespace and truncate
        title = message.strip()
        
        # Take first line if multiple lines
        if "\n" in title:
            title = title.split("\n")[0]
        
        # Truncate to max length and add ellipsis if needed
        if len(title) > max_length:
            title = title[:max_length].rstrip() + "..."
        
        # If empty, provide default
        if not title:
            title = "New Chat"
        
        return title

    @staticmethod
    def get_user_conversations(db: Session, user_id: int) -> List[ConversationSummaryResponse]:
        """
        Get all conversations for a user.
        
        Args:
            db: Database session.
            user_id: User ID.
            
        Returns:
            List of conversation summaries.
        """
        conversations = db.query(Conversation).filter(
            Conversation.user_id == user_id
        ).order_by(Conversation.updated_at.desc()).all()
        
        return [
            ConversationSummaryResponse(
                id=conv.id,
                title=conv.title,
                created_at=conv.created_at,
                updated_at=conv.updated_at,
                message_count=len(conv.messages),
            )
            for conv in conversations
        ]

    @staticmethod
    def get_conversation(db: Session, conversation_id: int, user_id: int) -> Conversation:
        """
        Get a specific conversation.
        
        Args:
            db: Database session.
            conversation_id: Conversation ID.
            user_id: User ID (for authorization).
            
        Returns:
            Conversation with messages.
            
        Raises:
            ValueError: If conversation not found or unauthorized.
        """
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        ).first()
        
        if not conversation:
            raise ValueError("Conversation not found")
        
        return conversation

    @staticmethod
    def add_message(
        db: Session,
        conversation_id: int,
        user_id: int,
        sender: str,
        content: str,
    ) -> Message:
        """
        Add a message to a conversation.
        
        Args:
            db: Database session.
            conversation_id: Conversation ID.
            user_id: User ID (for authorization).
            sender: Message sender ('user' or 'assistant').
            content: Message content.
            
        Returns:
            Created message.
            
        Raises:
            ValueError: If conversation not found or unauthorized.
        """
        # Verify conversation belongs to user
        conversation = ConversationService.get_conversation(db, conversation_id, user_id)
        
        # Auto-generate title from first user message if still "New Chat"
        if sender == "user" and conversation.title == "New Chat" and len(conversation.messages) == 0:
            conversation.title = ConversationService.generate_title_from_message(content)
        
        # Create message
        message = Message(
            conversation_id=conversation_id,
            sender=sender,
            content=content,
        )
        
        db.add(message)
        
        # Update conversation timestamp
        conversation.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(message)
        return message

    @staticmethod
    def get_file_context_from_conversation(db: Session, conversation_id: int) -> str:
        """
        Extract and return file content from previous user messages in the conversation.
        This allows follow-up questions to have access to previously uploaded file data.
        
        Args:
            db: Database session.
            conversation_id: Conversation ID.
            
        Returns:
            Concatenated file content from all previous messages, or empty string if none.
        """
        # Get all user messages in this conversation
        messages = db.query(Message).filter(
            Message.conversation_id == conversation_id,
            Message.sender == 'user',
        ).order_by(Message.created_at.asc()).all()
        
        file_contents = []
        
        for message in messages:
            # Extract file markers: ===== FILE START: filename ===== ... ===== FILE END: filename =====
            file_pattern = r'(===== FILE (?:START|ERROR): (.+?) =====\n([\s\S]*?)\n===== FILE (?:END|ERROR): )'
            matches = re.findall(file_pattern, message.content)
            
            for match in matches:
                filename = match[1]
                content = match[2]
                # Format as file marker for inclusion in new messages
                file_block = f"\n\n===== FILE START: {filename} =====\n{content}\n===== FILE END: {filename} ====="
                file_contents.append(file_block)
        
        return "".join(file_contents)

    @staticmethod
    def delete_conversation(db: Session, conversation_id: int, user_id: int) -> None:
        """
        Delete a conversation.
        
        Args:
            db: Database session.
            conversation_id: Conversation ID.
            user_id: User ID (for authorization).
            
        Raises:
            ValueError: If conversation not found or unauthorized.
        """
        conversation = ConversationService.get_conversation(db, conversation_id, user_id)
        db.delete(conversation)
        db.commit()

    @staticmethod
    def update_conversation_title(
        db: Session,
        conversation_id: int,
        user_id: int,
        title: str,
    ) -> Conversation:
        """
        Update conversation title.
        
        Args:
            db: Database session.
            conversation_id: Conversation ID.
            user_id: User ID (for authorization).
            title: New title.
            
        Returns:
            Updated conversation.
            
        Raises:
            ValueError: If conversation not found or unauthorized.
        """
        conversation = ConversationService.get_conversation(db, conversation_id, user_id)
        conversation.title = title
        db.commit()
        db.refresh(conversation)
        return conversation

    @staticmethod
    def get_previous_conversations(
        db: Session,
        user_id: int,
        current_conversation_id: int = None,
        limit: int = 5,
    ) -> List[Conversation]:
        """
        Get the previous conversations for a user (excluding current conversation).
        
        Args:
            db: Database session.
            user_id: User ID.
            current_conversation_id: Current conversation ID to exclude (optional).
            limit: Number of previous conversations to fetch (default: 5).
            
        Returns:
            List of previous conversations ordered by most recent first.
        """
        query = db.query(Conversation).filter(
            Conversation.user_id == user_id
        )
        
        # Exclude current conversation if provided
        if current_conversation_id:
            query = query.filter(Conversation.id != current_conversation_id)
        
        # Order by most recent first and limit
        conversations = query.order_by(Conversation.created_at.desc()).limit(limit).all()
        
        return conversations
