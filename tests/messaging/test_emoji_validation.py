import pytest

from fastapi import HTTPException

from app.messaging.emoji_validation import contains_emoji, validate_no_emoji


@pytest.mark.parametrize("value", ["Hello 😀", "🇮🇳", "👩🏽‍💻", "1️⃣", "Family 👨‍👩‍👧", "✈️"])
def test_rejects_emoji_sequences(value):
    assert contains_emoji(value)
    with pytest.raises(HTTPException) as exc:
        validate_no_emoji(value)
    assert exc.value.status_code == 422
    assert exc.value.detail["code"] == "EMOJI_NOT_ALLOWED"


@pytest.mark.parametrize("value", ["café", "مرحبا", "नमस्ते", "你好", "x² + y² = z²"])
def test_allows_non_emoji_unicode(value):
    assert validate_no_emoji(value) == value
