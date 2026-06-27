from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.dependencies import get_db
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, RefreshTokenRequest
from app.schemas.user import UserRead
from app.services.auth_service import (
    create_user,
    authenticate_user,
    create_tokens,
    refresh_access_token,
)
from app.api.deps import get_current_user
from app.models.user import User
from typing import Optional

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)  # Fix #8
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)):
    user = await create_user(db, payload)
    return user

@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(db, payload.email, payload.password)
    tokens = create_tokens(user)
    return tokens

@router.post("/refresh", response_model=TokenResponse)
async def refresh(payload: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    tokens = refresh_access_token(payload.refresh_token)
    return tokens

@router.get("/me", response_model=UserRead)
async def me(current_user: User = Depends(get_current_user)):
    return current_user