"""Session and caching service for managing DataFrame instances."""

import logging
import uuid
from typing import Optional, Dict, List
from datetime import datetime, timedelta
import pandas as pd

logger = logging.getLogger(__name__)


class DataframeSession:
    """Represents a single dataframe session with metadata."""

    def __init__(self, dataset_id: str, filename: str, df: pd.DataFrame, source: str = "file"):
        """
        Initialize a dataframe session.

        Args:
            dataset_id: Unique identifier for this dataset
            filename: Original filename or source identifier
            df: The pandas DataFrame
            source: Source type ('file', 'google_sheet', etc.)
        """
        self.dataset_id = dataset_id
        self.filename = filename
        self.df = df
        self.source = source
        self.created_at = datetime.now()
        self.last_accessed = datetime.now()
        self.query_count = 0
        self.conversation_history: List[Dict[str, str]] = []

    def update_access(self):
        """Update last access timestamp."""
        self.last_accessed = datetime.now()

    def add_to_history(self, question: str, answer: str):
        """
        Add a Q&A pair to conversation history.

        Args:
            question: User question
            answer: AI answer
        """
        self.conversation_history.append(
            {"question": question, "answer": answer, "timestamp": datetime.now()}
        )
        self.query_count += 1

    def get_context_summary(self, max_entries: int = 5) -> str:
        """
        Get a summary of recent conversation for context.

        Args:
            max_entries: Maximum number of recent entries to include

        Returns:
            Formatted context string
        """
        if not self.conversation_history:
            return ""

        recent = self.conversation_history[-max_entries:]
        context_lines = []
        for item in recent:
            context_lines.append(f"Q: {item['question']}")
            context_lines.append(f"A: {item['answer']}")
            context_lines.append("---")

        return "\n".join(context_lines)

    def to_dict(self) -> Dict:
        """Convert session to dictionary."""
        return {
            "dataset_id": self.dataset_id,
            "filename": self.filename,
            "source": self.source,
            "shape": {"rows": len(self.df), "columns": len(self.df.columns)},
            "columns": list(self.df.columns),
            "created_at": self.created_at.isoformat(),
            "last_accessed": self.last_accessed.isoformat(),
            "query_count": self.query_count,
        }


class DataframeSessionService:
    """Service for managing dataframe sessions with in-memory caching."""

    def __init__(self, ttl_minutes: int = 60):
        """
        Initialize the session service.

        Args:
            ttl_minutes: Time-to-live for sessions in minutes
        """
        self.sessions: Dict[str, DataframeSession] = {}
        self.ttl = timedelta(minutes=ttl_minutes)
        logger.info(f"[DataframeSessionService] Initialized with {ttl_minutes} min TTL")

    def create_session(
        self, filename: str, df: pd.DataFrame, source: str = "file"
    ) -> str:
        """
        Create a new dataframe session.

        Args:
            filename: Original filename or source identifier
            df: The pandas DataFrame
            source: Source type ('file', 'google_sheet', etc.)

        Returns:
            Dataset ID for the created session
        """
        dataset_id = str(uuid.uuid4())
        session = DataframeSession(dataset_id, filename, df, source)
        self.sessions[dataset_id] = session

        logger.info(
            f"[DataframeSessionService] Created session {dataset_id}: {filename}"
        )
        return dataset_id

    def get_session(self, dataset_id: str) -> Optional[DataframeSession]:
        """
        Get a dataframe session by ID.

        Args:
            dataset_id: The dataset ID

        Returns:
            DataframeSession or None if not found or expired
        """
        if dataset_id not in self.sessions:
            logger.warning(f"[DataframeSessionService] Session not found: {dataset_id}")
            return None

        session = self.sessions[dataset_id]

        # Check if session has expired
        if datetime.now() - session.last_accessed > self.ttl:
            logger.info(
                f"[DataframeSessionService] Session expired: {dataset_id}"
            )
            del self.sessions[dataset_id]
            return None

        session.update_access()
        return session

    def delete_session(self, dataset_id: str) -> bool:
        """
        Delete a dataframe session.

        Args:
            dataset_id: The dataset ID

        Returns:
            True if deleted, False if not found
        """
        if dataset_id in self.sessions:
            logger.info(
                f"[DataframeSessionService] Deleting session: {dataset_id}"
            )
            del self.sessions[dataset_id]
            return True

        return False

    def list_sessions(self) -> List[Dict]:
        """
        List all active sessions.

        Returns:
            List of session dictionaries
        """
        # Clean up expired sessions
        expired_ids = []
        for dataset_id, session in self.sessions.items():
            if datetime.now() - session.last_accessed > self.ttl:
                expired_ids.append(dataset_id)

        for dataset_id in expired_ids:
            logger.info(
                f"[DataframeSessionService] Cleaning expired session: {dataset_id}"
            )
            del self.sessions[dataset_id]

        sessions = [session.to_dict() for session in self.sessions.values()]
        logger.info(
            f"[DataframeSessionService] Listing {len(sessions)} active sessions"
        )
        return sessions

    def add_to_history(self, dataset_id: str, question: str, answer: str) -> bool:
        """
        Add Q&A to session history.

        Args:
            dataset_id: The dataset ID
            question: User question
            answer: AI answer

        Returns:
            True if added, False if session not found
        """
        session = self.get_session(dataset_id)
        if not session:
            return False

        session.add_to_history(question, answer)
        logger.info(
            f"[DataframeSessionService] Added to history for {dataset_id}"
        )
        return True

    def get_context(self, dataset_id: str, max_entries: int = 5) -> str:
        """
        Get context summary for a session.

        Args:
            dataset_id: The dataset ID
            max_entries: Maximum recent entries

        Returns:
            Context string
        """
        session = self.get_session(dataset_id)
        if not session:
            return ""

        return session.get_context_summary(max_entries)

    def cleanup_expired(self):
        """Remove all expired sessions."""
        now = datetime.now()
        expired_ids = [
            dataset_id
            for dataset_id, session in self.sessions.items()
            if now - session.last_accessed > self.ttl
        ]

        for dataset_id in expired_ids:
            logger.info(
                f"[DataframeSessionService] Cleaning up expired session: {dataset_id}"
            )
            del self.sessions[dataset_id]

        if expired_ids:
            logger.info(
                f"[DataframeSessionService] Cleaned {len(expired_ids)} expired sessions"
            )


# Global session service instance
_session_service: Optional[DataframeSessionService] = None


def get_dataframe_session_service() -> DataframeSessionService:
    """Get or create global dataframe session service."""
    global _session_service
    if _session_service is None:
        _session_service = DataframeSessionService(ttl_minutes=60)
    return _session_service
