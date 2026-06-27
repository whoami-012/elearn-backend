from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import Optional

from app.db.dependencies import get_db
from app.api.deps import get_current_user, get_current_user_optional
from app.models.user import User
from app.schemas.exam import ExamCreate, ExamUpdate, ExamResponse
from app.schemas.question import QuestionCreate, QuestionUpdate, QuestionResponse, QuestionResponseHidden
from app.services import exam_service, question_service
from app.services.enrollment_service import is_user_enrolled

router = APIRouter(tags=["Exams & Questions"])


# ─────────────────────────────────────────────────────────────────────────────
#  EXAMS
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/courses/{course_id}/exams",
    response_model=ExamResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_exam(
    course_id: UUID,
    data: ExamCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await exam_service.create_exam(db, course_id, data, current_user)


@router.get("/courses/{course_id}/exams", response_model=list[ExamResponse])
async def list_exams(
    course_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    return await exam_service.get_exams_by_course(db, course_id)


@router.get("/exams/{exam_id}", response_model=ExamResponse)
async def get_exam(
    exam_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    return await exam_service.get_exam_by_id(db, exam_id)


@router.patch("/exams/{exam_id}", response_model=ExamResponse)
async def update_exam(
    exam_id: UUID,
    data: ExamUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await exam_service.update_exam(db, exam_id, data, current_user)


@router.delete("/exams/{exam_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_exam(
    exam_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await exam_service.delete_exam(db, exam_id, current_user)


# ─────────────────────────────────────────────────────────────────────────────
#  QUESTIONS
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/exams/{exam_id}/questions",
    response_model=QuestionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_question(
    exam_id: UUID,
    data: QuestionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await question_service.add_question(db, exam_id, data, current_user)


@router.get("/exams/{exam_id}/questions")
async def get_questions(
    exam_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Faculty/admin → full response with correct_answer.
    Students & guests → hidden response without correct_answer.
    """
    questions = await question_service.get_questions_by_exam(db, exam_id)
    is_privileged = current_user and current_user.role in ("faculty", "admin")

    if is_privileged:
        return [QuestionResponse.model_validate(q) for q in questions]
    return [QuestionResponseHidden.model_validate(q) for q in questions]


@router.patch("/questions/{question_id}", response_model=QuestionResponse)
async def update_question(
    question_id: UUID,
    data: QuestionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await question_service.update_question(db, question_id, data, current_user)


@router.delete("/questions/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_question(
    question_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await question_service.delete_question(db, question_id, current_user)
