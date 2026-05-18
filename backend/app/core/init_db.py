"""Database initialization utilities."""

from app.core.database import Base, engine
from app.core.models import User, Conversation, Message


def init_db():
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    init_db()
    print("Database tables created successfully!")
