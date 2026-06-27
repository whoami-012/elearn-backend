from pydantic import BaseModel, Field
from typing import Optional, Dict
from datetime import datetime
from uuid import UUID


class QuestionCreate(BaseModel):
    """
    options must be a dict with exactly 4 keys A/B/C/D.
    correct_answer must be one of those keys.
    Example: {"A": "Paris", "B": "London", "C": "Berlin", "D": "Rome"}
    """
    question_text: str = Field(..., min_length=5)
    options: Dict[str, str] = Field(..., description='e.g. {"A":"Yes","B":"No","C":"Maybe","D":"Never"}')
    correct_answer: str = Field(..., max_length=10)


class QuestionUpdate(BaseModel):
    question_text: Optional[str] = Field(None, min_length=5)
    options: Optional[Dict[str, str]] = None
    correct_answer: Optional[str] = Field(None, max_length=10)


class QuestionResponse(BaseModel):
    id: UUID
    exam_id: UUID
    question_text: str
    options: Dict[str, str]
    correct_answer: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class QuestionResponseHidden(BaseModel):
    """Same as QuestionResponse but hides correct_answer (shown to students during exam)."""
    id: UUID
    exam_id: UUID
    question_text: str
    options: Dict[str, str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
