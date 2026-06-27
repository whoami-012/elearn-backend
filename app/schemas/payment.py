from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID


class PaymentOrderResponse(BaseModel):
    """Returned when a student initiates payment for a paid course."""
    payment_id: UUID
    order_id: str       # mock Razorpay order ID
    amount: float
    currency: str = "INR"
    course_id: UUID
    status: str


class PaymentVerifyRequest(BaseModel):
    """Student sends this after completing mock payment flow."""
    razorpay_order_id: str
    razorpay_payment_id: str


class PaymentResponse(BaseModel):
    id: UUID
    user_id: UUID
    course_id: UUID
    amount: float
    razorpay_order_id: str
    razorpay_payment_id: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
