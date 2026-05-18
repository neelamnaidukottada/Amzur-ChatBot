"""Dataframe caching service for managing CSV/Excel and Google Sheets data."""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import pandas as pd

logger = logging.getLogger(__name__)


class CachedDataframe:
    """Represents a cached dataframe with metadata."""
    
    def __init__(self, df: pd.DataFrame, filename: str, source: str):
        """
        Initialize cached dataframe.
        
        Args:
            df: The pandas DataFrame
            filename: Original filename or identifier
            source: Source type (file, google_sheet, csv, excel)
        """
        self.df = df
        self.display_name = filename
        self.source = source
        self.timestamp = datetime.now()
        self.row_count = len(df)
        self.columns = list(df.columns)
    
    def is_expired(self, ttl_hours: int = 12) -> bool:
        """Check if cache has expired."""
        return datetime.now() - self.timestamp > timedelta(hours=ttl_hours)


class DataframeCache:
    """Simple in-memory cache for dataframes in conversations."""
    
    def __init__(self, ttl_hours: int = 12):
        """
        Initialize the cache.
        
        Args:
            ttl_hours: Time-to-live in hours for cached dataframes.
        """
        self._cache: Dict[int, CachedDataframe] = {}
        self.ttl_hours = ttl_hours
        logger.info(f"[DataframeCache] Initialized with TTL={ttl_hours} hours")
    
    def store(
        self,
        conversation_id: int,
        df: pd.DataFrame,
        filename: str,
        source: str = "file",
    ) -> None:
        """
        Store a dataframe in the cache.
        
        Args:
            conversation_id: The conversation ID to cache under
            df: The pandas DataFrame to cache
            filename: Original filename or identifier
            source: Source type (file, google_sheet, csv, excel)
        """
        cached = CachedDataframe(df, filename, source)
        self._cache[conversation_id] = cached
        logger.info(
            f"[DataframeCache] Stored {source} for conv_id={conversation_id}: "
            f"{filename} ({cached.row_count} rows, {len(cached.columns)} cols)"
        )
    
    def retrieve(self, conversation_id: int) -> Optional[CachedDataframe]:
        """
        Retrieve a cached dataframe.
        
        Args:
            conversation_id: The conversation ID to retrieve from
            
        Returns:
            CachedDataframe if found and not expired, None otherwise
        """
        if conversation_id not in self._cache:
            logger.debug(f"[DataframeCache] No cache found for conv_id={conversation_id}")
            return None
        
        cached = self._cache[conversation_id]
        
        if cached.is_expired(self.ttl_hours):
            logger.info(f"[DataframeCache] Cache expired for conv_id={conversation_id}")
            del self._cache[conversation_id]
            return None
        
        logger.info(
            f"[DataframeCache] Retrieved {cached.source} for conv_id={conversation_id}: "
            f"{cached.display_name}"
        )
        return cached
    
    def clear(self, conversation_id: int) -> None:
        """
        Clear the cache for a conversation.
        
        Args:
            conversation_id: The conversation ID to clear
        """
        if conversation_id in self._cache:
            del self._cache[conversation_id]
            logger.info(f"[DataframeCache] Cleared cache for conv_id={conversation_id}")
    
    def clear_all(self) -> None:
        """Clear all cached dataframes."""
        count = len(self._cache)
        self._cache.clear()
        logger.info(f"[DataframeCache] Cleared all {count} cached dataframes")
    
    def cleanup_expired(self) -> int:
        """
        Remove all expired dataframes from cache.
        
        Returns:
            Number of expired entries removed
        """
        expired_ids = [
            cid for cid, cached in self._cache.items()
            if cached.is_expired(self.ttl_hours)
        ]
        
        for cid in expired_ids:
            del self._cache[cid]
        
        if expired_ids:
            logger.info(f"[DataframeCache] Cleaned up {len(expired_ids)} expired entries")
        
        return len(expired_ids)


# Global singleton instance
_dataframe_cache: Optional[DataframeCache] = None


def get_dataframe_cache() -> DataframeCache:
    """Get the global dataframe cache instance."""
    global _dataframe_cache
    if _dataframe_cache is None:
        _dataframe_cache = DataframeCache()
    return _dataframe_cache
