from datetime import datetime, timezone
import hashlib
import logging
import secrets
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.live_class import LiveClass, LiveClassAttendance
from app.models.user import User
from app.schemas.live_class import LiveClassCreate, LiveClassUpdate
from app.services.agora_service import AgoraTokenService
from app.services.notification_service import notification_service

logger = logging.getLogger("audit.live_classes")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _duration_status(seconds: int, class_minutes: int) -> str:
    if seconds <= 0:
        return "absent"
    return "present" if seconds >= class_minutes * 60 * settings.LIVE_CLASS_ATTENDANCE_THRESHOLD else "partial"


async def _get(db: AsyncSession, class_id: UUID, lock: bool = False) -> LiveClass:
    query = select(LiveClass).options(selectinload(LiveClass.faculty)).where(LiveClass.id == class_id)
    if lock:
        query = query.with_for_update()
    item = (await db.execute(query)).scalar_one_or_none()
    if not item:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Live class not found")
    return item


async def _is_enrolled(db: AsyncSession, user_id: UUID, course_id: UUID) -> bool:
    row = await db.execute(select(Enrollment.id).where(
        Enrollment.user_id == user_id, Enrollment.course_id == course_id, Enrollment.is_active.is_(True)
    ))
    return row.scalar_one_or_none() is not None


