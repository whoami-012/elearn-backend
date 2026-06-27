"""
services/upload_service.py — Business logic for file uploads.

Responsibilities:
  - Validate file type and size
  - Generate a unique filename
  - Save file to local static directory
  - Return the public URL path

Functions:
  - upload_thumbnail  : Save image files (JPEG / PNG / WebP) for course thumbnails.
  - upload_file       : Save document files (PDF / DOC / DOCX) for notes / materials.
  - delete_thumbnail  : Remove a previously saved thumbnail from disk.
  - delete_file       : Remove a previously saved document from disk.
"""

import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

# ── Config ─────────────────────────────────────────────────────────────────────

UPLOAD_DIR         = Path("static/thumbnails")
MAX_SIZE_BYTES     = 5 * 1024 * 1024          # 5 MB
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}

# All known MIME variations clients may send for valid image types
# (Android image_picker sends 'image/jpg' instead of the official 'image/jpeg')
ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/jpg",          # non-standard but sent by some Android clients
    "image/png",
    "image/webp",
    "application/octet-stream",   # generic fallback — extension is used as truth
}

# Map extension → canonical extension for saving
EXT_MAP = {
    "jpg":  "jpg",
    "jpeg": "jpg",
    "png":  "png",
    "webp": "webp",
}

# ── Doc-upload config ──────────────────────────────────────────────────────────

DOC_UPLOAD_DIR         = Path("static/documents")
DOC_MAX_SIZE_BYTES     = 20 * 1024 * 1024         # 20 MB
DOC_ALLOWED_EXTENSIONS = {"pdf", "doc", "docx"}

DOC_ALLOWED_MIME_TYPES = {
    "application/pdf",                                                      # .pdf
    "application/msword",                                                   # .doc
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
    "application/octet-stream",   # generic fallback — extension is used as truth
}

DOC_EXT_MAP = {
    "pdf":  "pdf",
    "doc":  "doc",
    "docx": "docx",
}


# ── Service ────────────────────────────────────────────────────────────────────

async def upload_thumbnail(file: UploadFile) -> str:
    """
    Validate, save, and return the public URL for a course thumbnail.

    Args:
        file: The uploaded file from FastAPI's UploadFile.

    Returns:
        Public URL string e.g. '/static/thumbnails/abc123.jpg'

    Raises:
        HTTPException 400: Invalid file type or size exceeds limit.
    """
    # ── 1. Determine extension from filename (most reliable signal) ─────────────
    original_name = file.filename or ""
    raw_ext = original_name.rsplit(".", 1)[-1].lower() if "." in original_name else ""
    ext = EXT_MAP.get(raw_ext)

    # ── 2. Fall back to MIME type if extension is missing or unrecognised ────────
    if ext is None:
        mime = (file.content_type or "").lower()
        if mime in ("image/jpeg", "image/jpg"):
            ext = "jpg"
        elif mime == "image/png":
            ext = "png"
        elif mime == "image/webp":
            ext = "webp"

    # ── 3. Reject if still unresolved ────────────────────────────────────────────
    if ext is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unsupported file type. "
                f"Upload a JPEG, PNG, or WebP image "
                f"(received: filename='{original_name}', "
                f"content_type='{file.content_type}')."
            ),
        )

    # ── 4. Generate unique filename & ensure directory exists ─────────────────
    filename = f"{uuid.uuid4()}.{ext}"
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    # ── 5. Read file and validate size ────────────────────────────────────────
    contents = await file.read()
    if len(contents) > MAX_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum allowed size is 5 MB.",
        )

    # ── 6. Save to disk ───────────────────────────────────────────────────────
    file_path = UPLOAD_DIR / filename
    with open(file_path, "wb") as f:
        f.write(contents)

    return f"/static/thumbnails/{filename}"


async def upload_file(file: UploadFile) -> str:
    """
    Validate, save, and return the public URL for a document file (PDF / DOC / DOCX).

    Args:
        file: The uploaded file from FastAPI's UploadFile.

    Returns:
        Public URL string e.g. '/static/documents/abc123.pdf'

    Raises:
        HTTPException 400: Unsupported file type or size exceeds 20 MB limit.
    """
    # ── 1. Determine extension from filename ──────────────────────────────────
    original_name = file.filename or ""
    raw_ext = original_name.rsplit(".", 1)[-1].lower() if "." in original_name else ""
    ext = DOC_EXT_MAP.get(raw_ext)

    # ── 2. Fall back to MIME type when extension is missing / unrecognised ────
    if ext is None:
        mime = (file.content_type or "").lower()
        if mime == "application/pdf":
            ext = "pdf"
        elif mime == "application/msword":
            ext = "doc"
        elif mime == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            ext = "docx"

    # ── 3. Reject if still unresolved ─────────────────────────────────────────
    if ext is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unsupported file type. "
                f"Upload a PDF, DOC, or DOCX document "
                f"(received: filename='{original_name}', "
                f"content_type='{file.content_type}')."
            ),
        )

    # ── 4. Generate unique filename & ensure directory exists ─────────────────
    filename = f"{uuid.uuid4()}.{ext}"
    DOC_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    # ── 5. Read file and validate size ────────────────────────────────────────
    contents = await file.read()
    if len(contents) > DOC_MAX_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum allowed size for documents is 20 MB.",
        )

    # ── 6. Save to disk ───────────────────────────────────────────────────────
    file_path = DOC_UPLOAD_DIR / filename
    with open(file_path, "wb") as f:
        f.write(contents)

    return f"/static/documents/{filename}"


async def delete_file(url: str) -> None:
    """
    Remove a previously uploaded document from disk.
    Silently ignores missing files (idempotent).

    Args:
        url: The URL returned by upload_file e.g. '/static/documents/abc.docx'
    """
    if not url or not url.startswith("/static/documents/"):
        return

    filename = url.split("/")[-1]
    file_path = DOC_UPLOAD_DIR / filename

    if file_path.exists():
        file_path.unlink()


async def delete_thumbnail(url: str) -> None:
    """
    Remove a previously uploaded thumbnail from disk.
    Silently ignores missing files (idempotent).

    Args:
        url: The URL returned by upload_thumbnail e.g. '/static/thumbnails/abc.jpg'
    """
    if not url or not url.startswith("/static/thumbnails/"):
        return

    filename = url.split("/")[-1]
    file_path = UPLOAD_DIR / filename

    if file_path.exists():
        file_path.unlink()
