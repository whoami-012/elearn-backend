from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID


class ExamCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    duration_minutes: int = Field(..., gt=0, le=480)


class ExamUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=255)
    duration_minutes: Optional[int] = Field(None, gt=0, le=480)


class ExamResponse(BaseModel):
    id: UUID
    course_id: UUID
    title: str
    duration_minutes: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
