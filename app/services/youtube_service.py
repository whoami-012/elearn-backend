import re
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import UserRole, require_course_faculty_or_admin, require_faculty_or_admin, user_role
from app.models.course import Course
from app.models.lesson import Lesson
from app.models.user import User
from app.schemas.lesson import YoutubeLessonCreate, YoutubeLessonUpdate
from app.services.audit_service import log_admin_action
from app.services.enrollment_service import is_user_enrolled

YOUTUBE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


def normalize_youtube_video_id(value: str) -> str:
    raw = value.strip()
    patterns = [
        r"(?:v=|\/)([A-Za-z0-9_-]{11})(?:[?&].*)?$",
        r"youtu\.be\/([A-Za-z0-9_-]{11})(?:[?&].*)?$",
    ]
    for pattern in patterns:
        match = re.search(pattern, raw)
        candidate = match.group(1) if match else raw
        if YOUTUBE_ID_RE.fullmatch(candidate):
            return candidate
    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid YouTube video identifier")


async def _get_course_or_404(db: AsyncSession, course_id: UUID) -> Course:
    course = await db.get(Course, course_id)
    if not course or course.is_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    return course


async def _get_lesson_or_404(db: AsyncSession, lesson_id: UUID) -> Lesson:
    result = await db.execute(select(Lesson).where(Lesson.id == lesson_id, Lesson.type == "video"))
    lesson = result.scalar_one_or_none()
    if not lesson:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found")
    return lesson


async def create_youtube_lesson(
    db: AsyncSession,
    course_id: UUID,
    data: YoutubeLessonCreate,
    current_user: User,
):
    require_faculty_or_admin(current_user)
    course = await _get_course_or_404(db, course_id)
    require_course_faculty_or_admin(course, current_user)
    lesson = Lesson(
        title=data.title,
        type="video",
        course_id=course_id,
        youtube_video_id=normalize_youtube_video_id(data.video_id),
        is_preview=data.is_preview,
        order_index=data.order_index,
    )
    db.add(lesson)
    if user_role(current_user) == UserRole.ADMIN:
        await log_admin_action(
            db,
            actor=current_user,
            action="lesson.create",
            resource_type="lesson",
            resource_id=str(lesson.id),
            new_values={"course_id": str(course_id), "title": lesson.title, "order_index": lesson.order_index},
        )
    await db.commit()
    await db.refresh(lesson)
    return lesson


async def update_youtube_lesson(
    db: AsyncSession,
    lesson_id: UUID,
    data: YoutubeLessonUpdate,
    current_user: User,
) -> Lesson:
    require_faculty_or_admin(current_user)
    lesson = await _get_lesson_or_404(db, lesson_id)
    course = await _get_course_or_404(db, lesson.course_id)
    require_course_faculty_or_admin(course, current_user)
    old_values = {"title": lesson.title, "video_id": lesson.youtube_video_id, "order_index": lesson.order_index, "is_preview": lesson.is_preview}

    update_data = data.model_dump(exclude_unset=True)
    if "video_id" in update_data:
        update_data["video_id"] = normalize_youtube_video_id(update_data["video_id"])
    for field, value in update_data.items():
        if field == "video_id":
            lesson.youtube_video_id = value
        else:
            setattr(lesson, field, value)

    if user_role(current_user) == UserRole.ADMIN:
        await log_admin_action(
            db,
            actor=current_user,
            action="lesson.update",
            resource_type="lesson",
            resource_id=str(lesson.id),
            old_values=old_values,
            new_values={"title": lesson.title, "video_id": lesson.youtube_video_id, "order_index": lesson.order_index, "is_preview": lesson.is_preview},
        )
    await db.commit()
    await db.refresh(lesson)
    return lesson


async def delete_youtube_lesson(db: AsyncSession, lesson_id: UUID, current_user: User) -> None:
    require_faculty_or_admin(current_user)
    lesson = await _get_lesson_or_404(db, lesson_id)
    course = await _get_course_or_404(db, lesson.course_id)
    require_course_faculty_or_admin(course, current_user)
    if user_role(current_user) == UserRole.ADMIN:
        await log_admin_action(
            db,
            actor=current_user,
            action="lesson.delete",
            resource_type="lesson",
            resource_id=str(lesson.id),
            old_values={"title": lesson.title, "course_id": str(lesson.course_id)},
        )
    await db.delete(lesson)
    await db.commit()


async def get_youtube_lessons_by_course(
    db: AsyncSession,
    course_id: UUID,
    current_user: Optional[User],
) -> list[Lesson]:
    result = await db.execute(select(Lesson).where(Lesson.course_id == course_id, Lesson.type == "video").order_by(Lesson.order_index))
    youtube_lessons = list(result.scalars().all())

    if not current_user:
        return [lesson for lesson in youtube_lessons if lesson.is_preview]

    if user_role(current_user) == UserRole.ADMIN:
        return youtube_lessons

    course = await _get_course_or_404(db, course_id)
    if user_role(current_user) in {UserRole.FACULTY, UserRole.TEACHER} and course.faculty_id == current_user.id:
        return youtube_lessons

    if await is_user_enrolled(db, current_user.id, course_id):
        return youtube_lessons
    return [lesson for lesson in youtube_lessons if lesson.is_preview]
