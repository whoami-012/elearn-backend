from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.permissions import require_admin
from app.db.dependencies import get_db
from app.models.user import User
from app.schemas.audit_log import AuditLogRead
from app.schemas.courses import CourseResponse
from app.schemas.user import AdminPasswordReset, AdminUserCreate, UserRead
from app.services import user_service
from app.services.audit_service import list_audit_logs

router = APIRouter(prefix="/users", tags=["Users (Admin)"])


@router.get("", response_model=list[UserRead])
async def list_all_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    search: str | None = Query(None),
    role: str | None = Query(None),
    is_active: bool | None = Query(None),
    include_deleted: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)
    return await user_service.list_users(
        db,
        skip=skip,
        limit=limit,
        search=search,
        role=role,
        is_active=is_active,
        include_deleted=include_deleted,
    )


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: AdminUserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)
    return await user_service.create_user(db, payload, current_user)


@router.get("/audit-logs", response_model=list[AuditLogRead])
async def get_audit_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    actor_user_id: UUID | None = Query(None),
    action: str | None = Query(None),
    resource_type: str | None = Query(None),
    resource_id: str | None = Query(None),
    created_from: datetime | None = Query(None),
    created_to: datetime | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)
    return await list_audit_logs(
        db,
        actor_user_id=actor_user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        created_from=created_from,
        created_to=created_to,
        skip=skip,
        limit=limit,
    )


@router.get("/{user_id}", response_model=UserRead)
async def get_user(
    user_id: UUID,
    include_deleted: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)
    return await user_service.get_user_by_id(db, user_id, include_deleted=include_deleted)


@router.get("/{user_id}/courses", response_model=list[CourseResponse])
async def get_user_courses(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)
    return await user_service.list_assigned_courses(db, user_id)


@router.patch("/{user_id}/role", response_model=UserRead)
async def change_user_role(
    user_id: UUID,
    role: str = Query(..., description="New role: student | faculty | admin"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)
    return await user_service.update_user_role(db, user_id, role, current_user)


@router.post("/{user_id}/activate", response_model=UserRead)
async def activate_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)
    return await user_service.set_user_active_status(db, user_id, True, current_user)


@router.post("/{user_id}/deactivate", response_model=UserRead)
async def deactivate_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)
    return await user_service.set_user_active_status(db, user_id, False, current_user)


@router.post("/{user_id}/restore", response_model=UserRead)
async def restore_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)
    return await user_service.restore_user(db, user_id, current_user)


@router.post("/{user_id}/reset-password", response_model=UserRead)
async def reset_user_password(
    user_id: UUID,
    payload: AdminPasswordReset,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)
    return await user_service.admin_reset_password(db, user_id, payload.new_password, current_user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)
    await user_service.soft_delete_user(db, user_id, current_user)
