from fastapi import HTTPException, status

from app.models.user import User
from app.repositories.enrollment_repo import EnrollmentRepo
from app.services.course_service import get_course_by_id

# create enrollment
async def enroll_user(db, course_id, current_user: User):
    repo = EnrollmentRepo(db)

    # Check if user is already enrolled
    if await repo.is_user_enrolled(current_user.id, course_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already enrolled in this course"
        )

    # check course exists
    course = await get_course_by_id(db, course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    # free course
    if course.price == 0:
        return await repo.create_enrollment(current_user.id, course_id)
    
    # paid course -> block
    raise HTTPException(
        status_code=status.HTTP_402_PAYMENT_REQUIRED,
        detail="Payment required"
    )


async def is_user_enrolled(db, user_id, course_id) -> bool:
    repo = EnrollmentRepo(db)
    return await repo.is_user_enrolled(user_id, course_id)

async def check_access(db, course_id, current_user):
    repo = EnrollmentRepo(db)
    
    if not current_user:
        return False

    if current_user.role == "faculty":
        return True

    return await is_user_enrolled(db, current_user.id, course_id)

# enroll after payment
async def enroll_after_payment(db, user_id, course_id, payment_id):
    repo = EnrollmentRepo(db)

    try:
        enrollment = await repo.create_enrollment(user_id, course_id)
    except HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is already enrolled in this course"):
        return enrollment
    
    # attach payment safely
    enrollment.payment_id = payment_id
    await db.commit()
    await db.refresh(enrollment)

    return enrollment
