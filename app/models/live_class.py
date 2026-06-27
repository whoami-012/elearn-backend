import uuid

from sqlalchemy import BigInteger, CheckConstraint, Column, DateTime, Enum as SQLEnum, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base

live_class_status_enum = SQLEnum("scheduled", "live", "completed", "cancelled", name="live_class_status")
attendance_status_enum = SQLEnum("present", "partial", "absent", name="attendance_status")


class LiveClass(Base):
    __tablename__ = "live_classes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    faculty_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    agora_channel_name = Column(String(128), nullable=False, unique=True)
    scheduled_start_time = Column(DateTime(timezone=True), nullable=False)
    scheduled_end_time = Column(DateTime(timezone=True), nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    status = Column(live_class_status_enum, nullable=False, default="scheduled")
    started_at = Column(DateTime(timezone=True))
    ended_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    course = relationship("Course", back_populates="live_classes")
    faculty = relationship("User", back_populates="live_classes", foreign_keys=[faculty_id])
    attendance = relationship("LiveClassAttendance", back_populates="live_class", cascade="all, delete-orphan", passive_deletes=True)

    __table_args__ = (
        CheckConstraint("scheduled_end_time > scheduled_start_time", name="ck_live_class_time_order"),
        CheckConstraint("duration_minutes > 0", name="ck_live_class_duration"),
        Index("idx_live_classes_course_status", "course_id", "status"),
        Index("idx_live_classes_faculty", "faculty_id"),
    )


class LiveClassAttendance(Base):
    __tablename__ = "live_class_attendance"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    live_class_id = Column(UUID(as_uuid=True), ForeignKey("live_classes.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    agora_uid = Column(BigInteger, nullable=False)
    joined_at = Column(DateTime(timezone=True), nullable=False)
    last_seen_at = Column(DateTime(timezone=True), nullable=False)
    left_at = Column(DateTime(timezone=True))
    duration_seconds = Column(Integer, nullable=False, default=0)
    attendance_status = Column(attendance_status_enum, nullable=False, default="absent")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    live_class = relationship("LiveClass", back_populates="attendance")
    student = relationship("User", back_populates="live_class_attendance")

    __table_args__ = (
        UniqueConstraint("live_class_id", "student_id", name="uq_attendance_student_class"),
        UniqueConstraint("live_class_id", "agora_uid", name="uq_attendance_channel_uid"),
        CheckConstraint("agora_uid > 0 AND agora_uid <= 4294967295", name="ck_agora_uid_range"),
        Index("idx_attendance_class", "live_class_id"),
    )
