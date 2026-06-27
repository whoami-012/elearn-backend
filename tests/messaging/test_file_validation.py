import pytest
from io import BytesIO
from fastapi import HTTPException
from starlette.datastructures import Headers, UploadFile

from app.messaging.file_validation import sanitize_filename, stream_and_validate_upload


def test_sanitizes_traversal():
    name, extension = sanitize_filename("../../assignment.pdf")
    assert name == "assignment.pdf"
    assert extension == "pdf"


@pytest.mark.parametrize("name", ["assignment.pdf.exe", "script.py", "archive.zip", "noextension"])
def test_rejects_disallowed_names(name):
    with pytest.raises(HTTPException):
        sanitize_filename(name)


@pytest.mark.asyncio
async def test_streams_and_hashes_valid_pdf(tmp_path):
    upload = UploadFile(
        BytesIO(b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF"),
        filename="notes.pdf",
        headers=Headers({"content-type": "application/pdf"}),
    )
    result = await stream_and_validate_upload(upload, tmp_path)
    assert result.file_size > 0
    assert len(result.checksum) == 64
    assert result.mime_type == "application/pdf"
    result.temporary_path.unlink()


@pytest.mark.asyncio
async def test_spoofed_pdf_is_rejected_and_cleaned_up(tmp_path):
    upload = UploadFile(
        BytesIO(b"MZ\x00\x00not a pdf"),
        filename="malware.pdf",
        headers=Headers({"content-type": "application/pdf"}),
    )
    with pytest.raises(HTTPException) as exc:
        await stream_and_validate_upload(upload, tmp_path)
    assert exc.value.detail["code"] == "FILE_SIGNATURE_MISMATCH"
    assert list(tmp_path.iterdir()) == []
