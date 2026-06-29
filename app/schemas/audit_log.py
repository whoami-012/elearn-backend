from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class AuditLogRead(BaseModel):
    id: UUID
    actor_user_id: UUID | None
    action: str
    resource_type: str
    resource_id: str
    old_values: dict[str, Any] | None = None
    new_values: dict[str, Any] | None = None
    metadata_json: dict[str, Any] | None = None
    created_at: datetime

    class Config:
        from_attributes = True
