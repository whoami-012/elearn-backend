from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from jose import JWTError

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
    if not user or not verify_password(password, user.password_hash):
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