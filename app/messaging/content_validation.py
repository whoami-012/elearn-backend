import re
import unicodedata

from app.core.config import settings
from app.messaging.emoji_validation import validate_no_emoji
from app.messaging.exceptions import unprocessable

_HTML_TAG = re.compile(r"<\s*/?\s*[a-zA-Z][^>]*>")
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def validate_message_content(value: str | None, *, required: bool = True) -> str | None:
    if value is None:
        if required:
            raise unprocessable("MESSAGE_EMPTY", "Message content cannot be empty.")
        return None
    value = unicodedata.normalize("NFC", value.replace("\r\n", "\n").replace("\r", "\n")).strip()
    if not value:
        if required:
            raise unprocessable("MESSAGE_EMPTY", "Message content cannot be empty.")
        return None
    if len(value) > settings.MESSAGE_MAX_LENGTH:
        raise unprocessable("MESSAGE_TOO_LONG", f"Messages may contain at most {settings.MESSAGE_MAX_LENGTH} characters.")
    if _HTML_TAG.search(value):
        raise unprocessable("HTML_NOT_ALLOWED", "HTML is not allowed in messages.")
    if _CONTROL.search(value):
        raise unprocessable("CONTROL_CHARACTER_NOT_ALLOWED", "Message contains an invalid control character.")
    return validate_no_emoji(value)


def validate_search_text(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if len(value) > settings.MESSAGE_MAX_SEARCH_LENGTH:
        raise unprocessable("SEARCH_TOO_LONG", "Search query is too long.")
    return validate_no_emoji(value) if value else None
