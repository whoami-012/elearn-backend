from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from jose import JWTError
from google.auth.exceptions import GoogleAuthError
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from sqlalchemy.exc import IntegrityError

from app.models.user import User
from app.schemas.auth import RegisterRequest        # Fix #5: correct type hint (was UserCreate)
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from fastapi import HTTPException, status
from app.core.config import settings


# 🔹 Create User (Register)
async def create_user(db: AsyncSession, user_data: RegisterRequest):
    # Normalize input email to lowercase
    email = user_data.email.lower().strip()

    # Case-insensitive check: func.lower() on DB column matches both old and new records
    result = await db.execute(select(User).where(func.lower(User.email) == email))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = User(
        email=email,                                       # stored as lowercase
        name=user_data.name,
        password_hash=hash_password(user_data.password),
        role="student",
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user


# 🔹 Authenticate User (Login)
async def authenticate_user(db: AsyncSession, email: str, password: str):
    # Normalize input email to lowercase
    email = email.lower().strip()

    # Case-insensitive match: handles old records stored with mixed-case emails
    result = await db.execute(select(User).where(func.lower(User.email) == email))
    user = result.scalar_one_or_none()

    # Intentionally vague error — don't reveal whether email exists
    if not user or not user.password_hash or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive",
        )

    if user.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account has been deleted",
        )

    return user


async def change_password(
    db: AsyncSession,
    user: User,
    current_password: str,
    new_password: str,
) -> None:
    """Verify the current password before replacing the stored password hash."""
    if not user.password_hash or not verify_password(current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    user.password_hash = hash_password(new_password)
    await db.commit()


def verify_google_id_token(token: str) -> dict:
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google Sign-In is not configured",
        )

    try:
        claims = google_id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            audience=settings.GOOGLE_CLIENT_ID,
        )
    except (ValueError, GoogleAuthError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Google ID token",
        )

    if not claims.get("email"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google account does not provide an email address",
        )
    if claims.get("email_verified") is not True:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Google email address is not verified",
        )
    if not claims.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google token payload",
        )
    return claims


async def authenticate_google_user(db: AsyncSession, claims: dict) -> User:
    email = claims["email"].lower().strip()
    google_id = claims["sub"]
    result = await db.execute(
        select(User).where(
            or_(func.lower(User.email) == email, User.google_id == google_id)
        )
    )
    matches = result.scalars().all()
    by_email = next((user for user in matches if user.email.lower() == email), None)
    by_google_id = next((user for user in matches if user.google_id == google_id), None)

    if by_email and by_google_id and by_email.id != by_google_id.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Google account is already linked to another user",
        )

    user = by_email or by_google_id
    if user and user.email.lower() != email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Google account email does not match the linked user",
        )

    if user:
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive")
        if user.is_deleted:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account has been deleted")
        user.google_id = google_id
        user.email_verified = True
        if claims.get("name"):
            user.name = claims["name"]
        if claims.get("picture"):
            user.profile_image = claims["picture"]
    else:
        user = User(
            email=email,
            name=claims.get("name") or email.split("@", 1)[0],
            password_hash=None,
            role="student",
            auth_provider="google",
            google_id=google_id,
            profile_image=claims.get("picture"),
            email_verified=True,
        )
        db.add(user)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Google account or email is already registered",
        )
    await db.refresh(user)
    return user


# 🔹 Create Tokens
def create_tokens(user: User) -> dict:
    # Fix #1: pass sub and role as separate positional args (not a dict, not str(a, b))
    access_token  = create_access_token(str(user.id), user.role)
    refresh_token = create_refresh_token(str(user.id), user.role)

    return {
        "access_token":  access_token,
        "refresh_token": refresh_token,
        "token_type":    "bearer",
    }


# 🔹 Refresh Access Token
def refresh_access_token(refresh_token: str) -> dict:
    # Fix #2: decode_token raises JWTError on failure — it never returns None
    try:
        payload = decode_token(refresh_token)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    # Fix #3: enforce that this token is actually a refresh token
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is not a refresh token",
        )

    user_id = payload.get("sub")
    user_role = payload.get("role")

    if not user_id or not user_role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    # Fix #4: return both access AND refresh token (TokenResponse requires both)
    return {
        "access_token":  create_access_token(user_id, user_role),
        "refresh_token": create_refresh_token(user_id, user_role),
        "token_type":    "bearer",
    }
