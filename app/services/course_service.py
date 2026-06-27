from sqlalchemy.ext.asyncio import AsyncSession
from app.models.course import Course
from app.models.user import User
from app.schemas.courses import CourseCreate, CourseUpdate
from fastapi import HTTPException, status


# 🔹 Create Course
async def create_course(db: AsyncSession, data: CourseCreate, user: User):
    # Fix: renamed param from 'course' to 'data' to avoid shadowing the ORM instance
    new_course = Course(
        title=data.title,
        description=data.description,
        price=data.price,
        is_free=data.is_free,
        thumbnail_url=data.thumbnail_url,
        faculty_id=user.id,
    )

    db.add(new_course)
    await db.commit()
    await db.refresh(new_course)

    return new_course


# 🔹 Get all courses
async def get_courses(db: AsyncSession):
    from sqlalchemy import select
    result = await db.execute(select(Course).where(Course.is_deleted == False))
    return result.scalars().all()


# 🔹 Get course by ID
async def get_course_by_id(db: AsyncSession, course_id):
    from sqlalchemy import select
    result = await db.execute(
        select(Course).where(Course.id == course_id, Course.is_deleted == False)
    )
    course = result.scalar_one_or_none()

    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        )

    return course


# 🔹 Update Course (PATCH — partial)
async def update_course(
    db: AsyncSession,
    course_id,
    data: CourseUpdate,
    user: User,
) -> Course:
    course = await get_course_by_id(db, course_id)

    # Only the faculty who owns the course or an admin can edit it
    if user.role != "admin" and course.faculty_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to edit this course",
        )

    # Apply only the fields that were provided
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(course, field, value)

    await db.commit()
    await db.refresh(course)
    return course


# 🔹 Delete Course (soft delete)
async def delete_course(db: AsyncSession, course_id, user: User) -> None:
    course = await get_course_by_id(db, course_id)

    if user.role != "admin" and course.faculty_id != user.id:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete this course",
        )

    course.is_deleted = True
    await db.commit()