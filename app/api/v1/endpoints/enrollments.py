from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.enrollment import EnrollmentResponse
from app.services.enrollment_service import enroll_user, is_user_enrolled
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

router = APIRouter(prefix="/enrollments", tags=["Enrollments"])


@router.post("/{course_id}", response_model=EnrollmentResponse)
async def create_enrollment(
    course_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await enroll_user(db, course_id, current_user)

# check enrollment
@router.get("/check/{course_id}")
async def check_enrollment(
    course_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # faculty/admin always have access
    if current_user.role == "faculty":
        return {"is_enrolled": True}

    is_enrolled = await is_user_enrolled(
        db,
        current_user.id,
        course_id
    )

    return {"is_enrolled": is_enrolled}