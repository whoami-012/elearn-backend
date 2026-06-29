from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime

class YoutubeLessonCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    video_id: str
    order_index: int = Field(..., ge=0)
    is_preview: bool = False


class YoutubeLessonUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=255)
    video_id: str | None = None
    order_index: int | None = Field(None, ge=0)
    is_preview: bool | None = None

class YoutubeLessonResponse(BaseModel):
    id: UUID
    course_id: UUID
    title: str
    video_id: str
    is_preview: bool = False
    order_index: int

    class Config:
        from_attributes = True

class ZoomLessonCreate(BaseModel):
    title: str
    course_id: UUID
    start_time: datetime
    duration: int
    is_free: bool = False
