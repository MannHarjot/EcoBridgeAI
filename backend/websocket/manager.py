"""WebSocket connection and session lifecycle management."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import WebSocket

from models.schemas import ImpairmentMode, OutputMode, SessionState, WebSocketMessage

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages all active WebSocket connections and their associated sessions.

    Sessions outlive individual connections so that a user who briefly
    disconnects (e.g. mobile network hiccup) can resume the same
    conversation without losing context.
    """

    def __init__(self) -> None:
        self.active_connections: dict[str, WebSocket] = {}
        self.session_states: dict[str, SessionState] = {}

    async def connect(self, websocket: WebSocket, session_id: str) -> SessionState:
        """Accept a new WebSocket and restore the session if it already exists.

        Args:
            websocket: The incoming WebSocket connection.
            session_id: Client-supplied session identifier.

        Returns:
            The existing or freshly created SessionState for this session.
        """
        await websocket.accept()
        self.active_connections[session_id] = websocket

        session = self.session_states.get(session_id)
        if session is not None:
            logger.info("Restoring existing session %s", session_id)
            await self.send(
                session_id,
                WebSocketMessage(
                    type="session_restored",
                    payload={
                        "session_id": session_id,
                        "message_count": len(session.messages),
                        "context_summary": session.context_summary,
                    },
                ),
            )
        else:
            session = SessionState(session_id=session_id)
            self.session_states[session_id] = session
            logger.info("Created new session %s", session_id)

        return session

    async def disconnect(self, session_id: str) -> None:
        """Remove the WebSocket but preserve session state for reconnection.

        Args:
            session_id: The session whose connection is being closed.
        """
        self.active_connections.pop(session_id, None)
        logger.info("Connection closed for session %s (state preserved)", session_id)

    async def send(self, session_id: str, message: WebSocketMessage) -> None:
        """Send a JSON-serialised WebSocketMessage to a connected client.

        If the send fails the stale connection is removed automatically.

        Args:
            session_id: Target session identifier.
            message: The message to deliver.
        """
        websocket = self.active_connections.get(session_id)
        if websocket is None:
            logger.debug("No active connection for session %s; message dropped", session_id)
            return

        try:
            await websocket.send_json(message.model_dump())
        except Exception as exc:
            logger.warning("Send failed for session %s (%s); removing connection", session_id, exc)
            self.active_connections.pop(session_id, None)

    def get_or_create_session(
        self,
        session_id: str,
        user_id: Optional[str] = None,
    ) -> SessionState:
        """Return an existing session or create a fresh one.

        Args:
            session_id: Unique identifier for the session.
            user_id: Optional authenticated user identifier.

        Returns:
            The matching or newly created SessionState.
        """
        if session_id not in self.session_states:
            self.session_states[session_id] = SessionState(
                session_id=session_id,
                user_id=user_id,
                mode=ImpairmentMode.DUAL_IMPAIRMENT,
                output_mode=OutputMode.TEXT_AND_VOICE,
            )
        return self.session_states[session_id]
