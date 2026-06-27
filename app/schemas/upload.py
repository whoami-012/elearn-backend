"""
schemas/upload.py — Pydantic schema for upload responses.
"""

from pydantic import BaseModel


class UploadResponse(BaseModel):
    url: str
