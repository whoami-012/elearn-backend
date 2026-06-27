from fastapi import APIRouter, Depends
from app.schemas.lesson import YoutubeLessonResponse, YoutubeLessonCreate
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user, get_db
from app.services import youtube_service
from app.models.user import User
from typing import Optional
from app.api.deps import get_db, get_current_user_optional

router = APIRouter(prefix="/courses", tags=["Lessons"])

@router.post("/{course_id}/lessons/youtube", response_model=YoutubeLessonResponse)
async def create_youtube_lesson(
    course_id: UUID,
    data: YoutubeLessonCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    lesson = await youtube_service.create_youtube_lesson(
        db=db,
        course_id=course_id,
        current_user=current_user,
        data=data,
    )
    return YoutubeLessonResponse(
        id=lesson.id,
        course_id=lesson.course_id,
        title=lesson.title,
        video_id=lesson.youtube_video_id,
        is_preview=lesson.is_preview,
        order_index=lesson.order_index,
    )

@router.get("/{course_id}/lessons/youtube", response_model=list[YoutubeLessonResponse])
async def get_yt_lessons_by_course(
    course_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    lessons = await youtube_service.get_youtube_lessons_by_course(
        db, course_id, current_user
    )
    print(f"[DEBUG] Fetched {len(lessons)} YT lessons for course {course_id}. User: {current_user.email if current_user else 'Guest'}")
    return [
        YoutubeLessonResponse(
            id=lesson.id,
            course_id=lesson.course_id,
            title=lesson.title,
            video_id=lesson.youtube_video_id,
            is_preview=lesson.is_preview,
            order_index=lesson.order_index,
        )
        for lesson in lessons
    ]
