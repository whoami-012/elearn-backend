from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app.models.user import User
from app.services.user_service import _ensure_can_change_admin_state


@pytest.mark.asyncio
async def test_last_active_admin_cannot_be_demoted():
    db = AsyncMock()
    target = User(name="Admin", email="admin@test.com", role="admin", is_active=True, is_deleted=False)
    actor = User(name="Other Admin", email="other@test.com", role="admin", is_active=True, is_deleted=False)
    target.id = "target"
    actor.id = "actor"

    with patch("app.services.user_service._active_admin_count", new=AsyncMock(return_value=1)):
        with pytest.raises(HTTPException) as exc:
            await _ensure_can_change_admin_state(db, target, actor, new_role="student")

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_admin_cannot_deactivate_self():
    db = AsyncMock()
    actor = User(name="Admin", email="admin@test.com", role="admin", is_active=True, is_deleted=False)
    actor.id = "same"

    with pytest.raises(HTTPException) as exc:
        await _ensure_can_change_admin_state(db, actor, actor, new_is_active=False)

    assert exc.value.status_code == 400
