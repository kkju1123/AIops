"""Business-facing auth repository contracts and records."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

ACCOUNT_KIND_MEMBER = "member"
ACCOUNT_KIND_GUEST = "guest"


@dataclass(frozen=True, slots=True)
class UserRecord:
    id: str
    email: str
    display_name: str
    password_hash: str
    created_at: datetime
    updated_at: datetime
    account_kind: str = "member"

    @property
    def is_guest(self) -> bool:
        return self.account_kind == ACCOUNT_KIND_GUEST


@dataclass(frozen=True, slots=True)
class AuthSessionRecord:
    id: str
    user_id: str
    token_hash: str
    created_at: datetime
    last_seen_at: datetime
    revoked_at: datetime | None


class AuthRepository(Protocol):
    """Repository contract for user authentication."""

    async def create_user(
        self,
        *,
        user_id: str,
        email: str,
        display_name: str,
        password_hash: str,
        created_at: datetime,
        account_kind: str = ACCOUNT_KIND_MEMBER,
    ) -> UserRecord:
        """Create a user."""
        ...

    async def count_users_created_since(self, *, account_kind: str, since: datetime) -> int:
        """Count users of one account kind created at or after `since`."""
        ...

    async def find_user_by_email(self, email: str) -> UserRecord | None:
        """Find a user by normalized email."""
        ...

    async def find_user_by_id(self, user_id: str) -> UserRecord | None:
        """Find a user by id."""
        ...

    async def create_session(
        self,
        *,
        session_id: str,
        user_id: str,
        token_hash: str,
        created_at: datetime,
    ) -> AuthSessionRecord:
        """Create an auth session."""
        ...

    async def find_session_by_token_hash(self, token_hash: str) -> AuthSessionRecord | None:
        """Find an auth session by token hash."""
        ...

    async def touch_session(self, session_id: str, seen_at: datetime) -> AuthSessionRecord | None:
        """Update session last-seen time."""
        ...

    async def revoke_session(
        self,
        session_id: str,
        revoked_at: datetime,
    ) -> AuthSessionRecord | None:
        """Revoke an auth session."""
        ...
