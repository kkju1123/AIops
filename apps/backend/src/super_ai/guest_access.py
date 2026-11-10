"""Ephemeral guest workspace access: settings and quota queries."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, cast

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from super_ai.memory.models import ChatMessageModel
from super_ai.project_config import ProjectConfigurationError, load_project_config


@dataclass(frozen=True, slots=True)
class GuestAccessSettings:
    enabled: bool
    session_ttl_hours: int
    hourly_creation_limit: int
    chat_messages_per_hour: int

    @property
    def session_ttl(self) -> timedelta:
        return timedelta(hours=self.session_ttl_hours)


DISABLED_GUEST_ACCESS_SETTINGS = GuestAccessSettings(
    enabled=False,
    session_ttl_hours=24,
    hourly_creation_limit=0,
    chat_messages_per_hour=0,
)


def load_guest_access_settings(*, config_path: Path | str | None = None) -> GuestAccessSettings:
    """Load the optional `guestAccess` section; a missing section means disabled."""
    raw = load_project_config(config_path).get("guestAccess")
    if raw is None:
        return DISABLED_GUEST_ACCESS_SETTINGS
    if not isinstance(raw, dict):
        raise ProjectConfigurationError("Project config section must be an object: guestAccess")
    section = cast(Mapping[str, Any], raw)
    enabled = section.get("enabled")
    if not isinstance(enabled, bool):
        raise ProjectConfigurationError("Project config field must be a boolean: enabled")
    ttl = _non_negative_int(section, "sessionTtlHours")
    if ttl < 1:
        raise ProjectConfigurationError("guestAccess.sessionTtlHours must be at least 1.")
    return GuestAccessSettings(
        enabled=enabled,
        session_ttl_hours=ttl,
        hourly_creation_limit=_non_negative_int(section, "hourlyCreationLimit"),
        chat_messages_per_hour=_non_negative_int(section, "chatMessagesPerHour"),
    )


async def count_recent_user_messages(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    owner_user_id: str,
    since: datetime,
) -> int:
    """Count chat messages the user sent (role `user`) at or after `since`."""
    stmt = (
        select(func.count())
        .select_from(ChatMessageModel)
        .where(
            ChatMessageModel.owner_user_id == owner_user_id,
            ChatMessageModel.role == "user",
            ChatMessageModel.created_at >= since,
        )
    )
    async with session_factory() as session:
        return int((await session.scalar(stmt)) or 0)


def _non_negative_int(section: Mapping[str, Any], key: str) -> int:
    value = section.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ProjectConfigurationError(f"Project config field must be a non-negative int: {key}")
    return value
