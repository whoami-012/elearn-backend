from sqlalchemy import Column, DateTime, Boolean, ForeignKey, func, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from app.db.base import Base


class Enrollment(Base):
    __tablename__ = "enrollments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    # SET NULL: enrollment record kept even if payment is deleted
    payment_id = Column(UUID(as_uuid=True), ForeignKey("payments.id", ondelete="SET NULL"), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    # child → parent (NO cascade — never delete parent from child side)
    user = relationship("User", back_populates="enrollments", passive_deletes=True)
    course = relationship("Course", back_populates="enrollments", passive_deletes=True)
    payment = relationship("Payment", back_populates="enrollment", passive_deletes=True)

    __table_args__ = (
        UniqueConstraint("user_id", "course_id", name="unique_enrollment"),
        Index("idx_enrollment_user_course", "user_id", "course_id"),
    )