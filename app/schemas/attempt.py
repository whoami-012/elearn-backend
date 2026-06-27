from pydantic import BaseModel, Field
from typing import Dict
from datetime import datetime
from uuid import UUID


class AttemptCreate(BaseModel):
    """
    answers: mapping of question_id (str) → chosen option key (e.g. "A").
    Example: {"<uuid>": "A", "<uuid2>": "C"}
    """
    answers: Dict[str, str] = Field(..., description="question_id → chosen option key")


class AttemptResponse(BaseModel):
    id: UUID
    exam_id: UUID
    user_id: UUID
    answers: Dict[str, str]
    score: int
    total: int
    percentage: float
    attempt_number: int
    submitted_at: datetime

    class Config:
        from_attributes = True
