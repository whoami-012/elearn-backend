from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import Optional

from app.db.dependencies import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.attempt import AttemptCreate, AttemptResponse
from app.services import attempt_service

router = APIRouter(tags=["Attempts"])


@router.post(
    "/exams/{exam_id}/attempt",
    status_code=status.HTTP_201_CREATED,
)
async def submit_attempt(
    exam_id: UUID,
    data: AttemptCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit answers for an exam. Returns score, total, and percentage."""
    return await attempt_service.submit_attempt(db, exam_id, data.answers, current_user)


@router.get("/exams/{exam_id}/my-attempt")
async def get_my_attempts(
    exam_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get current user's own attempts for an exam."""
    return await attempt_service.get_my_attempts(db, exam_id, current_user)


@router.get("/exams/{exam_id}/attempts")
async def get_all_attempts(
    exam_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Faculty/admin: get all student attempts for an exam."""
    return await attempt_service.get_all_attempts(db, exam_id, current_user)
