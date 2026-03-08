"""Backboard AI platform client for EchoBridge AI."""

from __future__ import annotations

import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://api.backboard.io/v1"


class BackboardClient:
    """Async HTTP client for the Backboard AI platform.

    Manages sessions, message routing, and memory recall through
    Backboard's agent orchestration API.
    """

    def __init__(self, api_key: str) -> None:
        self._client = httpx.AsyncClient(
            base_url=BASE_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

    async def create_session(self, user_id: str) -> str:
        """Create a new Backboard session for a user.

        Args:
            user_id: Unique identifier for the user.

        Returns:
            The Backboard-issued session ID string.
        """
        response = await self._client.post(
            "/sessions",
            json={"user_id": user_id},
        )
        response.raise_for_status()
        return response.json()["session_id"]

    async def send_message(
        self,
        session_id: str,
        message: str,
        agent_name: str,
    ) -> str:
        """Send a message to a named agent within a session.

        Args:
            session_id: The Backboard session to send into.
            message: The user or system message text.
            agent_name: Which Backboard agent should handle the message.

        Returns:
            The agent's response text.
        """
        response = await self._client.post(
            f"/sessions/{session_id}/messages",
            json={"message": message, "agent": agent_name},
        )
        response.raise_for_status()
        return response.json()["response"]

    async def recall_memory(self, session_id: str, query: str) -> list[str]:
        """Retrieve relevant memories for a session.

        Args:
            session_id: The session whose memory store to query.
            query: Natural-language query used to retrieve related memories.

        Returns:
            A list of matching memory strings, empty if none found.
        """
        response = await self._client.get(
            f"/sessions/{session_id}/memory",
            params={"query": query},
        )
        response.raise_for_status()
        return response.json().get("memories", [])

    async def store_memory(self, session_id: str, key: str, value: str) -> bool:
        """Persist a key-value memory entry for a session.

        Args:
            session_id: The session to attach the memory to.
            key: Memory key / label.
            value: Content to store.

        Returns:
            True on success, False on failure.
        """
        try:
            response = await self._client.post(
                f"/sessions/{session_id}/memory",
                json={"key": key, "value": value},
            )
            response.raise_for_status()
            return True
        except httpx.HTTPError as exc:
            logger.warning("Failed to store memory: %s", exc)
            return False

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()
