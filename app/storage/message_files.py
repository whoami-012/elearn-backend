import asyncio
import os
from abc import ABC, abstractmethod
from pathlib import Path

from app.core.config import settings
from app.messaging.file_validation import ValidatedUpload


class MessageFileStorage(ABC):
    @abstractmethod
    async def persist(self, upload: ValidatedUpload) -> None: ...

    @abstractmethod
    async def delete(self, storage_key: str) -> None: ...

    @abstractmethod
    def local_path(self, storage_key: str) -> Path | None: ...

    def signed_download_url(self, storage_key: str, filename: str, mime_type: str) -> str | None:
        return None


class LocalMessageFileStorage(MessageFileStorage):
    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root or settings.MESSAGE_LOCAL_STORAGE_PATH).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _safe_path(self, storage_key: str) -> Path:
        candidate = (self.root / storage_key).resolve()
        if candidate.parent != self.root:
            raise ValueError("Invalid storage key")
        return candidate

    async def persist(self, upload: ValidatedUpload) -> None:
        os.replace(upload.temporary_path, self._safe_path(upload.storage_key))

    async def delete(self, storage_key: str) -> None:
        self._safe_path(storage_key).unlink(missing_ok=True)

    def local_path(self, storage_key: str) -> Path | None:
        path = self._safe_path(storage_key)
        return path if path.is_file() else None


class S3MessageFileStorage(MessageFileStorage):
    def __init__(self) -> None:
        import boto3

        self.bucket = settings.MESSAGE_S3_BUCKET
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.MESSAGE_S3_ENDPOINT_URL or None,
            region_name=settings.MESSAGE_S3_REGION,
        )

    async def persist(self, upload: ValidatedUpload) -> None:
        try:
            await asyncio.to_thread(
                self.client.upload_file,
                str(upload.temporary_path),
                self.bucket,
                upload.storage_key,
                ExtraArgs={"ContentType": upload.mime_type},
            )
        finally:
            upload.temporary_path.unlink(missing_ok=True)

    async def delete(self, storage_key: str) -> None:
        await asyncio.to_thread(self.client.delete_object, Bucket=self.bucket, Key=storage_key)

    def local_path(self, storage_key: str) -> Path | None:
        return None

    def signed_download_url(self, storage_key: str, filename: str, mime_type: str) -> str | None:
        safe_name = filename.replace('"', "_").replace("\r", "_").replace("\n", "_")
        return self.client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": self.bucket,
                "Key": storage_key,
                "ResponseContentType": mime_type,
                "ResponseContentDisposition": f'attachment; filename="{safe_name}"',
            },
            ExpiresIn=300,
        )


def get_message_storage() -> MessageFileStorage:
    if settings.MESSAGE_STORAGE_BACKEND == "s3":
        return S3MessageFileStorage()
    return LocalMessageFileStorage()
