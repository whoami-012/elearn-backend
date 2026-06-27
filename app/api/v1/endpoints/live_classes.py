from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.dependencies import get_db
from app.models.user import User
from app.schemas.live_class import AttendanceResponse, JoinClassInfo, JoinResponse, LiveClassCreate, LiveClassResponse, LiveClassUpdate
from app.services import live_class_service as service

router = APIRouter(prefix="/live-classes", tags=["Live Classes"])
_hits: dict[str, deque[datetime]] = defaultdict(deque)


def rate_limit(action: str, user: User, limit: int = 30, window: int = 60) -> None:
    key = f"{action}:{user.id}"
    now = datetime.now(timezone.utc)
    queue = _hits[key]
    while queue and queue[0] < now - timedelta(seconds=window):
        queue.popleft()
    if len(queue) >= limit:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many requests")
    queue.append(now)


def response(item) -> LiveClassResponse:
    result = LiveClassResponse.model_validate(item)
    return result.model_copy(update={"faculty_name": item.faculty.name if item.faculty else None})


def join_response(item, uid, broadcaster, credential) -> JoinResponse:
    return JoinResponse(
        live_class_id=item.id, app_id=service.settings.AGORA_APP_ID, channel_name=item.agora_channel_name,
        token=credential.token, uid=uid, role="broadcaster" if broadcaster else "audience",
        token_expires_at=credential.expires_at,
        class_=JoinClassInfo(title=item.title, faculty_name=item.faculty.name, scheduled_start_time=item.scheduled_start_time, status=item.status),
    )


@router.post("", response_model=LiveClassResponse, status_code=status.HTTP_201_CREATED)
async def create(data: LiveClassCreate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    return response(await service.create_live_class(db, data, user))


@router.get("", response_model=list[LiveClassResponse])
async def list_all(class_status: str | None = Query(None, alias="status"), db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    return [response(x) for x in await service.list_live_classes(db, user, class_status)]


@router.get("/{class_id}", response_model=LiveClassResponse)
async def get_one(class_id: UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    return response(await service.get_visible(db, class_id, user))


@router.patch("/{class_id}", response_model=LiveClassResponse)
async def update(class_id: UUID, data: LiveClassUpdate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    return response(await service.update_live_class(db, class_id, data, user))


@router.post("/{class_id}/start", response_model=JoinResponse, response_model_by_alias=True)
async def start(class_id: UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    item, uid, broadcaster, token = await service.start_class(db, class_id, user)
    return join_response(item, uid, broadcaster, token)


@router.post("/{class_id}/join", response_model=JoinResponse, response_model_by_alias=True)
async def join(class_id: UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    rate_limit("join", user, 10)
    return join_response(*(await service.credentials(db, class_id, user)))


@router.post("/{class_id}/refresh-token", response_model=JoinResponse, response_model_by_alias=True)
async def refresh(class_id: UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    rate_limit("refresh", user, 10)
    return join_response(*(await service.credentials(db, class_id, user, refresh=True)))


@router.post("/{class_id}/heartbeat", response_model=AttendanceResponse)
async def heartbeat(class_id: UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    rate_limit("heartbeat", user, 4)
    return await service.heartbeat(db, class_id, user)


@router.post("/{class_id}/leave", response_model=AttendanceResponse)
async def leave(class_id: UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    return await service.leave(db, class_id, user)


@router.post("/{class_id}/end", response_model=LiveClassResponse)
async def end(class_id: UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    return response(await service.finish(db, class_id, user))


@router.post("/{class_id}/cancel", response_model=LiveClassResponse)
async def cancel(class_id: UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    return response(await service.finish(db, class_id, user, cancelled=True))


@router.get("/{class_id}/attendance", response_model=list[AttendanceResponse])
async def attendance(class_id: UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    rows = await service.attendance_list(db, class_id, user)
    return [AttendanceResponse.model_validate(x).model_copy(update={"student_name": x.student.name}) for x in rows]
