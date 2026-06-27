import enum
import uuid

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class MessageType(str, enum.Enum):
    TEXT = "text"
    FILE = "file"
    TEXT_WITH_FILE = "text_with_file"


class DirectConversation(Base):
    __tablename__ = "direct_conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    participant_one_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    participant_two_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    last_message_id = Column(
        UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="SET NULL", use_alter=True, name="fk_conversation_last_message"),
        nullable=True,
    )

    participant_one = relationship("User", foreign_keys=[participant_one_id])
    participant_two = relationship("User", foreign_keys=[participant_two_id])
    messages = relationship(
        "Message",
        back_populates="conversation",
        foreign_keys="Message.conversation_id",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    last_message = relationship("Message", foreign_keys=[last_message_id], post_update=True)
    read_states = relationship("ConversationReadState", back_populates="conversation", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("participant_one_id <> participant_two_id", name="ck_direct_conversation_distinct_users"),
        CheckConstraint("participant_one_id < participant_two_id", name="ck_direct_conversation_normalized_pair"),
        UniqueConstraint("participant_one_id", "participant_two_id", name="uq_direct_conversation_participants"),
        Index("ix_direct_conversations_participant_one", "participant_one_id"),
        Index("ix_direct_conversations_participant_two", "participant_two_id"),
        Index("ix_direct_conversations_updated_at", "updated_at"),
    )


class Message(Base):
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("direct_conversations.id", ondelete="CASCADE"), nullable=False)
    sender_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    message_type = Column(SQLEnum(MessageType, name="message_type", values_callable=lambda values: [v.value for v in values]), nullable=False)
    content = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    edited_at = Column(DateTime(timezone=True), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    client_message_id = Column(String(128), nullable=True)

    conversation = relationship("DirectConversation", back_populates="messages", foreign_keys=[conversation_id])
    sender = relationship("User", foreign_keys=[sender_id])
    attachment = relationship("MessageAttachment", back_populates="message", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("sender_id", "client_message_id", name="uq_message_sender_client_id"),
        Index("ix_messages_conversation_created", "conversation_id", "created_at", "id"),
        Index("ix_messages_sender", "sender_id"),
    )


class MessageAttachment(Base):
    __tablename__ = "message_attachments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"), nullable=False, unique=True)
    original_filename = Column(String(255), nullable=False)
    storage_key = Column(String(512), nullable=False, unique=True)
    mime_type = Column(String(128), nullable=False)
    file_extension = Column(String(16), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    checksum = Column(String(64), nullable=False)
    scan_status = Column(String(20), nullable=False, server_default="clean")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    message = relationship("Message", back_populates="attachment")

    __table_args__ = (CheckConstraint("file_size > 0", name="ck_message_attachment_positive_size"),)


class ConversationReadState(Base):
    __tablename__ = "conversation_read_states"

    conversation_id = Column(UUID(as_uuid=True), ForeignKey("direct_conversations.id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    last_read_message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id", ondelete="SET NULL"), nullable=True)
    last_read_at = Column(DateTime(timezone=True), nullable=True)

    conversation = relationship("DirectConversation", back_populates="read_states", foreign_keys=[conversation_id])
    user = relationship("User", foreign_keys=[user_id])
    last_read_message = relationship("Message", foreign_keys=[last_read_message_id])

    __table_args__ = (Index("ix_read_states_user", "user_id"),)
