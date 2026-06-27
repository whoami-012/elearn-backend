from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from app.models.exam import Exam


class ExamRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, exam: Exam) -> Exam:
        self.db.add(exam)
        await self.db.commit()
        await self.db.refresh(exam)
        return exam

    async def get_by_id(self, exam_id: UUID) -> Exam | None:
        result = await self.db.execute(
            select(Exam).where(Exam.id == exam_id)
        )
        return result.scalar_one_or_none()

    async def get_by_course(self, course_id: UUID) -> list[Exam]:
        result = await self.db.execute(
            select(Exam).where(Exam.course_id == course_id).order_by(Exam.created_at)
        )
        return list(result.scalars().all())

    async def delete(self, exam: Exam) -> None:
        await self.db.delete(exam)
        await self.db.commit()

    async def save(self, exam: Exam) -> Exam:
        await self.db.commit()
        await self.db.refresh(exam)
        return exam
