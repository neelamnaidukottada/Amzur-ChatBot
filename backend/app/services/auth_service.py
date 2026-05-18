"""Authentication service for user management and JWT tokens."""

from sqlalchemy.orm import Session
from google.auth.transport import requests
from google.oauth2 import id_token

from app.core.models import User
from app.core.auth import hash_password, verify_password, create_access_token
from app.core.settings import settings
from app.schemas.auth import UserRegister, UserLogin, TokenResponse


class AuthService:
    """Service for authentication operations."""

    @staticmethod
    def register_user(db: Session, user_data: UserRegister) -> User:
        """
        Register a new user.
        
        Args:
            db: Database session.
            user_data: User registration data.
            
        Returns:
            Created user.
            
        Raises:
            ValueError: If email already exists.
        """
        # Check if email already exists
        existing_user = db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            raise ValueError(f"Email {user_data.email} already registered")
        
        # Create new user
        user = User(
            email=user_data.email,
            full_name=user_data.full_name,
            hashed_password=hash_password(user_data.password),
            is_active=True,
            auth_provider="email",
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def authenticate_user(db: Session, email: str, password: str) -> User:
        """
        Authenticate a user.
        
        Args:
            db: Database session.
            email: User email.
            password: User password.
            
        Returns:
            Authenticated user.
            
        Raises:
            ValueError: If authentication fails.
        """
        user = db.query(User).filter(User.email == email).first()
        
        if not user:
            raise ValueError("Invalid email or password")
        
        if not user.hashed_password or not verify_password(password, user.hashed_password):
            raise ValueError("Invalid email or password")
        
        if not user.is_active:
            raise ValueError("User account is inactive")
        
        return user

    @staticmethod
    def authenticate_google_user(db: Session, token: str) -> User:
        """
        Authenticate a user via Google OAuth.
        
        Args:
            db: Database session.
            token: Google OAuth token from frontend.
            
        Returns:
            User object (creates new user if doesn't exist).
            
        Raises:
            ValueError: If token verification fails.
        """
        try:
            # Verify and decode Google token
            idinfo = id_token.verify_oauth2_token(
                token, requests.Request(), settings.GOOGLE_CLIENT_ID
            )
            
            # Extract user info from token
            google_id = idinfo.get("sub")
            email = idinfo.get("email")
            full_name = idinfo.get("name", email.split("@")[0])
            
            if not google_id or not email:
                raise ValueError("Invalid Google token: missing required fields")
            
            # Check if user with this Google ID exists
            user = db.query(User).filter(User.google_id == google_id).first()
            
            if user:
                # Update user info if needed
                user.google_email = email
                user.updated_at = __import__("datetime").datetime.utcnow()
                db.commit()
                db.refresh(user)
                return user
            
            # Check if user with this email exists (from previous email/password signup)
            user = db.query(User).filter(User.email == email).first()
            
            if user:
                # Link Google account to existing user
                user.google_id = google_id
                user.google_email = email
                user.auth_provider = "google"
                user.updated_at = __import__("datetime").datetime.utcnow()
                db.commit()
                db.refresh(user)
                return user
            
            # Create new Google user
            user = User(
                email=email,
                google_id=google_id,
                google_email=email,
                full_name=full_name,
                hashed_password=None,  # No password for OAuth users
                is_active=True,
                auth_provider="google",
            )
            
            db.add(user)
            db.commit()
            db.refresh(user)
            return user
            
        except ValueError as e:
            raise ValueError(f"Google authentication failed: {str(e)}")
        except Exception as e:
            raise ValueError(f"Google token verification failed: {str(e)}")

    @staticmethod
    def get_user_by_email(db: Session, email: str) -> User:
        """Get user by email."""
        return db.query(User).filter(User.email == email).first()

    @staticmethod
    def create_token_response(user: User, auth_provider: str = None) -> TokenResponse:
        """Create a token response for authenticated user."""
        access_token = create_access_token(data={"sub": user.email})
        provider = auth_provider or user.auth_provider or "email"
        return TokenResponse(
            access_token=access_token,
            user_email=user.email,
            user_name=user.full_name or user.email,
            auth_provider=provider,
        )
