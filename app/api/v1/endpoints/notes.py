from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from fastapi import Form
from app.db.dependencies import get_db
from app.schemas.note import NoteCreate, NoteUpdate, NoteResponse
from app.models.note import Note
from app.api.deps import get_current_user, get_current_user_optional
from app.services import note_service
from fastapi import File, UploadFile
from typing import Optional
from app.models.user import User

router = APIRouter()

router = APIRouter(prefix="/notes", tags=["Notes"])

@router.post("/courses/{course_id}", response_model=NoteResponse)
async def create_note(
    course_id: UUID,
    title: str = Form(...),
    content: Optional[str] = Form(None),
    is_free: bool = Form(False),
    file: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not content and not file:
        raise HTTPException(400, "Content or file required")

    note_data = NoteCreate(
        title=title,
        content=content,
        is_free=is_free
    )
    return await note_service.create_note(db, note_data, file, current_user, course_id)

@router.get("/courses/{course_id}", response_model=list[NoteResponse])
async def get_notes_by_course(
    course_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    return await note_service.get_notes_by_course(db, course_id, current_user)

@router.get("/{note_id}", response_model=NoteResponse)
async def get_note(
    note_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    return await note_service.get_note_by_id(db, note_id, current_user)