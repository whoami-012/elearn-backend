import logging
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, RedirectResponse
from jose import JWTError
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.security import decode_token
from app.db.dependencies import get_db
from app.db.session import AsyncSessionLocal
from app.messaging.content_validation import validate_search_text
from app.messaging.exceptions import messaging_error
from app.messaging.file_validation import stream_and_validate_upload
from app.messaging.models import Message, MessageType
from app.messaging.repository import MessagingRepository
from app.messaging.schemas import (
    ContactResponse,
    ContactsPage,
    ConversationCreate,
    ConversationDetailResponse,
    ConversationsPage,
    ConversationSummaryResponse,
    LastMessageResponse,
    MarkReadRequest,
    MessageCreate,
    MessageResponse,
    MessagesPage,
    ParticipantResponse,
    SharedCourseResponse,
    UnreadCountResponse,
    WebSocketClientEvent,
)
from app.messaging.service import MessagingService
from app.messaging.websocket import connection_manager
from app.models.user import User
from app.repositories.user_repo import UserRepo
from app.storage.message_files import get_message_storage

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/messages", tags=["Messaging"])


def participant_response(user: User) -> ParticipantResponse:
    return ParticipantResponse(id=user.id, name=user.name, role=str(user.role), avatar_url=None)


def message_response(message: Message) -> MessageResponse:
    attachment = message.attachment
    attachment_response = None
    attachment_url = None
    if attachment is not None:
        attachment_url = f"/api/v1/messages/attachments/{attachment.id}"
        attachment_response = {
            "id": attachment.id,
            "original_filename": attachment.original_filename,
            "mime_type": attachment.mime_type,
            "attachment_type": attachment.attachment_type,
            "file_extension": attachment.file_extension,
            "file_size": attachment.file_size,
            "checksum": attachment.checksum,
            "attachment_url": attachment_url,
            "file_name": attachment.original_filename,
            "thumbnail_url": attachment.thumbnail_url,
        }
    return MessageResponse(
        id=message.id,
        conversation_id=message.conversation_id,
        sender_id=message.sender_id,
        message_type=message.message_type,
        content=message.content,
        created_at=message.created_at,
        updated_at=message.updated_at,
        edited_at=message.edited_at,
        deleted_at=message.deleted_at,
        client_message_id=message.client_message_id,
        attachment=attachment_response,
        attachment_url=attachment_url,
        attachment_type=attachment.attachment_type if attachment else None,
        mime_type=attachment.mime_type if attachment else None,
        file_name=attachment.original_filename if attachment else None,
        file_size=attachment.file_size if attachment else None,
        thumbnail_url=attachment.thumbnail_url if attachment else None,
    )


async def conversation_detail(service: MessagingService, conversation_id: UUID, current_user: User):
    conversation, other = await service.authorize_conversation(conversation_id, current_user)
    return ConversationDetailResponse(
        id=conversation.id,
        participant=participant_response(other),
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
    )


