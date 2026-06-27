from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.note import Note
from uuid import UUID

class NoteRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_note_by_course(self, course_id: UUID) -> list[Note]:
        result = await self.db.execute(
            select(Note).where(Note.course_id == course_id)
        )
        return result.scalars().all()

    async def get_note_by_id(self, note_id: UUID) -> Note:
        result = await self.db.execute(
            select(Note).where(Note.id == note_id)
        )
        return result.scalar_one_or_none()