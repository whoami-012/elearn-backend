from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.course import Course
from typing import Optional
from uuid import UUID


class CourseRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_course(self, course: Course) -> Course:
        self.db.add(course)
        await self.db.commit()
        await self.db.refresh(course)
        return course

    async def get_course_by_id(self, course_id: UUID) -> Optional[Course]:
        result = await self.db.execute(
            select(Course).where(
                Course.id == course_id,
                Course.is_deleted == False
            )
        )
        return result.scalar_one_or_none()

    async def get_all_courses(self) -> list[Course]:
        result = await self.db.execute(
            select(Course).where(Course.is_deleted == False)
        )
        return result.scalars().all()

    async def update_course(self, course: Course) -> Course:
        await self.db.commit()
        await self.db.refresh(course)
        return course

    async def delete_course(self, course: Course) -> Course:
        course.is_deleted = True
        await self.db.commit()
        await self.db.refresh(course)
        return course