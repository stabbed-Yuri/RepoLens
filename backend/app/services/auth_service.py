from __future__ import annotations


class AuthService:
    """Coordinate Firebase Auth identity data with session ownership."""

    async def attach_owner(self, session_id: str, user_id: str) -> None:
        raise NotImplementedError(
            "Firebase Auth coordination will be implemented in a later slice."
        )

