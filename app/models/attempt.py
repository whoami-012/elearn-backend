from sqlalchemy import Column, DateTime, Integer, ForeignKey, func, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
from app.db.base import Base


class Attempt(Base):
    __tablename__ = "attempts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    exam_id = Column(UUID(as_uuid=True), ForeignKey("exams.id", ondelete="CASCADE"), nullable=False)
    answers = Column(JSONB, nullable=False)      # e.g. {"<question_id>": "A", ...}
    attempt_number = Column(Integer, nullable=False, default=1)
    score = Column(Integer, nullable=False)
    submitted_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    # child → parent (NO cascade)
    user = relationship("User", back_populates="attempts", passive_deletes=True)
    exam = relationship("Exam", back_populates="attempts", passive_deletes=True)

    __table_args__ = (
        Index("idx_attempts_user", "user_id"),
        Index("idx_attempts_exam", "exam_id"),
    )
