from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.models.exam import Exam
from app.models.course import Course
from app.models.user import User
from app.schemas.exam import ExamCreate, ExamUpdate
from app.repositories.exam_repo import ExamRepo


async def _get_course_or_404(db: AsyncSession, course_id: UUID) -> Course:
    course = await db.get(Course, course_id)
    if not course or course.is_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    return course


async def _require_exam_ownership(exam: Exam, user: User) -> None:
    """Faculty must own the exam's course; admins bypass."""
    if user.role == "admin":
        return
    if exam.course_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    # We need to check course ownership — done in callers via the course object


async def create_exam(db: AsyncSession, course_id: UUID, data: ExamCreate, user: User) -> Exam:
    course = await _get_course_or_404(db, course_id)

    if user.role not in ("faculty", "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only faculty/admin can create exams")

    if user.role == "faculty" and course.faculty_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not own this course")

    repo = ExamRepo(db)
    exam = Exam(
        course_id=course_id,
        title=data.title,
        duration_minutes=data.duration_minutes,
    )
    return await repo.create(exam)


async def get_exams_by_course(db: AsyncSession, course_id: UUID) -> list[Exam]:
    await _get_course_or_404(db, course_id)
    repo = ExamRepo(db)
    return await repo.get_by_course(course_id)


async def get_exam_by_id(db: AsyncSession, exam_id: UUID) -> Exam:
    repo = ExamRepo(db)
    exam = await repo.get_by_id(exam_id)
    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")
    return exam


async def update_exam(db: AsyncSession, exam_id: UUID, data: ExamUpdate, user: User) -> Exam:
    repo = ExamRepo(db)
    exam = await get_exam_by_id(db, exam_id)

    if user.role == "faculty":
        course = await db.get(Course, exam.course_id)
        if not course or course.faculty_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(exam, field, value)

    return await repo.save(exam)


async def delete_exam(db: AsyncSession, exam_id: UUID, user: User) -> None:
    repo = ExamRepo(db)
    exam = await get_exam_by_id(db, exam_id)

    if user.role == "faculty":
        course = await db.get(Course, exam.course_id)
        if not course or course.faculty_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    await repo.delete(exam)
