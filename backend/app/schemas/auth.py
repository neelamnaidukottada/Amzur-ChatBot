"""Pydantic schemas for authentication."""

from pydantic import BaseModel, EmailStr, Field


class UserRegister(BaseModel):
    """Schema for user registration."""

    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    full_name: str = Field(..., min_length=1, max_length=255)


class UserLogin(BaseModel):
    """Schema for user login."""

    email: EmailStr
    password: str = Field(..., min_length=1)


class GoogleLoginRequest(BaseModel):
    """Schema for Google login request."""

    token: str = Field(..., description="Google OAuth token from frontend")


class TokenResponse(BaseModel):
    """Schema for token response."""

    access_token: str
    token_type: str = "bearer"
    user_email: str
    user_name: str
    auth_provider: str = "email"


class UserResponse(BaseModel):
    """Schema for user response."""

    id: int
    email: str
    full_name: str
    auth_provider: str
    created_at: str

    class Config:
        from_attributes = True
