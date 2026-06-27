from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID


class CourseCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    description: str = Field(..., min_length=10)
    price: float = Field(..., ge=0)
    is_free: bool = False
    thumbnail_url: Optional[str] = None


class CourseUpdate(BaseModel):
    """All fields optional — only provided fields are updated (PATCH semantics)."""
    title: Optional[str]         = Field(None, min_length=3, max_length=200)
    description: Optional[str]   = Field(None, min_length=10)
    price: Optional[float]       = Field(None, ge=0)
    is_free: Optional[bool]      = None
    thumbnail_url: Optional[str] = None


class CourseResponse(BaseModel):
    id: UUID
    title: str
    description: str
    price: float
    is_free: bool
    thumbnail_url: Optional[str]
    faculty_id: Optional[UUID]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True