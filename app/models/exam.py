from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, func, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from app.db.base import Base


class Exam(Base):
    __tablename__ = "exams"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    # child → parent (NO cascade)
    course = relationship("Course", back_populates="exams", passive_deletes=True)
    # parent → children
    questions = relationship("Question", back_populates="exam", cascade="all, delete-orphan", passive_deletes=True)
    attempts = relationship("Attempt", back_populates="exam", cascade="all, delete-orphan", passive_deletes=True)

    __table_args__ = (
        Index("idx_exams_course", "course_id"),
    )