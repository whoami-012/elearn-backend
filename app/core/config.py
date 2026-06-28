import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote_plus


def _csv_setting(name: str, default: str) -> tuple[str, ...]:
    return tuple(
        item.strip().lower().lstrip(".")
        for item in os.getenv(name, default).split(",")
        if item.strip()
    )


def _load_dotenv() -> None:
    current = Path(__file__).resolve()
    candidates = (current.parents[1] / ".env", current.parents[2] / ".env")

    for env_path in candidates:
        if not env_path.exists():
            continue

        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("'\""))
        break


_load_dotenv()


def _default_database_url() -> str:
    database = os.getenv("DB_NAME", "elearndb")
    host = os.getenv("DB_HOST", "127.0.0.1")
    port = os.getenv("DB_PORT", "5432")
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD", "postgres")

    auth = quote_plus(user)
    if password:
        auth = f"{auth}:{quote_plus(password)}"
    auth = f"{auth}@"

    return f"postgresql+asyncpg://{auth}{host}:{port}/{database}"


@dataclass(frozen=True)
class Settings:
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        _default_database_url(),
    )
    JWT_SECRET: str = os.getenv("JWT_SECRET", "your-secret-key")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))   # Fix #8: cast to int
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))        # Fix #5: new setting
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "").strip()
    AGORA_APP_ID: str = os.getenv("AGORA_APP_ID", "")
    AGORA_APP_CERTIFICATE: str = os.getenv("AGORA_APP_CERTIFICATE", "")
    LIVE_CLASS_EARLY_JOIN_MINUTES: int = int(os.getenv("LIVE_CLASS_EARLY_JOIN_MINUTES", "10"))
    LIVE_CLASS_ATTENDANCE_THRESHOLD: float = float(os.getenv("LIVE_CLASS_ATTENDANCE_THRESHOLD", "0.75"))
    LIVE_CLASS_TOKEN_BUFFER_MINUTES: int = int(os.getenv("LIVE_CLASS_TOKEN_BUFFER_MINUTES", "15"))
    MESSAGE_MAX_LENGTH: int = int(os.getenv("MESSAGE_MAX_LENGTH", "2000"))
    MESSAGE_MAX_FILE_SIZE_BYTES: int = int(os.getenv("MESSAGE_MAX_FILE_SIZE_BYTES", "10485760"))
    MESSAGE_MAX_ATTACHMENTS_PER_MESSAGE: int = int(os.getenv("MESSAGE_MAX_ATTACHMENTS_PER_MESSAGE", "1"))
    MESSAGE_ALLOWED_EXTENSIONS: tuple[str, ...] = _csv_setting(
        "MESSAGE_ALLOWED_EXTENSIONS", "pdf,doc,docx,ppt,pptx,xls,xlsx,txt,csv,jpg,jpeg,png"
    )
    MESSAGE_RATE_LIMIT_PER_MINUTE: int = int(os.getenv("MESSAGE_RATE_LIMIT_PER_MINUTE", "30"))
    MESSAGE_CONVERSATION_RATE_LIMIT_PER_MINUTE: int = int(
        os.getenv("MESSAGE_CONVERSATION_RATE_LIMIT_PER_MINUTE", "10")
    )
    MESSAGE_UPLOAD_RATE_LIMIT_PER_10_MINUTES: int = int(
        os.getenv("MESSAGE_UPLOAD_RATE_LIMIT_PER_10_MINUTES", "10")
    )
    MESSAGE_MAX_SEARCH_LENGTH: int = int(os.getenv("MESSAGE_MAX_SEARCH_LENGTH", "100"))
    MESSAGE_STORAGE_BACKEND: str = os.getenv("MESSAGE_STORAGE_BACKEND", "local")
    MESSAGE_LOCAL_STORAGE_PATH: str = os.getenv(
        "MESSAGE_LOCAL_STORAGE_PATH", "./private_uploads/messages"
    )
    MESSAGE_ANTIVIRUS_ENABLED: bool = os.getenv("MESSAGE_ANTIVIRUS_ENABLED", "false").lower() == "true"
    MESSAGE_REDIS_URL: str = os.getenv("MESSAGE_REDIS_URL", "")
    MESSAGE_S3_BUCKET: str = os.getenv("MESSAGE_S3_BUCKET", "")
    MESSAGE_S3_ENDPOINT_URL: str = os.getenv("MESSAGE_S3_ENDPOINT_URL", "")
    MESSAGE_S3_REGION: str = os.getenv("MESSAGE_S3_REGION", "us-east-1")

    def __post_init__(self) -> None:
        positive = {
            "MESSAGE_MAX_LENGTH": self.MESSAGE_MAX_LENGTH,
            "MESSAGE_MAX_FILE_SIZE_BYTES": self.MESSAGE_MAX_FILE_SIZE_BYTES,
            "MESSAGE_MAX_ATTACHMENTS_PER_MESSAGE": self.MESSAGE_MAX_ATTACHMENTS_PER_MESSAGE,
            "MESSAGE_RATE_LIMIT_PER_MINUTE": self.MESSAGE_RATE_LIMIT_PER_MINUTE,
            "MESSAGE_UPLOAD_RATE_LIMIT_PER_10_MINUTES": self.MESSAGE_UPLOAD_RATE_LIMIT_PER_10_MINUTES,
        }
        for name, value in positive.items():
            if value <= 0:
                raise ValueError(f"{name} must be greater than zero")
        if self.MESSAGE_MAX_ATTACHMENTS_PER_MESSAGE != 1:
            raise ValueError("Restricted messaging supports exactly one attachment per message")
        if not self.MESSAGE_ALLOWED_EXTENSIONS:
            raise ValueError("MESSAGE_ALLOWED_EXTENSIONS cannot be empty")
        if self.MESSAGE_STORAGE_BACKEND not in {"local", "s3"}:
            raise ValueError("MESSAGE_STORAGE_BACKEND must be local or s3")
        if self.MESSAGE_STORAGE_BACKEND == "s3" and not self.MESSAGE_S3_BUCKET:
            raise ValueError("MESSAGE_S3_BUCKET is required for S3 storage")


settings = Settings()
