from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID

class NoteCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    content: Optional[str] = Field(None, min_length=10)
    is_free: bool = False

class NoteUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=200)
    content: Optional[str] = Field(None, min_length=10)
    is_free: Optional[bool] = None

class NoteResponse(BaseModel):
    id: UUID
    title: str
    content: Optional[str]
    file_url: Optional[str]
    file_type: Optional[str]
    course_id: UUID
    uploaded_by: UUID
    is_free: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True