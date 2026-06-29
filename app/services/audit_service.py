from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.models.user import User


async def log_admin_action(
    db: AsyncSession,
    *,
    actor: User | None,
    action: str,
    resource_type: str,
    resource_id: str,
    old_values: dict[str, Any] | None = None,
    new_values: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditLog:
    entry = AuditLog(
        actor_user_id=actor.id if actor else None,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        old_values=old_values,
        new_values=new_values,
        metadata_json=metadata,
    )
    db.add(entry)
    await db.flush()
    return entry


async def list_audit_logs(
    db: AsyncSession,
    *,
    actor_user_id=None,
    action: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    skip: int = 0,
    limit: int = 50,
) -> list[AuditLog]:
    query = select(AuditLog).order_by(AuditLog.created_at.desc()).offset(skip).limit(limit)
    if actor_user_id:
        query = query.where(AuditLog.actor_user_id == actor_user_id)
    if action:
        query = query.where(AuditLog.action == action)
    if resource_type:
        query = query.where(AuditLog.resource_type == resource_type)
    if resource_id:
        query = query.where(AuditLog.resource_id == resource_id)
    if created_from:
        query = query.where(AuditLog.created_at >= created_from)
    if created_to:
        query = query.where(AuditLog.created_at <= created_to)
    result = await db.execute(query)
    return list(result.scalars().all())
