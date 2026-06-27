from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.messaging.content_validation import validate_message_content
from app.messaging.models import MessageType


class ConversationCreate(BaseModel):
    receiver_id: UUID


class MessageCreate(BaseModel):
    content: str
    client_message_id: str | None = Field(default=None, max_length=128)

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        return validate_message_content(value, required=True) or ""


class MarkReadRequest(BaseModel):
    last_read_message_id: UUID


class ParticipantResponse(BaseModel):
    id: UUID
    name: str
    role: str
    avatar_url: str | None = None


class SharedCourseResponse(BaseModel):
    id: UUID
    name: str


class ContactResponse(ParticipantResponse):
    department: str | None = None
    shared_course: SharedCourseResponse | None = None


class AttachmentResponse(BaseModel):
    id: UUID
    original_filename: str
    mime_type: str
    file_extension: str
    file_size: int
    checksum: str

    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    sender_id: UUID
    message_type: MessageType
    content: str | None
    created_at: datetime
    updated_at: datetime
    edited_at: datetime | None
    deleted_at: datetime | None
    client_message_id: str | None
    attachment: AttachmentResponse | None = None

    model_config = ConfigDict(from_attributes=True)


class LastMessageResponse(BaseModel):
    id: UUID
    type: MessageType
    preview: str
    created_at: datetime
    is_sent_by_current_user: bool
    has_attachment: bool


class ConversationSummaryResponse(BaseModel):
    id: UUID
    participant: ParticipantResponse
    last_message: LastMessageResponse | None
    unread_count: int
    updated_at: datetime


class ConversationDetailResponse(BaseModel):
    id: UUID
    participant: ParticipantResponse
    created_at: datetime
    updated_at: datetime


class ContactsPage(BaseModel):
    items: list[ContactResponse]
    next_cursor: str | None = None


class ConversationsPage(BaseModel):
    items: list[ConversationSummaryResponse]
    next_cursor: str | None = None


class MessagesPage(BaseModel):
    items: list[MessageResponse]
    next_cursor: str | None = None


class UnreadCountResponse(BaseModel):
    unread_count: int


class WebSocketClientEvent(BaseModel):
    event: Literal["subscribe", "send_message", "mark_read", "ping"]
    conversation_id: UUID | None = None
    content: str | None = None
    client_message_id: str | None = Field(default=None, max_length=128)
    last_read_message_id: UUID | None = None
