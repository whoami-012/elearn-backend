from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from app.models.attempt import Attempt


class AttemptRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, attempt: Attempt) -> Attempt:
        self.db.add(attempt)
        await self.db.commit()
        await self.db.refresh(attempt)
        return attempt

    async def get_by_id(self, attempt_id: UUID) -> Attempt | None:
        result = await self.db.execute(
            select(Attempt).where(Attempt.id == attempt_id)
        )
        return result.scalar_one_or_none()

    async def get_by_exam_and_user(self, exam_id: UUID, user_id: UUID) -> list[Attempt]:
        result = await self.db.execute(
            select(Attempt)
            .where(Attempt.exam_id == exam_id, Attempt.user_id == user_id)
            .order_by(Attempt.submitted_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_exam(self, exam_id: UUID) -> list[Attempt]:
        result = await self.db.execute(
            select(Attempt)
            .where(Attempt.exam_id == exam_id)
            .order_by(Attempt.submitted_at.desc())
        )
        return list(result.scalars().all())

    async def count_by_exam_and_user(self, exam_id: UUID, user_id: UUID) -> int:
        result = await self.db.execute(
            select(Attempt)
            .where(Attempt.exam_id == exam_id, Attempt.user_id == user_id)
        )
        return len(result.scalars().all())
