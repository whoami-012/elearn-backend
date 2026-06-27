from uuid import UUID

from fastapi import status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.messaging.content_validation import validate_message_content
from app.messaging.exceptions import forbidden, messaging_error, not_found
from app.messaging.file_validation import ValidatedUpload
from app.messaging.models import Message, MessageAttachment, MessageType
from app.messaging.permissions import validate_academic_relationship, validate_role_pair
from app.messaging.rate_limit import rate_limiter
from app.messaging.repository import MessagingRepository
from app.models.user import User
from app.storage.message_files import MessageFileStorage


class MessagingService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = MessagingRepository(db)

    async def start_conversation(self, current_user: User, receiver_id: UUID):
        await rate_limiter.check(
            f"conversation:{current_user.id}",
            settings.MESSAGE_CONVERSATION_RATE_LIMIT_PER_MINUTE,
            60,
        )
        if current_user.id == receiver_id:
            raise messaging_error(400, "SELF_MESSAGING_NOT_ALLOWED", "You cannot message yourself.")
        receiver = await self.repo.get_user(receiver_id)
        if receiver is None:
            raise not_found("USER_NOT_FOUND", "The requested user was not found.")
        validate_role_pair(current_user, receiver)
        await validate_academic_relationship(self.db, current_user, receiver)
        existing = await self.repo.get_conversation_between(current_user.id, receiver.id)
        if existing:
            return existing, False
        try:
            conversation = await self.repo.create_conversation(current_user.id, receiver.id)
            await self.db.commit()
            await self.db.refresh(conversation)
            return conversation, True
        except IntegrityError:
            await self.db.rollback()
            existing = await self.repo.get_conversation_between(current_user.id, receiver.id)
            if existing is None:
                raise
            return existing, False

    async def authorize_conversation(self, conversation_id: UUID, current_user: User):
        conversation = await self.repo.get_conversation(conversation_id)
        if conversation is None:
            raise not_found("CONVERSATION_NOT_FOUND", "Conversation not found.")
        if current_user.id not in {conversation.participant_one_id, conversation.participant_two_id}:
            raise forbidden("CONVERSATION_ACCESS_DENIED", "You do not have access to this conversation.")
        other = conversation.participant_two if current_user.id == conversation.participant_one_id else conversation.participant_one
        if not other.is_active or other.is_deleted:
            raise forbidden("CONVERSATION_ACCESS_DENIED", "The other participant is unavailable.")
        validate_role_pair(current_user, other)
        await validate_academic_relationship(self.db, current_user, other)
        return conversation, other

    async def send_text(self, conversation_id: UUID, current_user: User, content: str | None, client_message_id: str | None):
        await rate_limiter.check(f"message:{current_user.id}", settings.MESSAGE_RATE_LIMIT_PER_MINUTE, 60)
        conversation, _ = await self.authorize_conversation(conversation_id, current_user)
        content = validate_message_content(content, required=True)
        existing = await self.repo.get_idempotent_message(current_user.id, client_message_id)
        if existing:
            if existing.conversation_id != conversation_id:
                raise messaging_error(409, "IDEMPOTENCY_KEY_REUSED", "This client message id was used in another conversation.")
            return existing
        message = Message(
            conversation_id=conversation_id,
            sender_id=current_user.id,
            message_type=MessageType.TEXT,
            content=content,
            client_message_id=client_message_id,
        )
        try:
            await self.repo.add_message(message)
            conversation.last_message = message
            await self.db.commit()
            await self.db.refresh(message)
            return message
        except IntegrityError:
            await self.db.rollback()
            existing = await self.repo.get_idempotent_message(current_user.id, client_message_id)
            if existing and existing.conversation_id == conversation_id:
                return existing
            raise

    async def send_upload(
        self,
        conversation_id: UUID,
        current_user: User,
        content: str | None,
        client_message_id: str,
        upload: ValidatedUpload,
        storage: MessageFileStorage,
    ):
        await rate_limiter.check(
            f"upload:{current_user.id}", settings.MESSAGE_UPLOAD_RATE_LIMIT_PER_10_MINUTES, 600
        )
        conversation, _ = await self.authorize_conversation(conversation_id, current_user)
        content = validate_message_content(content, required=False)
        existing = await self.repo.get_idempotent_message(current_user.id, client_message_id)
        if existing:
            upload.temporary_path.unlink(missing_ok=True)
            if existing.conversation_id != conversation_id:
                raise messaging_error(409, "IDEMPOTENCY_KEY_REUSED", "This client message id was used in another conversation.")
            return existing
        try:
            await storage.persist(upload)
        except Exception:
            upload.temporary_path.unlink(missing_ok=True)
            raise
        message = Message(
            conversation_id=conversation_id,
            sender_id=current_user.id,
            message_type=MessageType.TEXT_WITH_FILE if content else MessageType.FILE,
            content=content,
            client_message_id=client_message_id,
        )
        attachment = MessageAttachment(
            original_filename=upload.original_filename,
            storage_key=upload.storage_key,
            mime_type=upload.mime_type,
            file_extension=upload.extension,
            file_size=upload.file_size,
            checksum=upload.checksum,
            scan_status="clean",
        )
        message.attachment = attachment
        try:
            await self.repo.add_message(message)
            conversation.last_message = message
            await self.db.commit()
            await self.db.refresh(message)
            return message
        except Exception:
            await self.db.rollback()
            await storage.delete(upload.storage_key)
            raise

    async def mark_read(self, conversation_id: UUID, current_user: User, message_id: UUID):
        await self.authorize_conversation(conversation_id, current_user)
        message = await self.repo.get_message(message_id)
        if message is None or message.conversation_id != conversation_id:
            raise messaging_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "INVALID_READ_POSITION", "Read position is not in this conversation.")
        state = await self.repo.mark_read(conversation_id, current_user.id, message)
        await self.db.commit()
        return state

    async def authorize_attachment(self, attachment_id: UUID, current_user: User):
        attachment = await self.repo.get_attachment(attachment_id)
        if attachment is None:
            raise not_found("ATTACHMENT_NOT_FOUND", "Attachment not found.")
        await self.authorize_conversation(attachment.message.conversation_id, current_user)
        if attachment.scan_status != "clean":
            raise forbidden("FILE_SCAN_FAILED", "This attachment is not available for download.")
        return attachment
