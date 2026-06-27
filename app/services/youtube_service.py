from sqlalchemy.ext.asyncio import AsyncSession
from app.models.lesson import Lesson
from app.models.user import User
from app.models.course import Course
from fastapi import HTTPException
from app.schemas.lesson import YoutubeLessonCreate
from app.repositories.lesson_repo import LessonRepo
from app.services.enrollment_service import is_user_enrolled
from typing import Optional
from uuid import UUID

async def create_youtube_lesson(
    db: AsyncSession,
    course_id: UUID,
    data: YoutubeLessonCreate,
    current_user: User,
):
    # validate course exists
    course = await db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # ownership check
    if course.faculty_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    lesson = Lesson(
        title=data.title,
        type="video",
        course_id=course_id,
        youtube_video_id=data.video_id,
        is_preview=data.is_preview,
        order_index=data.order_index,
    )
    db.add(lesson)
    await db.commit()
    await db.refresh(lesson)

    return lesson

async def get_youtube_lessons_by_course(
        db: AsyncSession,
        course_id: UUID,
        current_user: Optional[User],
) -> list[Lesson]:
    
    repo = LessonRepo(db)
    youtube_lessons = await repo.get_youtube_lessons_by_course(course_id)

    #if no user (guest) -> free lessons only
    if not current_user:
        return [lesson for lesson in youtube_lessons if lesson.is_preview]
    
    # faculty full access
    if current_user.role == "admin":
        return youtube_lessons

    if current_user.role == "faculty":
        course = await db.get(Course, course_id)
        if course and course.faculty_id == current_user.id:
            return youtube_lessons

    # student -> check enrollment
    if await is_user_enrolled(db, current_user.id, course_id):
        return youtube_lessons
    
    # Not enrolled -> only free
    return [lesson for lesson in youtube_lessons if lesson.is_preview]
