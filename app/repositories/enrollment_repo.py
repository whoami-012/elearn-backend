from sqlalchemy import select
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.enrollment import Enrollment
from typing import Optional
from uuid import UUID

from sqlalchemy.exc import IntegrityError

class EnrollmentRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def is_user_enrolled(self, user_id, course_id) -> bool:
        result = await self.db.execute(
            select(Enrollment).where(
                Enrollment.user_id == user_id,
                Enrollment.course_id == course_id,
                Enrollment.is_active == True
            )
        )
        return result.scalar_one_or_none() is not None

    async def create_enrollment(self, user_id, course_id):
        enrollment = Enrollment(
            user_id=user_id,
            course_id=course_id
        )

        self.db.add(enrollment)

        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise HTTPException(
                status_code=400,
                detail="User is already enrolled in this course"
            )

        await self.db.refresh(enrollment)
        return enrollment