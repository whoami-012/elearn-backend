from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.db.dependencies import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.user import UserRead
from app.services import user_service

router = APIRouter(prefix="/users", tags=["Users (Admin)"])


def _require_admin(current_user: User) -> None:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )


@router.get("", response_model=list[UserRead])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Admin only: list all active users."""
    _require_admin(current_user)
    return await user_service.list_users(db, skip=skip, limit=limit)


@router.get("/{user_id}", response_model=UserRead)
async def get_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Admin only: get user by ID."""
    _require_admin(current_user)
    return await user_service.get_user_by_id(db, user_id)


@router.patch("/{user_id}/role", response_model=UserRead)
async def change_user_role(
    user_id: UUID,
    role: str = Query(..., description="New role: student | faculty | admin"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Admin only: change a user's role."""
    _require_admin(current_user)
    return await user_service.update_user_role(db, user_id, role, current_user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Admin only: soft-delete a user (sets is_deleted=True, is_active=False)."""
    _require_admin(current_user)
    await user_service.soft_delete_user(db, user_id, current_user)
