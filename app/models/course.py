from sqlalchemy import Column, String, Text, DateTime, Boolean, Numeric, ForeignKey, func, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from app.db.base import Base


class Course(Base):
    __tablename__ = "courses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Numeric(10, 2), nullable=False, default=0)
    is_free = Column(Boolean, nullable=False, default=False)
    # nullable=True because ON DELETE SET NULL — course survives if faculty is deleted
    faculty_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    thumbnail_url = Column(String(255), nullable=True)
    is_deleted = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    # parent → passive (SET NULL handled by DB)
    faculty = relationship("User", back_populates="courses", foreign_keys=[faculty_id], passive_deletes=True)
    # parent → children (cascade ORM + DB)
    enrollments = relationship("Enrollment", back_populates="course", cascade="all, delete-orphan", passive_deletes=True)
    payments = relationship("Payment", back_populates="course", cascade="all, delete-orphan", passive_deletes=True)
    lessons = relationship("Lesson", back_populates="course", cascade="all, delete-orphan", passive_deletes=True)
    exams = relationship("Exam", back_populates="course", cascade="all, delete-orphan", passive_deletes=True)
    notes = relationship("Note", back_populates="course", cascade="all, delete-orphan", passive_deletes=True)
    live_classes = relationship("LiveClass", back_populates="course", cascade="all, delete-orphan", passive_deletes=True)

    __table_args__ = (
        Index("idx_courses_faculty", "faculty_id"),
    )
