from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.messaging.models import ConversationReadState, DirectConversation, Message, MessageAttachment
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.user import User


def normalize_participants(first: UUID, second: UUID) -> tuple[UUID, UUID]:
    return (first, second) if first.bytes < second.bytes else (second, first)


class MessagingRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user(self, user_id: UUID) -> User | None:
        return await self.db.scalar(
            select(User).where(User.id == user_id, User.is_active.is_(True), User.is_deleted.is_(False))
        )

    async def get_conversation_between(self, first: UUID, second: UUID) -> DirectConversation | None:
        one, two = normalize_participants(first, second)
        return await self.db.scalar(
            select(DirectConversation).where(
                DirectConversation.participant_one_id == one,
                DirectConversation.participant_two_id == two,
            )
        )

    async def create_conversation(self, first: UUID, second: UUID) -> DirectConversation:
        one, two = normalize_participants(first, second)
        conversation = DirectConversation(participant_one_id=one, participant_two_id=two)
        self.db.add(conversation)
        await self.db.flush()
        return conversation

    async def get_conversation(self, conversation_id: UUID) -> DirectConversation | None:
        return await self.db.scalar(
            select(DirectConversation)
            .where(DirectConversation.id == conversation_id)
            .options(
                selectinload(DirectConversation.participant_one),
                selectinload(DirectConversation.participant_two),
                selectinload(DirectConversation.last_message).selectinload(Message.attachment),
                selectinload(DirectConversation.read_states),
            )
        )

    async def list_conversations(self, user_id: UUID, limit: int, cursor: UUID | None = None) -> list[DirectConversation]:
        query = (
            select(DirectConversation)
            .where(or_(DirectConversation.participant_one_id == user_id, DirectConversation.participant_two_id == user_id))
            .options(
                selectinload(DirectConversation.participant_one),
                selectinload(DirectConversation.participant_two),
                selectinload(DirectConversation.last_message).selectinload(Message.attachment),
                selectinload(DirectConversation.read_states),
            )
            .order_by(DirectConversation.updated_at.desc(), DirectConversation.id.desc())
            .limit(limit + 1)
        )
        if cursor:
            anchor = await self.db.scalar(select(DirectConversation).where(DirectConversation.id == cursor))
            if anchor:
                query = query.where(
                    or_(
                        DirectConversation.updated_at < anchor.updated_at,
                        and_(DirectConversation.updated_at == anchor.updated_at, DirectConversation.id < anchor.id),
                    )
                )
        return list((await self.db.scalars(query)).all())

    async def list_messages(self, conversation_id: UUID, limit: int, before_id: UUID | None = None) -> list[Message]:
        query = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .options(selectinload(Message.attachment))
            .order_by(Message.created_at.desc(), Message.id.desc())
            .limit(limit + 1)
        )
        if before_id:
            anchor = await self.db.scalar(select(Message).where(Message.id == before_id, Message.conversation_id == conversation_id))
            if anchor:
                query = query.where(
                    or_(Message.created_at < anchor.created_at, and_(Message.created_at == anchor.created_at, Message.id < anchor.id))
                )
        return list((await self.db.scalars(query)).all())

    async def get_message(self, message_id: UUID) -> Message | None:
        return await self.db.scalar(
            select(Message).where(Message.id == message_id).options(selectinload(Message.attachment))
        )

    async def get_idempotent_message(self, sender_id: UUID, client_message_id: str | None) -> Message | None:
        if not client_message_id:
            return None
        return await self.db.scalar(
            select(Message)
            .where(Message.sender_id == sender_id, Message.client_message_id == client_message_id)
            .options(selectinload(Message.attachment))
        )

    async def add_message(self, message: Message) -> Message:
        self.db.add(message)
        await self.db.flush()
        return message

    async def unread_count(self, conversation_id: UUID, user_id: UUID) -> int:
        read_at = await self.db.scalar(
            select(ConversationReadState.last_read_at).where(
                ConversationReadState.conversation_id == conversation_id,
                ConversationReadState.user_id == user_id,
            )
        )
        conditions = [Message.conversation_id == conversation_id, Message.sender_id != user_id]
        if read_at:
            conditions.append(Message.created_at > read_at)
        return int(await self.db.scalar(select(func.count(Message.id)).where(*conditions)) or 0)

    async def total_unread_count(self, user_id: UUID) -> int:
        conversation_ids = list(
            (await self.db.scalars(
                select(DirectConversation.id).where(
                    or_(DirectConversation.participant_one_id == user_id, DirectConversation.participant_two_id == user_id)
                )
            )).all()
        )
        return sum((await self.unread_counts(conversation_ids, user_id)).values())

    async def unread_counts(self, conversation_ids: list[UUID], user_id: UUID) -> dict[UUID, int]:
        if not conversation_ids:
            return {}
        statement = (
            select(Message.conversation_id, func.count(Message.id))
            .outerjoin(
                ConversationReadState,
                and_(
                    ConversationReadState.conversation_id == Message.conversation_id,
                    ConversationReadState.user_id == user_id,
                ),
            )
            .where(
                Message.conversation_id.in_(conversation_ids),
                Message.sender_id != user_id,
                or_(
                    ConversationReadState.last_read_at.is_(None),
                    Message.created_at > ConversationReadState.last_read_at,
                ),
            )
            .group_by(Message.conversation_id)
        )
        return {conversation_id: int(count) for conversation_id, count in (await self.db.execute(statement)).all()}

    async def mark_read(self, conversation_id: UUID, user_id: UUID, message: Message) -> ConversationReadState:
        state = await self.db.get(ConversationReadState, (conversation_id, user_id))
        if state is None:
            state = ConversationReadState(conversation_id=conversation_id, user_id=user_id)
            self.db.add(state)
        state.last_read_message_id = message.id
        state.last_read_at = message.created_at or datetime.now(timezone.utc)
        await self.db.flush()
        return state

    async def get_attachment(self, attachment_id: UUID) -> MessageAttachment | None:
        return await self.db.scalar(
            select(MessageAttachment)
            .where(MessageAttachment.id == attachment_id)
            .options(
                selectinload(MessageAttachment.message)
                .selectinload(Message.conversation)
            )
        )

    async def available_contacts(self, user: User, search: str | None, limit: int) -> list[tuple[User, Course]]:
        role = str(user.role.value if hasattr(user.role, "value") else user.role)
        if role == "student":
            query = (
                select(User, Course)
                .join(Course, Course.faculty_id == User.id)
                .join(Enrollment, Enrollment.course_id == Course.id)
                .where(
                    Enrollment.user_id == user.id,
                    Enrollment.is_active.is_(True),
                    Course.is_deleted.is_(False),
                    User.is_active.is_(True),
                    User.is_deleted.is_(False),
                )
            )
        elif role in {"faculty", "teacher"}:
            query = (
                select(User, Course)
                .join(Enrollment, Enrollment.user_id == User.id)
                .join(Course, Course.id == Enrollment.course_id)
                .where(
                    Course.faculty_id == user.id,
                    Enrollment.is_active.is_(True),
                    User.role == "student",
                    User.is_active.is_(True),
                    User.is_deleted.is_(False),
                )
            )
        else:
            return []
        if search:
            query = query.where(User.name.ilike(f"%{search}%"))
        return list((await self.db.execute(query.order_by(User.name).limit(limit))).tuples().all())
