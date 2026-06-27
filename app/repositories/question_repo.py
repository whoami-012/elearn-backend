from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from app.models.question import Question


class QuestionRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, question: Question) -> Question:
        self.db.add(question)
        await self.db.commit()
        await self.db.refresh(question)
        return question

    async def get_by_id(self, question_id: UUID) -> Question | None:
        result = await self.db.execute(
            select(Question).where(Question.id == question_id)
        )
        return result.scalar_one_or_none()

    async def get_by_exam(self, exam_id: UUID) -> list[Question]:
        result = await self.db.execute(
            select(Question)
            .where(Question.exam_id == exam_id)
            .order_by(Question.created_at)
        )
        return list(result.scalars().all())

    async def delete(self, question: Question) -> None:
        await self.db.delete(question)
        await self.db.commit()

    async def save(self, question: Question) -> Question:
        await self.db.commit()
        await self.db.refresh(question)
        return question
