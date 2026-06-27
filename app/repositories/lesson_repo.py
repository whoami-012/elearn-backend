from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.models.lesson import Lesson

class LessonRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_youtube_lessons_by_course(self, course_id: UUID) -> list[Lesson]:
        result = await self.db.execute(
            select(Lesson).where(Lesson.course_id == course_id, Lesson.type == "video")
        )
        return result.scalars().all()
    
