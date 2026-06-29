from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import UserRole, normalized_role, require_admin
from app.core.security import hash_password
from app.models.course import Course
from app.models.user import User
from app.schemas.user import AdminUserCreate
from app.services.audit_service import log_admin_action


VALID_ROLES = {UserRole.STUDENT.value, UserRole.FACULTY.value, UserRole.ADMIN.value}


async def list_users(
    db: AsyncSession,
    *,
    skip: int = 0,
    limit: int = 50,
    search: str | None = None,
    role: str | None = None,
    is_active: bool | None = None,
    include_deleted: bool = False,
) -> list[User]:
    query = select(User).order_by(User.created_at.desc()).offset(skip).limit(limit)
    if not include_deleted:
        query = query.where(User.is_deleted.is_(False))
    if search:
        like = f"%{search.strip().lower()}%"
        query = query.where(or_(func.lower(User.name).like(like), func.lower(User.email).like(like)))
    if role:
        normalized = normalized_role(role)
        if normalized not in VALID_ROLES:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid role filter")
        query = query.where(User.role == normalized)
    if is_active is not None:
        query = query.where(User.is_active.is_(is_active))
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_user_by_id(db: AsyncSession, user_id: UUID, *, include_deleted: bool = False) -> User:
    query = select(User).where(User.id == user_id)
    if not include_deleted:
        query = query.where(User.is_deleted.is_(False))
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


async def create_user(db: AsyncSession, payload: AdminUserCreate, admin: User) -> User:
    require_admin(admin)
    email = payload.email.lower().strip()
    existing = await db.execute(select(User).where(func.lower(User.email) == email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        email=email,
        name=payload.name,
        password_hash=hash_password(payload.password),
        role=payload.role.value,
        is_active=payload.is_active,
    )
    db.add(user)
    await db.flush()
    await log_admin_action(
        db,
        actor=admin,
        action="user.create",
        resource_type="user",
        resource_id=str(user.id),
        new_values={"email": user.email, "name": user.name, "role": user.role, "is_active": user.is_active},
    )
    await db.commit()
    await db.refresh(user)
    return user


async def _active_admin_count(db: AsyncSession) -> int:
    result = await db.execute(
        select(func.count()).select_from(User).where(
            User.role == UserRole.ADMIN.value,
            User.is_active.is_(True),
            User.is_deleted.is_(False),
        )
    )
    return int(result.scalar_one())


async def _ensure_can_change_admin_state(db: AsyncSession, target: User, actor: User, *, new_role: str | None = None, new_is_active: bool | None = None, new_is_deleted: bool | None = None) -> None:
    if str(target.id) == str(actor.id):
        if new_role and normalized_role(new_role) != UserRole.ADMIN.value:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Admins cannot change their own role")
        if new_is_active is False:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Admins cannot deactivate themselves")
        if new_is_deleted:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Admins cannot delete themselves")

    if normalized_role(target.role) != UserRole.ADMIN.value:
        return

    if (
        (new_role and normalized_role(new_role) != UserRole.ADMIN.value)
        or new_is_active is False
        or new_is_deleted is True
    ):
        if await _active_admin_count(db) <= 1:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="The last active admin cannot be changed")


async def update_user_role(db: AsyncSession, user_id: UUID, new_role: str, admin: User) -> User:
    require_admin(admin)
    normalized = normalized_role(new_role)
    if normalized not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid role. Must be one of: {sorted(VALID_ROLES)}",
        )

    user = await get_user_by_id(db, user_id, include_deleted=True)
    await _ensure_can_change_admin_state(db, user, admin, new_role=normalized)
    old_values = {"role": normalized_role(user.role)}
    user.role = normalized
    await log_admin_action(
        db,
        actor=admin,
        action="user.role_changed",
        resource_type="user",
        resource_id=str(user.id),
        old_values=old_values,
        new_values={"role": user.role},
    )
    await db.commit()
    await db.refresh(user)
    return user


async def set_user_active_status(db: AsyncSession, user_id: UUID, is_active: bool, admin: User) -> User:
    require_admin(admin)
    user = await get_user_by_id(db, user_id, include_deleted=True)
    await _ensure_can_change_admin_state(db, user, admin, new_is_active=is_active)
    old_values = {"is_active": user.is_active}
    user.is_active = is_active
    await log_admin_action(
        db,
        actor=admin,
        action="user.activated" if is_active else "user.deactivated",
        resource_type="user",
        resource_id=str(user.id),
        old_values=old_values,
        new_values={"is_active": user.is_active},
    )
    await db.commit()
    await db.refresh(user)
    return user


async def soft_delete_user(db: AsyncSession, user_id: UUID, admin: User) -> None:
    require_admin(admin)
    user = await get_user_by_id(db, user_id, include_deleted=True)
    await _ensure_can_change_admin_state(db, user, admin, new_is_deleted=True)
    user.is_deleted = True
    user.is_active = False
    await log_admin_action(
        db,
        actor=admin,
        action="user.deleted",
        resource_type="user",
        resource_id=str(user.id),
        old_values={"is_active": True, "is_deleted": False},
        new_values={"is_active": user.is_active, "is_deleted": user.is_deleted},
    )
    await db.commit()


async def restore_user(db: AsyncSession, user_id: UUID, admin: User) -> User:
    require_admin(admin)
    user = await get_user_by_id(db, user_id, include_deleted=True)
    old_values = {"is_deleted": user.is_deleted, "is_active": user.is_active}
    user.is_deleted = False
    user.is_active = True
    await log_admin_action(
        db,
        actor=admin,
        action="user.restored",
        resource_type="user",
        resource_id=str(user.id),
        old_values=old_values,
        new_values={"is_deleted": user.is_deleted, "is_active": user.is_active},
    )
    await db.commit()
    await db.refresh(user)
    return user


async def admin_reset_password(db: AsyncSession, user_id: UUID, new_password: str, admin: User) -> User:
    require_admin(admin)
    user = await get_user_by_id(db, user_id, include_deleted=True)
    user.password_hash = hash_password(new_password)
    await log_admin_action(
        db,
        actor=admin,
        action="user.password_reset",
        resource_type="user",
        resource_id=str(user.id),
        metadata={"forced_reset": True},
    )
    await db.commit()
    await db.refresh(user)
    return user


async def list_assigned_courses(db: AsyncSession, user_id: UUID) -> list[Course]:
    result = await db.execute(
        select(Course).where(Course.faculty_id == user_id, Course.is_deleted.is_(False)).order_by(Course.created_at.desc())
    )
    return list(result.scalars().all())
