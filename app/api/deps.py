from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError                            # Fix #1: was missing, caused NameError
from uuid import UUID
from fastapi.security import OAuth2PasswordBearer
from typing import Optional
from app.models.user import User
from app.core.security import decode_token
from app.db.dependencies import get_db               # Fix #2: get_db lives here, not in session.py
from app.repositories.user_repo import UserRepo

security = HTTPBearer()
security_optional = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    """
    FastAPI dependency that authenticates a request via Bearer JWT token.

    Flow:
      1. Extracts and decodes the JWT from the Authorization header.
      2. Resolves the user_id (sub claim) from the token payload.
      3. Loads the user from the database.
      4. Rejects inactive or soft-deleted accounts.

    Returns the authenticated User ORM instance on success.
    """
    token = credentials.credentials

    # --- Step 1: Decode & validate JWT ---
    try:
        payload = decode_token(token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    # --- Step 2: Extract and cast user_id ---
    raw_id = payload.get("sub")
    if not raw_id:
        raise HTTPException(status_code=401, detail="Invalid token payload: missing sub")

    try:
        user_id = UUID(raw_id)          # Fix #3: JWT sub is str; repo expects UUID
    except (ValueError, AttributeError):
        raise HTTPException(status_code=401, detail="Invalid token payload: malformed user ID")

    # --- Step 3: Load user from DB ---
    user = await UserRepo(db).get_by_id(user_id)

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    # --- Step 4: Guard checks ---
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User account is inactive")  # Fix #4: 403 not 401

    if user.is_deleted:
        raise HTTPException(status_code=403, detail="User account has been deleted")  # Fix #5: soft-delete guard

    return user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_optional),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    try:
        if not credentials:
            return None
        
        token = credentials.credentials
        if not token:
            return None

        payload = decode_token(token)
        raw_id = payload.get("sub")

        if not raw_id:
            return None

        try:
            user_id = UUID(raw_id)
        except (ValueError, AttributeError):
            return None

        user = await UserRepo(db).get_by_id(user_id)
        if not user or not user.is_active or user.is_deleted:
            return None

        return user

    except JWTError:
        return None