@router.get("/contacts", response_model=ContactsPage)
async def get_contacts(
    search: str | None = None,
    role: str | None = None,
    course_id: UUID | None = None,
    department_id: UUID | None = None,
    cursor: str | None = None,
    limit: int = Query(30, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    del department_id, cursor  # Current schema has neither departments nor a stable contact cursor.
    search = validate_search_text(search)
    rows = await MessagingRepository(db).available_contacts(current_user, search, limit + 1)
    items = []
    seen = set()
    for user, course in rows:
        if user.id in seen or (role and str(user.role) != role) or (course_id and course.id != course_id):
            continue
        seen.add(user.id)
        items.append(
            ContactResponse(
                **participant_response(user).model_dump(),
                shared_course=SharedCourseResponse(id=course.id, name=course.title),
            )
        )
        if len(items) == limit:
            break
    return ContactsPage(items=items, next_cursor=None)


@router.get("/unread-count", response_model=UnreadCountResponse)
async def get_total_unread_count(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return UnreadCountResponse(unread_count=await MessagingRepository(db).total_unread_count(current_user.id))


@router.post("/conversations", response_model=ConversationDetailResponse)
async def start_conversation(
    payload: ConversationCreate,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = MessagingService(db)
    conversation, created = await service.start_conversation(current_user, payload.receiver_id)
    response.status_code = 201 if created else 200
    return await conversation_detail(service, conversation.id, current_user)


@router.get("/conversations", response_model=ConversationsPage)
async def list_conversations(
    filter: str = Query("all", pattern="^(all|teachers|faculty|students|unread)$"),
    search: str | None = None,
    cursor: UUID | None = None,
    limit: int = Query(30, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    search = validate_search_text(search)
    repo = MessagingRepository(db)
    conversations = await repo.list_conversations(current_user.id, limit, cursor)
    has_more = len(conversations) > limit
    conversations = conversations[:limit]
    unread_by_conversation = await repo.unread_counts([item.id for item in conversations], current_user.id)
    items = []
    for conversation in conversations:
        other = conversation.participant_two if current_user.id == conversation.participant_one_id else conversation.participant_one
        unread = unread_by_conversation.get(conversation.id, 0)
        other_role = str(other.role)
        if filter != "all" and filter != "unread":
            expected = filter[:-1] if filter.endswith("s") else filter
            if other_role != expected:
                continue
        if filter == "unread" and unread == 0:
            continue
        if search and search.casefold() not in other.name.casefold():
            continue
        last = conversation.last_message
        last_response = None
        if last:
            preview = "Attachment" if not last.content else last.content[:120]
            last_response = LastMessageResponse(
                id=last.id,
                type=last.message_type,
                preview=preview,
                created_at=last.created_at,
                is_sent_by_current_user=last.sender_id == current_user.id,
                has_attachment=last.attachment is not None,
                attachment_type=last.attachment.attachment_type if last.attachment else None,
                mime_type=last.attachment.mime_type if last.attachment else None,
                file_name=last.attachment.original_filename if last.attachment else None,
                file_size=last.attachment.file_size if last.attachment else None,
                thumbnail_url=last.attachment.thumbnail_url if last.attachment else None,
            )
        items.append(
            ConversationSummaryResponse(
                id=conversation.id,
                participant=participant_response(other),
                last_message=last_response,
                unread_count=unread,
                updated_at=conversation.updated_at,
            )
        )
    next_cursor = str(conversations[-1].id) if has_more and conversations else None
    return ConversationsPage(items=items, next_cursor=next_cursor)


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(conversation_id: UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await conversation_detail(MessagingService(db), conversation_id, current_user)


@router.get("/conversations/{conversation_id}/messages", response_model=MessagesPage)
async def list_messages(
    conversation_id: UUID,
    cursor: UUID | None = None,
    before_message_id: UUID | None = None,
    limit: int = Query(30, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = MessagingService(db)
    await service.authorize_conversation(conversation_id, current_user)
    messages = await service.repo.list_messages(conversation_id, limit, before_message_id or cursor)
    has_more = len(messages) > limit
    messages = messages[:limit]
    return MessagesPage(
        items=[message_response(message) for message in reversed(messages)],
        next_cursor=str(messages[-1].id) if has_more and messages else None,
    )


@router.post("/conversations/{conversation_id}/messages", response_model=MessageResponse, status_code=201)
async def send_message(
    conversation_id: UUID,
    payload: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = MessagingService(db)
    conversation, _ = await service.authorize_conversation(conversation_id, current_user)
    message = await service.send_text(
        conversation_id, current_user, payload.content, payload.client_message_id
    )
    await connection_manager.send_to_users(
        {conversation.participant_one_id, conversation.participant_two_id},
        conversation.id,
        {"event": "message.created", "data": message_response(message).model_dump(mode="json")},
    )
    return message_response(message)


@router.post("/conversations/{conversation_id}/messages/upload", response_model=MessageResponse, status_code=201)
async def send_message_upload(
    conversation_id: UUID,
    file: UploadFile = File(...),
    content: str | None = Form(None),
    client_message_id: str = Form(..., min_length=1, max_length=128),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = MessagingService(db)
    conversation, _ = await service.authorize_conversation(conversation_id, current_user)
    storage = get_message_storage()
    temp_dir = Path(settings.MESSAGE_LOCAL_STORAGE_PATH).resolve() / ".tmp"
    validated = await stream_and_validate_upload(file, temp_dir)
    message = await service.send_upload(
        conversation_id, current_user, content, client_message_id, validated, storage
    )
    await connection_manager.send_to_users(
        {conversation.participant_one_id, conversation.participant_two_id},
        conversation.id,
        {"event": "message.created", "data": message_response(message).model_dump(mode="json")},
    )
    return message_response(message)


@router.post("/conversations/{conversation_id}/read", status_code=204)
async def mark_conversation_read(
    conversation_id: UUID,
    payload: MarkReadRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = MessagingService(db)
    conversation, _ = await service.authorize_conversation(conversation_id, current_user)
    await service.mark_read(conversation_id, current_user, payload.last_read_message_id)
    await connection_manager.send_to_users(
        {conversation.participant_one_id, conversation.participant_two_id},
        conversation.id,
        {
            "event": "message.read",
            "conversation_id": str(conversation.id),
            "user_id": str(current_user.id),
        },
    )


@router.get("/attachments/{attachment_id}")
async def download_attachment(
    attachment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    attachment = await MessagingService(db).authorize_attachment(attachment_id, current_user)
    storage = get_message_storage()
    path = storage.local_path(attachment.storage_key)
    signed_url = storage.signed_download_url(
        attachment.storage_key, attachment.original_filename, attachment.mime_type
    )
    if signed_url:
        return RedirectResponse(signed_url, status_code=307, headers={"Cache-Control": "private, no-store"})
    if path is None:
        raise messaging_error(404, "ATTACHMENT_NOT_FOUND", "Attachment data was not found.")
    return FileResponse(
        path,
        media_type=attachment.mime_type,
        filename=attachment.original_filename,
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
    )


@router.websocket("/ws")
async def messaging_websocket(websocket: WebSocket, token: str | None = Query(None)):
    auth_header = websocket.headers.get("authorization", "")
    token = token or (auth_header[7:] if auth_header.lower().startswith("bearer ") else None)
    if not token:
        await websocket.close(code=4401)
        return
    try:
        payload = decode_token(token)
        user_id = UUID(payload["sub"])
    except (JWTError, KeyError, ValueError, TypeError):
        await websocket.close(code=4401)
        return
    async with AsyncSessionLocal() as db:
        user = await UserRepo(db).get_by_id(user_id)
        if not user or not user.is_active or user.is_deleted:
            await websocket.close(code=4401)
            return
        if not await connection_manager.connect(user.id, websocket):
            await websocket.close(code=4429)
            return
        service = MessagingService(db)
        try:
            while True:
                raw = await websocket.receive_json()
                try:
                    event = WebSocketClientEvent.model_validate(raw)
                    if event.event == "ping":
                        await websocket.send_json({"event": "pong"})
                        continue
                    if event.conversation_id is None:
                        raise messaging_error(422, "CONVERSATION_NOT_FOUND", "conversation_id is required.")
                    conversation, _ = await service.authorize_conversation(event.conversation_id, user)
                    if event.event == "subscribe":
                        await connection_manager.subscribe(websocket, conversation.id)
                        await websocket.send_json({"event": "subscribed", "conversation_id": str(conversation.id)})
                    elif event.event == "send_message":
                        message = await service.send_text(conversation.id, user, event.content, event.client_message_id)
                        await connection_manager.send_to_users(
                            {conversation.participant_one_id, conversation.participant_two_id},
                            conversation.id,
                            {"event": "message.created", "data": message_response(message).model_dump(mode="json")},
                        )
                    elif event.event == "mark_read":
                        if event.last_read_message_id is None:
                            raise messaging_error(422, "INVALID_READ_POSITION", "last_read_message_id is required.")
                        await service.mark_read(conversation.id, user, event.last_read_message_id)
                        await connection_manager.send_to_users(
                            {conversation.participant_one_id, conversation.participant_two_id},
                            conversation.id,
                            {"event": "message.read", "conversation_id": str(conversation.id), "user_id": str(user.id)},
                        )
                except ValidationError as exc:
                    await websocket.send_json({"event": "error", "detail": {"code": "INVALID_EVENT", "message": str(exc)}})
                except Exception as exc:
                    detail = getattr(exc, "detail", None)
                    if isinstance(detail, dict):
                        await websocket.send_json({"event": "error", "detail": detail})
                    else:
                        logger.exception("messaging_websocket_event_failed user_id=%s", user.id)
                        await websocket.send_json({"event": "error", "detail": {"code": "INTERNAL_ERROR", "message": "Event could not be processed."}})
        except WebSocketDisconnect:
            pass
        finally:
            await connection_manager.disconnect(user.id, websocket)
