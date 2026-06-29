from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.dependencies import get_db
from app.schemas.auth import (
    AppleLoginRequest,
    AppleLoginResponse,
    GoogleLoginRequest,
    GoogleLoginResponse,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    RefreshTokenRequest,
)
from app.schemas.user import UserPasswordRequest, UserRead
from app.services.auth_service import (
    create_user,
    authenticate_user,
    create_tokens,
    refresh_access_token,
    authenticate_google_user,
    authenticate_apple_user,
    change_password,
    verify_google_id_token,
    verify_apple_id_token,
)
from app.api.deps import get_current_user
from app.models.user import User
from typing import Optional
from starlette.concurrency import run_in_threadpool

router = APIRouter(prefix="/auth", tags=["Auth"])
google_router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)  # Fix #8
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)):
    user = await create_user(db, payload)
    return user

@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(db, payload.email, payload.password)
    tokens = create_tokens(user)
    return tokens


async def _google_login(payload: GoogleLoginRequest, db: AsyncSession):
    claims = await run_in_threadpool(verify_google_id_token, payload.id_token)
    user = await authenticate_google_user(db, claims)
    return {
        **create_tokens(user),
        "success": True,
        "message": "Google login successful",
        "user": user,
    }


@router.post("/google-login/", response_model=GoogleLoginResponse)
async def google_login_v1(payload: GoogleLoginRequest, db: AsyncSession = Depends(get_db)):
    return await _google_login(payload, db)


@google_router.post("/google-login/", response_model=GoogleLoginResponse)
async def google_login(payload: GoogleLoginRequest, db: AsyncSession = Depends(get_db)):
    return await _google_login(payload, db)


async def _apple_login(payload: AppleLoginRequest, db: AsyncSession):
    claims = await run_in_threadpool(verify_apple_id_token, payload.id_token)
    user = await authenticate_apple_user(db, claims, payload.first_name, payload.last_name)
    return {**create_tokens(user), "success": True, "message": "Apple login successful", "user": user}


@router.post("/apple-login/", response_model=AppleLoginResponse)
async def apple_login_v1(payload: AppleLoginRequest, db: AsyncSession = Depends(get_db)):
    return await _apple_login(payload, db)


@google_router.post("/apple-login/", response_model=AppleLoginResponse)
async def apple_login(payload: AppleLoginRequest, db: AsyncSession = Depends(get_db)):
    return await _apple_login(payload, db)

@router.post("/refresh", response_model=TokenResponse)
async def refresh(payload: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    tokens = refresh_access_token(payload.refresh_token)
    return tokens

@router.get("/me", response_model=UserRead)
async def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def update_password(
    payload: UserPasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await change_password(
        db,
        current_user,
        payload.current_password,
        payload.new_password,
    )
