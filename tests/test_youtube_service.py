import pytest
from fastapi import HTTPException

from app.services.youtube_service import normalize_youtube_video_id


def test_normalize_youtube_video_id_accepts_raw_id():
    assert normalize_youtube_video_id("dQw4w9WgXcQ") == "dQw4w9WgXcQ"


def test_normalize_youtube_video_id_extracts_from_url():
    assert (
        normalize_youtube_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        == "dQw4w9WgXcQ"
    )


def test_normalize_youtube_video_id_rejects_invalid_values():
    with pytest.raises(HTTPException) as exc:
        normalize_youtube_video_id("not-a-youtube-id")
    assert exc.value.status_code == 422
