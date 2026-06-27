from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.models.attempt import Attempt
from app.models.user import User
from app.repositories.attempt_repo import AttemptRepo
from app.repositories.question_repo import QuestionRepo
from app.services.exam_service import get_exam_by_id
from app.services.enrollment_service import is_user_enrolled


async def submit_attempt(
    db: AsyncSession,
    exam_id: UUID,
    answers: dict[str, str],
    user: User,
) -> dict:
    """
    Auto-grade an exam attempt.
    - Students must be enrolled in the course.
    - Faculty/admin can attempt freely (for testing).
    - Returns scored attempt with total, score, percentage.
    """
    exam = await get_exam_by_id(db, exam_id)

    # Enrollment check for students
    if user.role == "student":
        enrolled = await is_user_enrolled(db, user.id, exam.course_id)
        if not enrolled:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You must be enrolled in this course to take the exam",
            )

    # Load all questions for this exam
    q_repo = QuestionRepo(db)
    questions = await q_repo.get_by_exam(exam_id)

    if not questions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This exam has no questions yet",
        )

    # Build a map: question_id (str) → correct_answer
    correct_map = {str(q.id): q.correct_answer for q in questions}

    # Score the answers
    score = 0
    for q_id, chosen in answers.items():
        if correct_map.get(q_id) == chosen:
            score += 1
    total = len(questions)
    percentage = round((score / total) * 100, 2) if total > 0 else 0.0

    # Determine attempt number
    a_repo = AttemptRepo(db)
    attempt_number = await a_repo.count_by_exam_and_user(exam_id, user.id) + 1

    attempt = Attempt(
        user_id=user.id,
        exam_id=exam_id,
        answers=answers,
        score=score,
        attempt_number=attempt_number,
    )
    saved = await a_repo.create(attempt)

    # Return enriched response (total + percentage not stored in DB)
    return {
        "id": saved.id,
        "exam_id": saved.exam_id,
        "user_id": saved.user_id,
        "answers": saved.answers,
        "score": saved.score,
        "total": total,
        "percentage": percentage,
        "attempt_number": saved.attempt_number,
        "submitted_at": saved.submitted_at,
    }


async def get_my_attempts(db: AsyncSession, exam_id: UUID, user: User) -> list[dict]:
    """Student fetches their own attempts for an exam."""
    await get_exam_by_id(db, exam_id)
    a_repo = AttemptRepo(db)
    q_repo = QuestionRepo(db)

    attempts = await a_repo.get_by_exam_and_user(exam_id, user.id)
    questions = await q_repo.get_by_exam(exam_id)
    total = len(questions)

    return [_enrich(a, total) for a in attempts]


async def get_all_attempts(db: AsyncSession, exam_id: UUID, user: User) -> list[dict]:
    """Faculty/admin fetches all student attempts for an exam."""
    if user.role not in ("faculty", "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    await get_exam_by_id(db, exam_id)
    a_repo = AttemptRepo(db)
    q_repo = QuestionRepo(db)

    attempts = await a_repo.get_by_exam(exam_id)
    questions = await q_repo.get_by_exam(exam_id)
    total = len(questions)

    return [_enrich(a, total) for a in attempts]


def _enrich(attempt: Attempt, total: int) -> dict:
    """Add computed total and percentage to an attempt."""
    percentage = round((attempt.score / total) * 100, 2) if total > 0 else 0.0
    return {
        "id": attempt.id,
        "exam_id": attempt.exam_id,
        "user_id": attempt.user_id,
        "answers": attempt.answers,
        "score": attempt.score,
        "total": total,
        "percentage": percentage,
        "attempt_number": attempt.attempt_number,
        "submitted_at": attempt.submitted_at,
    }
