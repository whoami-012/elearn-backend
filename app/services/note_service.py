from typing import Optional

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.models.note import Note
from app.models.user import User
from app.repositories.note_repo import NoteRepo
from app.schemas.note import NoteCreate
from app.services.course_service import get_course_by_id
from app.services.enrollment_service import is_user_enrolled
from app.services import upload_service
from fastapi import HTTPException, status


def _get_file_type(file: UploadFile) -> Optional[str]:
    if file.content_type:
        return file.content_type.lower()

    if file.filename and "." in file.filename:
        return file.filename.rsplit(".", 1)[-1].lower()

    return None


# 🔹 Create Course
async def create_note(
    db: AsyncSession,
    note: NoteCreate,
    file: Optional[UploadFile],
    current_user: User,
    course_id: UUID,
) -> Note:

    # role check
    if current_user.role != "faculty":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only faculty can create notes",
        )
    
    # validate course exists
    await get_course_by_id(db, course_id)
    
    # handle file upload
    if file:
        file_url = await upload_service.upload_file(file)
        file_type = _get_file_type(file)
    else:
        file_url = None
        file_type = None
    
    # validate content or file
    if not note.content and not file_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Note must have either content or a file",
        )

    # Create note
    new_note = Note(
        title=note.title,
        content=note.content,
        file_url=file_url,
        file_type=file_type,
        is_free=note.is_free,
        course_id=course_id,
        uploaded_by=current_user.id
    )

    db.add(new_note)
    await db.commit()
    await db.refresh(new_note)

    return new_note
    
async def get_notes_by_course(
    db: AsyncSession,
    course_id: UUID,
    current_user: Optional[User],
) -> list[Note]:
    repo = NoteRepo(db)
    notes = await repo.get_note_by_course(course_id)
    
    # If no user (guest) → only free notes
    if not current_user:
        return [note for note in notes if note.is_free]
    
    # faculty full access
    if current_user.role == "faculty":
        return notes
    
    # Student → check enrollment
    if await is_user_enrolled(db, current_user.id, course_id):
        return notes

    # Not enrolled → only free
    return [n for n in notes if n.is_free]

async def get_note_by_id(
    db: AsyncSession,
    note_id: UUID,
    current_user: Optional[User],
) -> Note:
    repo = NoteRepo(db)
    note = await repo.get_note_by_id(note_id)

    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found",
        )
    
    # Free note allow
    if note.is_free:
        return note
    
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not enrolled in this course",
        )

    # faculty allow
    if current_user.role == "faculty":
        return note
    
    # student check enrollment
    if await is_user_enrolled(db, current_user.id, note.course_id):
        return note
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You are not enrolled in this course",
    )
