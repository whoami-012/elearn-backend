"""
user.py — Pydantic schemas for user-related API operations.

Defines request/response models for:
- User registration and authentication
- Profile updates (self and admin)
- Password management
- Token responses
"""

from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from enum import Enum
from datetime import datetime
from uuid import UUID


class UserRole(str, Enum):
    """Enumeration of allowed user roles in the platform."""

    student = "student"   # Default role; can enroll in courses
    faculty = "faculty"   # Can create and manage courses
    admin = "admin"       # Full platform access and user management


class UserBase(BaseModel):
    """
    Shared base fields used across multiple user schemas.
    Inherited by UserCreate and used as a foundation for common fields.
    """

    email: EmailStr          # Must be a valid email format (validated by Pydantic)
    name: str                # Full display name of the user
    is_active: bool = True   # Account status; defaults to active on creation


class UserCreate(UserBase):
    """
    Schema for registering a new user.
    Extends UserBase with a password field and enforces password strength rules.
    """

    password: str  # Plain-text password; will be hashed before storage

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """
        Enforce minimum password strength requirements:
        - At least 8 characters long
        - Must contain at least one uppercase letter
        """
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(char.isupper() for char in v):
            raise ValueError("Password must contain an uppercase letter")
        return v


class UserUpdate(BaseModel):
    """
    Schema for users updating their own profile information.
    All fields are optional — only provided fields will be updated (PATCH semantics).
    """

    email: Optional[EmailStr] = None     # New email address (validated if provided)
    name: Optional[str] = None           # New display name
    is_active: Optional[bool] = None     # Toggle account active status


class UserRead(BaseModel):
    """
    Schema for returning user data in API responses.
    Includes all fields that are safe to expose publicly.
    """

    id: UUID             # Unique identifier for the user
    email: EmailStr      # User's email address
    name: str            # User's display name
    role: UserRole       # Role assigned to the user
    is_active: bool      # Whether the account is currently active
    created_at: datetime # Timestamp when the account was created
    updated_at: datetime # Timestamp of the last update

    class Config:
        # Allows this schema to be built from ORM model instances (SQLAlchemy)
        from_attributes = True


class UserLogin(BaseModel):
    """
    Schema for user login requests.
    Accepts email and password credentials for authentication.
    """

    email: EmailStr  # Registered email address
    password: str    # Plain-text password to verify against stored hash


class UserPasswordRequest(BaseModel):
    """
    Schema for authenticated users changing their own password.
    Requires both the current and new password for security verification.
    """

    current_password: str  # Must match the user's existing password
    new_password: str      # Replacement password (subject to strength validation)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        """Ensure the new password meets the minimum length requirement."""
        if len(v) < 8:
            raise ValueError("Weak password")
        return v


class UserDeleteRequest(BaseModel):
    """
    Schema for account deletion requests.
    Requires the user's current password as confirmation before deletion.
    """

    password: str  # Password confirmation to authorize account deletion


class AdminUserUpdate(BaseModel):
    """
    Schema for admin-level user updates.
    Extends standard update capabilities with role and soft-delete control.
    All fields are optional — only provided fields will be applied.
    """

    email: Optional[EmailStr] = None      # Update user's email
    name: Optional[str] = None            # Update user's display name
    role: Optional[UserRole] = None       # Reassign user role (e.g., promote to admin)
    is_active: Optional[bool] = None      # Enable or disable user account
    is_deleted: Optional[bool] = None     # Soft-delete or restore a user account


class Token(BaseModel):
    """
    Schema for JWT token responses returned after successful authentication.
    Contains both access and refresh tokens for session management.
    """

    access_token: str          # Short-lived JWT used to authorize API requests
    refresh_token: str         # Long-lived token used to obtain a new access token
    token_type: str = "bearer" # Token scheme; always 'bearer' for OAuth2 compliance

