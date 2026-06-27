from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Enum as SQLEnum, func, Index, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from app.db.base import Base

payment_status_enum = SQLEnum("pending", "success", "failed", name="payment_status", create_type=True)


class Payment(Base):
    __tablename__ = "payments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    razorpay_order_id = Column(String(255), nullable=False)
    razorpay_payment_id = Column(String(255), nullable=True)
    status = Column(payment_status_enum, nullable=False, default="pending")
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    # child → parent (NO cascade — never delete parent from child side)
    user = relationship("User", back_populates="payments", passive_deletes=True)
    course = relationship("Course", back_populates="payments", passive_deletes=True)
    # parent → child (one payment → one enrollment link)
    enrollment = relationship("Enrollment", back_populates="payment", uselist=False, passive_deletes=True)

    __table_args__ = (
        Index("idx_payments_user", "user_id"),
        Index("idx_payments_course", "course_id"),
    )
