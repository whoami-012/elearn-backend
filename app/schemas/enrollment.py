from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID


class EnrollmentCreate(BaseModel):
    course_id: UUID
    user_id: UUID


class EnrollmentUpdate(BaseModel):
    is_active: Optional[bool] = None
    payment_id: Optional[UUID] = None


class EnrollmentResponse(BaseModel):
    id: UUID
    user_id: UUID
    course_id: UUID
    payment_id: Optional[UUID]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
