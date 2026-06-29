from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.db.dependencies import get_db
from app.schemas.courses import CourseCreate, CourseResponse, CourseUpdate, FacultyAssignmentUpdate
from app.services.course_service import (
    create_course,
    get_courses,
    get_course_by_id,
    update_course,
    delete_course,
    assign_course_faculty,
)
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/courses", tags=["Courses"])


# 🔹 List all courses (public)
@router.get("", response_model=list[CourseResponse])
async def list_courses(db: AsyncSession = Depends(get_db)):
    return await get_courses(db)


# 🔹 Get course by ID (public)
@router.get("/{course_id}", response_model=CourseResponse)
async def get_course(
    course_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    return await get_course_by_id(db, course_id)


# 🔹 Create course (faculty only)
@router.post("", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
async def create(
    data: CourseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ("faculty", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only faculty or admin can create courses",
        )
    return await create_course(db, data, current_user)


# 🔹 Update course (faculty who owns it or admin)
@router.patch("/{course_id}", response_model=CourseResponse)
async def edit_course(
    course_id: UUID,
    data: CourseUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ("faculty", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only faculty or admin can edit courses",
        )
    return await update_course(db, course_id, data, current_user)


# 🔹 Delete course (faculty who owns it or admin) — soft delete
@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_course(
    course_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ("faculty", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only faculty or admin can delete courses",
    )
    await delete_course(db, course_id, current_user)


@router.patch("/{course_id}/assign-faculty", response_model=CourseResponse)
async def assign_faculty(
    course_id: UUID,
    data: FacultyAssignmentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await assign_course_faculty(db, course_id, data.faculty_id, current_user)


@router.delete("/{course_id}/faculty-assignment", response_model=CourseResponse)
async def remove_faculty_assignment(
    course_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await assign_course_faculty(db, course_id, None, current_user)
