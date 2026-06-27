import uuid as uuid_lib
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.models.payment import Payment
from app.models.user import User
from app.repositories.payment_repo import PaymentRepo
from app.repositories.enrollment_repo import EnrollmentRepo
from app.services.course_service import get_course_by_id


async def create_order(db: AsyncSession, course_id: UUID, user: User) -> Payment:
    """
    Mock Razorpay order creation.
    Generates a fake order_id and records a pending payment.
    """
    course = await get_course_by_id(db, course_id)

    if course.is_free or course.price == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This course is free — enroll directly via /enrollments/{course_id}",
        )

    # Check if already enrolled
    enroll_repo = EnrollmentRepo(db)
    if await enroll_repo.is_user_enrolled(user.id, course_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are already enrolled in this course",
        )

    # Mock Razorpay order ID
    fake_order_id = f"order_{uuid_lib.uuid4().hex[:16].upper()}"

    repo = PaymentRepo(db)
    payment = Payment(
        user_id=user.id,
        course_id=course_id,
        amount=float(course.price),
        razorpay_order_id=fake_order_id,
        status="pending",
    )
    return await repo.create(payment)


async def verify_payment(
    db: AsyncSession,
    razorpay_order_id: str,
    razorpay_payment_id: str,
    user: User,
) -> Payment:
    """
    Mock Razorpay verification.
    - Looks up the pending payment by order_id.
    - Marks it as success.
    - Auto-enrolls the student in the course.
    """
    repo = PaymentRepo(db)
    payment = await repo.get_by_order_id(razorpay_order_id)

    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment order not found")

    if payment.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your payment")

    if payment.status == "success":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payment already verified")

    # Mark payment successful
    payment.razorpay_payment_id = razorpay_payment_id
    payment.status = "success"
    await repo.save(payment)

    # Auto-enroll the student
    enroll_repo = EnrollmentRepo(db)
    already_enrolled = await enroll_repo.is_user_enrolled(user.id, payment.course_id)
    if not already_enrolled:
        enrollment = await enroll_repo.create_enrollment(user.id, payment.course_id)
        enrollment.payment_id = payment.id
        await db.commit()

    return payment


async def get_my_payments(db: AsyncSession, user: User) -> list[Payment]:
    repo = PaymentRepo(db)
    return await repo.get_by_user(user.id)
