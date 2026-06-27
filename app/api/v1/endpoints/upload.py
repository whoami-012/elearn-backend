"""
api/v1/endpoints/upload.py — Upload endpoints.

Only route-level logic here:
  - Accept the request
  - Delegate to upload_service for business logic
  - Return the response

Business logic lives in app/services/upload_service.py
"""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.upload import UploadResponse
from app.services.upload_service import upload_thumbnail

router = APIRouter(prefix="/upload", tags=["Upload"])


@router.post(
    "/thumbnail",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a course thumbnail image",
    description=(
        "Accepts JPEG, PNG, or WebP. Max size 5 MB. "
        "Requires faculty or admin role. Returns the public URL."
    ),
)
async def upload_course_thumbnail(
    file: UploadFile = File(..., description="Image file (JPEG / PNG / WebP, max 5 MB)"),
    current_user: User = Depends(get_current_user),
):
    """POST /api/v1/upload/thumbnail"""
    if current_user.role not in ("faculty", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only faculty or admin can upload thumbnails.",
        )

    url = await upload_thumbnail(file)
    return UploadResponse(url=url)