def _assert_owner(item: LiveClass, user: User) -> None:
    if user.role != "admin" and (user.role != "faculty" or item.faculty_id != user.id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You do not manage this live class")


async def create_live_class(db: AsyncSession, data: LiveClassCreate, user: User) -> LiveClass:
    if user.role not in ("faculty", "admin"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only faculty or admin can schedule live classes")
    course = (await db.execute(select(Course).where(Course.id == data.course_id, Course.is_deleted.is_(False)))).scalar_one_or_none()
    if not course:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Course not found")
    if user.role != "admin" and course.faculty_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Faculty can only schedule classes for their own courses")
    faculty_id = course.faculty_id if user.role == "admin" else user.id
    if not faculty_id:
        raise HTTPException(status.HTTP_409_CONFLICT, "Course has no assigned faculty")
    minutes = max(1, int((data.scheduled_end_time - data.scheduled_start_time).total_seconds() / 60))
    item = LiveClass(
        course_id=course.id, faculty_id=faculty_id, title=data.title.strip(), description=data.description,
        agora_channel_name=f"course_{str(course.id)[:8]}_{secrets.token_urlsafe(18)}",
        scheduled_start_time=data.scheduled_start_time, scheduled_end_time=data.scheduled_end_time,
        duration_minutes=minutes,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    logger.info("created live_class=%s actor=%s", item.id, user.id)
    await notification_service.publish("scheduled", item.id, item.course_id)
    return await _get(db, item.id)


async def list_live_classes(db: AsyncSession, user: User, class_status: str | None = None) -> list[LiveClass]:
    query = select(LiveClass).options(selectinload(LiveClass.faculty)).order_by(LiveClass.scheduled_start_time)
    if class_status:
        query = query.where(LiveClass.status == class_status)
    if user.role == "faculty":
        query = query.where(LiveClass.faculty_id == user.id)
    elif user.role == "student":
        query = query.join(Enrollment, Enrollment.course_id == LiveClass.course_id).where(
            Enrollment.user_id == user.id, Enrollment.is_active.is_(True)
        )
    return list((await db.execute(query)).scalars().unique().all())


async def get_visible(db: AsyncSession, class_id: UUID, user: User) -> LiveClass:
    item = await _get(db, class_id)
    if user.role == "admin" or (user.role == "faculty" and item.faculty_id == user.id):
        return item
    if user.role == "student" and await _is_enrolled(db, user.id, item.course_id):
        return item
    raise HTTPException(status.HTTP_403_FORBIDDEN, "You cannot access this live class")


async def update_live_class(db: AsyncSession, class_id: UUID, data: LiveClassUpdate, user: User) -> LiveClass:
    item = await _get(db, class_id, True)
    _assert_owner(item, user)
    if item.status != "scheduled":
        raise HTTPException(status.HTTP_409_CONFLICT, "Only scheduled classes can be edited")
    values = data.model_dump(exclude_unset=True)
    start = values.get("scheduled_start_time", item.scheduled_start_time)
    end = values.get("scheduled_end_time", item.scheduled_end_time)
    if start.tzinfo is None or end.tzinfo is None or end <= start:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "End time must be after start time and include timezone")
    for key, value in values.items():
        setattr(item, key, value.astimezone(timezone.utc) if isinstance(value, datetime) else value)
    item.duration_minutes = max(1, int((end - start).total_seconds() / 60))
    await db.commit()
    await db.refresh(item)
    logger.info("rescheduled live_class=%s actor=%s", item.id, user.id)
    await notification_service.publish("rescheduled", item.id, item.course_id)
    return await _get(db, item.id)


async def _student_attendance(db: AsyncSession, item: LiveClass, user: User) -> LiveClassAttendance:
    now = utcnow()
    result = await db.execute(select(LiveClassAttendance).where(
        LiveClassAttendance.live_class_id == item.id, LiveClassAttendance.student_id == user.id
    ).with_for_update())
    attendance = result.scalar_one_or_none()
    if attendance:
        if attendance.left_at is not None:
            attendance.joined_at = now
            attendance.left_at = None
        attendance.last_seen_at = now
        return attendance
    seed = int.from_bytes(hashlib.sha256(f"{item.id}:{user.id}".encode()).digest()[:4], "big")
    uid = max(2, seed)
    used = set((await db.execute(select(LiveClassAttendance.agora_uid).where(
        LiveClassAttendance.live_class_id == item.id
    ))).scalars().all())
    while uid in used or uid == 1:
        uid = secrets.randbelow(0xFFFFFFFD) + 2
    attendance = LiveClassAttendance(
        live_class_id=item.id, student_id=user.id, agora_uid=uid, joined_at=now, last_seen_at=now
    )
    db.add(attendance)
    return attendance


async def credentials(db: AsyncSession, class_id: UUID, user: User, refresh: bool = False):
    item = await _get(db, class_id, True)
    broadcaster = user.role == "faculty" and item.faculty_id == user.id
    if user.role == "admin" and not broadcaster:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admins monitor classes but do not join RTC channels")
    if not broadcaster:
        if user.role != "student" or not await _is_enrolled(db, user.id, item.course_id):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Active course enrollment is required")
        if not refresh and utcnow() < item.scheduled_start_time - __import__("datetime").timedelta(minutes=settings.LIVE_CLASS_EARLY_JOIN_MINUTES):
            raise HTTPException(status.HTTP_409_CONFLICT, "Class is not open for joining yet")
    if item.status in ("completed", "cancelled"):
        raise HTTPException(status.HTTP_409_CONFLICT, f"Class is {item.status}")
    if item.status != "live" and not broadcaster:
        raise HTTPException(status.HTTP_409_CONFLICT, "Class has not started")
    if broadcaster:
        uid = 1
    else:
        if refresh:
            attendance = (await db.execute(select(LiveClassAttendance).where(
                LiveClassAttendance.live_class_id == item.id,
                LiveClassAttendance.student_id == user.id,
                LiveClassAttendance.left_at.is_(None),
            ).with_for_update())).scalar_one_or_none()
            if not attendance:
                raise HTTPException(status.HTTP_409_CONFLICT, "No active participation to refresh")
        else:
            attendance = await _student_attendance(db, item, user)
        uid = attendance.agora_uid
    await db.commit()
    try:
        credential = AgoraTokenService().issue(item.agora_channel_name, uid, broadcaster, item.duration_minutes)
    except RuntimeError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc
    logger.info("token_issued live_class=%s actor=%s role=%s", item.id, user.id, "broadcaster" if broadcaster else "audience")
    return item, uid, broadcaster, credential


async def start_class(db: AsyncSession, class_id: UUID, user: User):
    item = await _get(db, class_id, True)
    _assert_owner(item, user)
    if user.role == "admin" and item.faculty_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only assigned faculty can start a class")
    if item.status == "scheduled":
        item.status, item.started_at = "live", utcnow()
        await db.commit()
        logger.info("started live_class=%s actor=%s", item.id, user.id)
        await notification_service.publish("started", item.id, item.course_id)
    elif item.status != "live":
        raise HTTPException(status.HTTP_409_CONFLICT, f"Class is {item.status}")
    return await credentials(db, class_id, user)


async def heartbeat(db: AsyncSession, class_id: UUID, user: User) -> LiveClassAttendance:
    item = await _get(db, class_id)
    if item.status != "live" or user.role != "student":
        raise HTTPException(status.HTTP_409_CONFLICT, "No active student participation")
    row = (await db.execute(select(LiveClassAttendance).where(
        LiveClassAttendance.live_class_id == item.id, LiveClassAttendance.student_id == user.id,
        LiveClassAttendance.left_at.is_(None)
    ).with_for_update())).scalar_one_or_none()
    if not row:
        raise HTTPException(status.HTTP_409_CONFLICT, "Join the class before sending heartbeats")
    row.last_seen_at = max(row.last_seen_at, utcnow())
    await db.commit()
    await db.refresh(row)
    return row


async def leave(db: AsyncSession, class_id: UUID, user: User) -> LiveClassAttendance:
    item = await _get(db, class_id)
    row = (await db.execute(select(LiveClassAttendance).where(
        LiveClassAttendance.live_class_id == item.id, LiveClassAttendance.student_id == user.id
    ).with_for_update())).scalar_one_or_none()
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Attendance record not found")
    if row.left_at is None:
        end = min(utcnow(), row.last_seen_at)
        row.duration_seconds += max(0, int((end - row.joined_at).total_seconds()))
        row.left_at = end
        row.attendance_status = _duration_status(row.duration_seconds, item.duration_minutes)
        await db.commit()
        await db.refresh(row)
    return row


async def finish(db: AsyncSession, class_id: UUID, user: User, cancelled: bool = False) -> LiveClass:
    item = await _get(db, class_id, True)
    _assert_owner(item, user)
    target = "cancelled" if cancelled else "completed"
    if item.status == target:
        return item
    allowed = (item.status == "scheduled" and cancelled) or (item.status in ("scheduled", "live") and not cancelled)
    if not allowed:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Cannot transition {item.status} to {target}")
    now = utcnow()
    item.status = target
    item.ended_at = now if target == "completed" else None
    active = (await db.execute(select(LiveClassAttendance).where(
        LiveClassAttendance.live_class_id == item.id, LiveClassAttendance.left_at.is_(None)
    ).with_for_update())).scalars().all()
    for row in active:
        end = min(now, row.last_seen_at)
        row.duration_seconds += max(0, int((end - row.joined_at).total_seconds()))
        row.left_at = end
        row.attendance_status = _duration_status(row.duration_seconds, item.duration_minutes)
    await db.commit()
    logger.info("%s live_class=%s actor=%s", target, item.id, user.id)
    await notification_service.publish(target, item.id, item.course_id)
    return await _get(db, item.id)


async def attendance_list(db: AsyncSession, class_id: UUID, user: User) -> list[LiveClassAttendance]:
    item = await _get(db, class_id)
    _assert_owner(item, user)
    query = select(LiveClassAttendance).options(selectinload(LiveClassAttendance.student)).where(
        LiveClassAttendance.live_class_id == class_id
    ).order_by(LiveClassAttendance.joined_at)
    return list((await db.execute(query)).scalars().all())
