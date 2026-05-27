"""Authentication router - HTTP endpoints for auth."""

from fastapi import APIRouter, HTTPException, Depends, status, BackgroundTasks
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.auth import UserRegister, UserLogin, TokenResponse, GoogleLoginRequest
from app.services.auth_service import AuthService
from app.services.n8n_service import triggerUserOnboardingWebhook

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
async def register(
    user_data: UserRegister,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """
    Register a new user.
    
    Args:
        user_data: User registration data.
        db: Database session.
        
    Returns:
        Token response with access token.
    """
    try:
        user = AuthService.register_user(db, user_data)
        background_tasks.add_task(triggerUserOnboardingWebhook, user)
        return AuthService.create_token_response(user, auth_provider="email")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: UserLogin,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """
    Login user and get access token.
    
    Args:
        credentials: User credentials.
        db: Database session.
        
    Returns:
        Token response with access token.
    """
    try:
        user = AuthService.authenticate_user(db, credentials.email, credentials.password)
        return AuthService.create_token_response(user, auth_provider="email")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )


@router.post("/google", response_model=TokenResponse)
async def google_login(
    request: GoogleLoginRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """
    Login user via Google OAuth.
    
    Args:
        request: Google login request with token.
        db: Database session.
        
    Returns:
        Token response with access token.
    """
    try:
        user, created_new_user = AuthService.authenticate_google_user(db, request.token)
        if created_new_user:
            background_tasks.add_task(triggerUserOnboardingWebhook, user)
        return AuthService.create_token_response(user, auth_provider="google")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )


@router.get("/me")
async def get_current_user(
    email: str = Depends(lambda db: None),  # Placeholder
    db: Session = Depends(get_db),
):
    """Get current authenticated user info."""
    # This will be improved with proper dependency
    pass
