from sqlalchemy import Column, Enum as SQLEnum, String, DateTime, Boolean, func, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from app.db.base import Base

user_role_enum = SQLEnum("student", "faculty", "admin", name="user_role", create_type=True)


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=True)
    role = Column(user_role_enum, nullable=False)
    auth_provider = Column(String(20), nullable=False, default="local")
    google_id = Column(String(255), unique=True, nullable=True)
    apple_id = Column(String(255), unique=True, nullable=True)
    profile_image = Column(String(2048), nullable=True)
    email_verified = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    is_deleted = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    # Relationships — passive_deletes=True: let DB handle ON DELETE CASCADE/SET NULL
    courses = relationship(
        "Course",
        back_populates="faculty",
        foreign_keys="Course.faculty_id",
        passive_deletes=True,
    )
    enrollments = relationship("Enrollment", back_populates="user", passive_deletes=True)
    payments = relationship("Payment", back_populates="user", passive_deletes=True)
    attempts = relationship("Attempt", back_populates="user", passive_deletes=True)
    live_classes = relationship("LiveClass", back_populates="faculty", foreign_keys="LiveClass.faculty_id", passive_deletes=True)
    live_class_attendance = relationship("LiveClassAttendance", back_populates="student", passive_deletes=True)

    __table_args__ = (
        Index("idx_users_email", "email"),
    )
