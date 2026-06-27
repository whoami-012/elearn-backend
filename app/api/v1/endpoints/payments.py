from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.db.dependencies import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.payment import PaymentOrderResponse, PaymentVerifyRequest, PaymentResponse
from app.services import payment_service

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post("/order/{course_id}", response_model=PaymentOrderResponse)
async def create_payment_order(
    course_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Initiate payment for a paid course.
    Returns a mock Razorpay order ID and amount.
    Student must send this order_id to /verify after completing payment.
    """
    payment = await payment_service.create_order(db, course_id, current_user)
    return PaymentOrderResponse(
        payment_id=payment.id,
        order_id=payment.razorpay_order_id,
        amount=float(payment.amount),
        currency="INR",
        course_id=payment.course_id,
        status=payment.status,
    )


@router.post("/verify", response_model=PaymentResponse)
async def verify_payment(
    data: PaymentVerifyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Verify payment and auto-enroll student.
    In production: validate Razorpay signature here.
    In this mock: simply marks the payment as success and enrolls the student.
    """
    payment = await payment_service.verify_payment(
        db,
        data.razorpay_order_id,
        data.razorpay_payment_id,
        current_user,
    )
    return payment


@router.get("/my", response_model=list[PaymentResponse])
async def my_payments(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get current user's payment history."""
    return await payment_service.get_my_payments(db, current_user)
