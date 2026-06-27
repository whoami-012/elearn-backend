from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.models.question import Question
from app.models.course import Course
from app.models.user import User
from app.schemas.question import QuestionCreate, QuestionUpdate
from app.repositories.question_repo import QuestionRepo
from app.services.exam_service import get_exam_by_id


async def _require_faculty_ownership(db: AsyncSession, exam_id: UUID, user: User) -> None:
    """Validate faculty owns the course that contains this exam."""
    if user.role == "admin":
        return
    exam = await get_exam_by_id(db, exam_id)
    course = await db.get(Course, exam.course_id)
    if not course or course.faculty_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")


async def add_question(db: AsyncSession, exam_id: UUID, data: QuestionCreate, user: User) -> Question:
    if user.role not in ("faculty", "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only faculty/admin can add questions")

    await _require_faculty_ownership(db, exam_id, user)

    # Validate correct_answer is one of the option keys
    if data.correct_answer not in data.options:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"correct_answer '{data.correct_answer}' must be a key in options {list(data.options.keys())}"
        )

    repo = QuestionRepo(db)
    question = Question(
        exam_id=exam_id,
        question_text=data.question_text,
        options=data.options,
        correct_answer=data.correct_answer,
    )
    return await repo.create(question)


async def get_questions_by_exam(db: AsyncSession, exam_id: UUID) -> list[Question]:
    # Ensure exam exists
    await get_exam_by_id(db, exam_id)
    repo = QuestionRepo(db)
    return await repo.get_by_exam(exam_id)


async def get_question_by_id(db: AsyncSession, question_id: UUID) -> Question:
    repo = QuestionRepo(db)
    q = await repo.get_by_id(question_id)
    if not q:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
    return q


async def update_question(db: AsyncSession, question_id: UUID, data: QuestionUpdate, user: User) -> Question:
    repo = QuestionRepo(db)
    question = await get_question_by_id(db, question_id)

    await _require_faculty_ownership(db, question.exam_id, user)

    update_data = data.model_dump(exclude_unset=True)

    # If updating options or correct_answer, validate consistency
    new_options = update_data.get("options", question.options)
    new_answer = update_data.get("correct_answer", question.correct_answer)
    if new_answer not in new_options:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"correct_answer '{new_answer}' must be a key in options {list(new_options.keys())}"
        )

    for field, value in update_data.items():
        setattr(question, field, value)

    return await repo.save(question)


async def delete_question(db: AsyncSession, question_id: UUID, user: User) -> None:
    repo = QuestionRepo(db)
    question = await get_question_by_id(db, question_id)

    await _require_faculty_ownership(db, question.exam_id, user)

    await repo.delete(question)
