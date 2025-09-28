from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Action, ActionType


async def log_action(
    session: AsyncSession,
    *,
    user_id: int,
    action_type: ActionType,
    value: int | None = None,
    meta: dict[str, Any] | None = None,
) -> Action:
    action = Action(user_id=user_id, type=action_type, value=value, meta_json=meta)
    session.add(action)
    return action
