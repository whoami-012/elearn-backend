import hashlib
import os
import re
import unicodedata
import zipfile
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import settings
from app.messaging.exceptions import messaging_error, unprocessable

CHUNK_SIZE = 64 * 1024
_SAFE_FILENAME = re.compile(r"[^\w .()\-]+", re.UNICODE)

MIME_BY_EXTENSION = {
    "pdf": "application/pdf",
    "doc": "application/msword",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "ppt": "application/vnd.ms-powerpoint",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "xls": "application/vnd.ms-excel",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "txt": "text/plain",
    "csv": "text/csv",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
}


@dataclass(frozen=True)
class ValidatedUpload:
    temporary_path: Path
    original_filename: str
    extension: str
    mime_type: str
    file_size: int
    checksum: str
    storage_key: str


def _file_contains(path: Path, markers: tuple[bytes, ...]) -> bool:
    overlap = b""
    with path.open("rb") as stream:
        while chunk := stream.read(CHUNK_SIZE):
            block = overlap + chunk
            if any(marker in block for marker in markers):
                return True
            overlap = block[-64:]
    return False


def sanitize_filename(filename: str | None) -> tuple[str, str]:
    if not filename or "\x00" in filename:
        raise unprocessable("FILE_TYPE_NOT_ALLOWED", "A valid filename is required.")
    filename = unicodedata.normalize("NFC", filename.replace("\\", "/").split("/")[-1]).strip()
    filename = _SAFE_FILENAME.sub("_", filename)[:255]
    path = Path(filename)
    extension = path.suffix.lower().lstrip(".")
    if not path.stem or not extension or "." in path.stem:
        raise unprocessable("FILE_TYPE_NOT_ALLOWED", "Double extensions and extensionless files are not allowed.")
    if extension not in settings.MESSAGE_ALLOWED_EXTENSIONS or extension not in MIME_BY_EXTENSION:
        raise messaging_error(415, "FILE_TYPE_NOT_ALLOWED", "This attachment type is not allowed.")
    return filename, extension


def _detect_mime(path: Path, extension: str) -> str:
    with path.open("rb") as stream:
        header = stream.read(8192)
    if header.startswith(b"%PDF-"):
        return "application/pdf"
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if header.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if header.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
        if _file_contains(path, ("WordDocument".encode("utf-16le"),)):
            return MIME_BY_EXTENSION["doc"]
        if _file_contains(path, ("PowerPoint Document".encode("utf-16le"),)):
            return MIME_BY_EXTENSION["ppt"]
        if _file_contains(path, ("Workbook".encode("utf-16le"), "Book".encode("utf-16le"))):
            return MIME_BY_EXTENSION["xls"]
        return "application/x-ole-storage"
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            names = set(archive.namelist())
            if any(name.startswith("word/") for name in names):
                return MIME_BY_EXTENSION["docx"]
            if any(name.startswith("ppt/") for name in names):
                return MIME_BY_EXTENSION["pptx"]
            if any(name.startswith("xl/") for name in names):
                return MIME_BY_EXTENSION["xlsx"]
        return "application/zip"
    if b"\x00" not in header:
        try:
            header.decode("utf-8")
            return MIME_BY_EXTENSION[extension] if extension in {"txt", "csv"} else "text/plain"
        except UnicodeDecodeError:
            pass
    return "application/octet-stream"


def _reject_unsafe_document_features(path: Path, extension: str) -> None:
    if extension == "pdf":
        if _file_contains(path, (b"/Encrypt",)):
            raise messaging_error(415, "FILE_TYPE_NOT_ALLOWED", "Password-protected PDF files are not allowed.")
    if extension in {"docx", "pptx", "xlsx"}:
        with zipfile.ZipFile(path) as archive:
            if any(name.lower().endswith("vbaproject.bin") for name in archive.namelist()):
                raise messaging_error(415, "FILE_TYPE_NOT_ALLOWED", "Macro-enabled Office files are not allowed.")
    if extension in {"doc", "ppt", "xls"}:
        if _file_contains(path, (b"V\x00B\x00A\x00", b"_VBA_PROJECT")):
            raise messaging_error(415, "FILE_TYPE_NOT_ALLOWED", "Macro-enabled Office files are not allowed.")


class AntivirusScanner:
    async def scan(self, path: Path) -> bool:
        if settings.MESSAGE_ANTIVIRUS_ENABLED:
            raise messaging_error(503, "FILE_SCAN_FAILED", "Antivirus scanning is enabled but no scanner adapter is configured.")
        return True


async def stream_and_validate_upload(upload: UploadFile, temp_directory: Path, scanner: AntivirusScanner | None = None) -> ValidatedUpload:
    original_filename, extension = sanitize_filename(upload.filename)
    temp_directory.mkdir(parents=True, exist_ok=True)
    temporary_path = temp_directory / f".{uuid4().hex}.upload"
    total_size = 0
    digest = hashlib.sha256()
    try:
        with temporary_path.open("xb") as destination:
            while chunk := await upload.read(CHUNK_SIZE):
                total_size += len(chunk)
                if total_size > settings.MESSAGE_MAX_FILE_SIZE_BYTES:
                    raise messaging_error(
                        413,
                        "FILE_TOO_LARGE",
                        f"The maximum allowed file size is {settings.MESSAGE_MAX_FILE_SIZE_BYTES} bytes.",
                    )
                digest.update(chunk)
                destination.write(chunk)
        if total_size == 0:
            raise unprocessable("FILE_REQUIRED", "The uploaded file is empty.")
        detected_mime = _detect_mime(temporary_path, extension)
        expected_mime = MIME_BY_EXTENSION[extension]
        if detected_mime != expected_mime:
            raise messaging_error(415, "FILE_SIGNATURE_MISMATCH", "The file content does not match its extension.")
        _reject_unsafe_document_features(temporary_path, extension)
        provided_mime = (upload.content_type or "").lower().split(";", 1)[0]
        if provided_mime and provided_mime not in {expected_mime, "application/octet-stream"}:
            raise messaging_error(415, "FILE_SIGNATURE_MISMATCH", "The declared file type does not match its content.")
        if not await (scanner or AntivirusScanner()).scan(temporary_path):
            raise messaging_error(422, "FILE_SCAN_FAILED", "The attachment failed malware scanning.")
        return ValidatedUpload(
            temporary_path=temporary_path,
            original_filename=original_filename,
            extension=extension,
            mime_type=detected_mime,
            file_size=total_size,
            checksum=digest.hexdigest(),
            storage_key=f"{uuid4().hex}.{extension}",
        )
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise
    finally:
        await upload.close()
