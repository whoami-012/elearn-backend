import pytest
from fastapi import HTTPException

from app.messaging.content_validation import validate_message_content


def test_normalizes_text():
    assert validate_message_content("  hello\r\nworld  ") == "hello\nworld"


@pytest.mark.parametrize("value,code", [("   ", "MESSAGE_EMPTY"), ("<script>x</script>", "HTML_NOT_ALLOWED"), ("a\x00b", "CONTROL_CHARACTER_NOT_ALLOWED")])
def test_rejects_invalid_content(value, code):
    with pytest.raises(HTTPException) as exc:
        validate_message_content(value)
    assert exc.value.detail["code"] == code
