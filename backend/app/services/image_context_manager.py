"""Image context manager for handling follow-up questions about images."""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ImageContextManager:
    """Manages image context for follow-up questions in conversations."""
    
    # In-memory storage for image contexts (conversation_id -> image_data)
    _image_cache: Dict[int, Dict[str, Any]] = {}
    
    # Cache expiration time (12 hours)
    _CACHE_EXPIRATION = timedelta(hours=12)
    
    @staticmethod
    def is_followup_question(user_message: str) -> bool:
        """
        Check if the user message indicates a follow-up question about an image.
        
        Args:
            user_message: The user's message text.
            
        Returns:
            True if the message appears to be a follow-up about an image, False otherwise.
        """
        followup_keywords = [
            "this image", "that image", "the image", "that picture", "this picture",
            "describe", "what", "explain", "analyze", "tell me about", "what is",
            "can you see", "do you see", "look at", "in the image", "in this image",
            "previous image", "earlier image", "last image", "the photo", "this photo"
        ]
        
        message_lower = user_message.lower()
        return any(keyword in message_lower for keyword in followup_keywords)
    
    @staticmethod
    def store_image_context(
        conversation_id: int,
        image_data: str,
        filename: str,
        initial_analysis: str = ""
    ) -> None:
        """
        Store image context for a conversation to enable follow-up questions.
        
        Args:
            conversation_id: The conversation ID.
            image_data: The image data (base64 or data URL).
            filename: The original filename.
            initial_analysis: Optional initial analysis of the image.
        """
        ImageContextManager._image_cache[conversation_id] = {
            "image_data": image_data,
            "filename": filename,
            "initial_analysis": initial_analysis,
            "timestamp": datetime.now(),
        }
        logger.info(f"[ImageContextManager] Stored image context for conversation {conversation_id}")
    
    @staticmethod
    def get_image_context(conversation_id: int) -> Optional[Dict[str, Any]]:
        """
        Get the stored image context for a conversation.
        
        Args:
            conversation_id: The conversation ID.
            
        Returns:
            Dictionary with image context if found and not expired, None otherwise.
        """
        if conversation_id not in ImageContextManager._image_cache:
            return None
        
        cached_data = ImageContextManager._image_cache[conversation_id]
        
        # Check if cache has expired
        if datetime.now() - cached_data["timestamp"] > ImageContextManager._CACHE_EXPIRATION:
            del ImageContextManager._image_cache[conversation_id]
            logger.info(f"[ImageContextManager] Image context expired for conversation {conversation_id}")
            return None
        
        return cached_data
    
    @staticmethod
    def build_followup_message_with_image(
        user_question: str,
        image_data: str,
        filename: str,
    ) -> str:
        """
        Build a follow-up message that includes the previous image reference.
        
        Args:
            user_question: The user's follow-up question.
            image_data: The image data (base64 or data URL).
            filename: The original filename.
            
        Returns:
            Formatted message with image data embedded.
        """
        # Format: [IMAGE]data_url[/IMAGE]\nUser question
        message = f"[IMAGE_REFERENCE: {filename}]\n{image_data}\n\nUser question: {user_question}"
        return message
    
    @staticmethod
    def clear_image_context(conversation_id: int) -> None:
        """
        Clear the image context for a conversation.
        
        Args:
            conversation_id: The conversation ID.
        """
        if conversation_id in ImageContextManager._image_cache:
            del ImageContextManager._image_cache[conversation_id]
            logger.info(f"[ImageContextManager] Cleared image context for conversation {conversation_id}")
    
    @staticmethod
    def cleanup_expired_contexts() -> None:
        """Remove all expired image contexts from the cache."""
        expired_ids = []
        current_time = datetime.now()
        
        for conv_id, cached_data in ImageContextManager._image_cache.items():
            if current_time - cached_data["timestamp"] > ImageContextManager._CACHE_EXPIRATION:
                expired_ids.append(conv_id)
        
        for conv_id in expired_ids:
            del ImageContextManager._image_cache[conv_id]
        
        if expired_ids:
            logger.info(f"[ImageContextManager] Cleaned up {len(expired_ids)} expired contexts")
