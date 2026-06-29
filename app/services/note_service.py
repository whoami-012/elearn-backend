from typing import Optional
from uuid import UUID

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import UserRole, require_course_faculty_or_admin, require_faculty_or_admin, user_role
from app.models.note import Note
from app.models.user import User
from app.repositories.note_repo import NoteRepo
from app.schemas.note import NoteCreate, NoteUpdate
from app.services import upload_service
from app.services.audit_service import log_admin_action
from app.services.course_service import get_course_by_id
from app.services.enrollment_service import is_user_enrolled


def _get_file_type(file: UploadFile) -> Optional[str]:
    if file.content_type:
        return file.content_type.lower()
    if file.filename and "." in file.filename:
        return file.filename.rsplit(".", 1)[-1].lower()
    return None


async def _get_note_or_404(db: AsyncSession, note_id: UUID) -> Note:
    note = await NoteRepo(db).get_note_by_id(note_id)
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    return note


async def create_note(
    db: AsyncSession,
    note: NoteCreate,
    file: Optional[UploadFile],
    current_user: User,
    course_id: UUID,
) -> Note:
    require_faculty_or_admin(current_user)
    course = await get_course_by_id(db, course_id)
    require_course_faculty_or_admin(course, current_user)

    if file:
        file_url = await upload_service.upload_file(file)
        file_type = _get_file_type(file)
    else:
        file_url = None
        file_type = None

    if not note.content and not file_url:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Note must have either content or a file")

    new_note = Note(
        title=note.title,
        content=note.content,
        file_url=file_url,
        file_type=file_type,
        is_free=note.is_free,
        course_id=course_id,
        uploaded_by=current_user.id,
    )
    db.add(new_note)
    if user_role(current_user) == UserRole.ADMIN:
        await log_admin_action(
            db,
            actor=current_user,
            action="note.create",
            resource_type="note",
            resource_id=str(new_note.id),
            new_values={"course_id": str(course_id), "title": note.title, "is_free": note.is_free},
        )
    await db.commit()
    await db.refresh(new_note)
    return new_note


async def update_note(
    db: AsyncSession,
    note_id: UUID,
    data: NoteUpdate,
    file: Optional[UploadFile],
    current_user: User,
) -> Note:
    require_faculty_or_admin(current_user)
    note = await _get_note_or_404(db, note_id)
    course = await get_course_by_id(db, note.course_id)
    require_course_faculty_or_admin(course, current_user)
    old_values = {"title": note.title, "content": note.content, "is_free": note.is_free, "file_url": note.file_url}

    if file:
        note.file_url = await upload_service.upload_file(file)
        note.file_type = _get_file_type(file)

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(note, field, value)

    if not note.content and not note.file_url:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Note must have either content or a file")

    if user_role(current_user) == UserRole.ADMIN:
        await log_admin_action(
            db,
            actor=current_user,
            action="note.update",
            resource_type="note",
            resource_id=str(note.id),
            old_values=old_values,
            new_values={"title": note.title, "content": note.content, "is_free": note.is_free, "file_url": note.file_url},
        )
    await db.commit()
    await db.refresh(note)
    return note


async def delete_note(db: AsyncSession, note_id: UUID, current_user: User) -> None:
    require_faculty_or_admin(current_user)
    note = await _get_note_or_404(db, note_id)
    course = await get_course_by_id(db, note.course_id)
    require_course_faculty_or_admin(course, current_user)
    if user_role(current_user) == UserRole.ADMIN:
        await log_admin_action(
            db,
            actor=current_user,
            action="note.delete",
            resource_type="note",
            resource_id=str(note.id),
            old_values={"title": note.title, "course_id": str(note.course_id)},
        )
    await db.delete(note)
    await db.commit()


async def get_notes_by_course(
    db: AsyncSession,
    course_id: UUID,
    current_user: Optional[User],
) -> list[Note]:
    repo = NoteRepo(db)
    notes = await repo.get_note_by_course(course_id)
    course = await get_course_by_id(db, course_id)

    if not current_user:
        return [note for note in notes if note.is_free]

    role = user_role(current_user)
    if role == UserRole.ADMIN:
        return notes
    if role in {UserRole.FACULTY, UserRole.TEACHER} and course.faculty_id == current_user.id:
        return notes
    if await is_user_enrolled(db, current_user.id, course_id):
        return notes
    return [n for n in notes if n.is_free]


async def get_note_by_id(
    db: AsyncSession,
    note_id: UUID,
    current_user: Optional[User],
) -> Note:
    note = await _get_note_or_404(db, note_id)
    course = await get_course_by_id(db, note.course_id)

    if note.is_free:
        return note
    if not current_user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not enrolled in this course")

    role = user_role(current_user)
    if role == UserRole.ADMIN:
        return note
    if role in {UserRole.FACULTY, UserRole.TEACHER} and course.faculty_id == current_user.id:
        return note
    if await is_user_enrolled(db, current_user.id, note.course_id):
        return note
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not enrolled in this course")
