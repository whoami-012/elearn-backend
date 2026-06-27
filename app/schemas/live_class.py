from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LiveClassCreate(BaseModel):
    course_id: UUID
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    scheduled_start_time: datetime
    scheduled_end_time: datetime

    @model_validator(mode="after")
    def validate_times(self):
        if self.scheduled_start_time.tzinfo is None or self.scheduled_end_time.tzinfo is None:
            raise ValueError("Scheduled times must include a timezone")
        if self.scheduled_end_time <= self.scheduled_start_time:
            raise ValueError("scheduled_end_time must be after scheduled_start_time")
        self.scheduled_start_time = self.scheduled_start_time.astimezone(timezone.utc)
        self.scheduled_end_time = self.scheduled_end_time.astimezone(timezone.utc)
        return self


class LiveClassUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    scheduled_start_time: datetime | None = None
    scheduled_end_time: datetime | None = None


class LiveClassResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    course_id: UUID
    faculty_id: UUID
    faculty_name: str | None = None
    title: str
    description: str | None
    scheduled_start_time: datetime
    scheduled_end_time: datetime
    duration_minutes: int
    status: Literal["scheduled", "live", "completed", "cancelled"]
    started_at: datetime | None
    ended_at: datetime | None
    created_at: datetime
    updated_at: datetime


class JoinClassInfo(BaseModel):
    title: str
    faculty_name: str = Field(serialization_alias="facultyName")
    scheduled_start_time: datetime
    status: str


class JoinResponse(BaseModel):
    live_class_id: UUID = Field(serialization_alias="liveClassId")
    app_id: str = Field(serialization_alias="appId")
    channel_name: str = Field(serialization_alias="channelName")
    token: str
    uid: int
    role: Literal["audience", "broadcaster"]
    token_expires_at: datetime = Field(serialization_alias="tokenExpiresAt")
    class_: JoinClassInfo = Field(serialization_alias="class")


class AttendanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    live_class_id: UUID
    student_id: UUID
    student_name: str | None = None
    agora_uid: int
    joined_at: datetime
    last_seen_at: datetime
    left_at: datetime | None
    duration_seconds: int
    attendance_status: str
