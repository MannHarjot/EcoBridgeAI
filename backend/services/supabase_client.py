"""Supabase persistence layer for sessions, messages, and user preferences."""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class SupabaseClient:
    """Thin async wrapper around the Supabase Python client.

    All methods degrade gracefully to no-ops when no credentials are
    configured, so the rest of the pipeline works without a database.
    """

    def __init__(self, url: str, key: str) -> None:
        self.client = None
        if url and key:
            try:
                from supabase import create_client

                self.client = create_client(url, key)
                logger.info("Supabase client initialised (%s)", url)
            except Exception as exc:
                logger.warning("Failed to initialise Supabase client: %s", exc)

    # ------------------------------------------------------------------
    # Sessions
    # ------------------------------------------------------------------

    async def save_session(self, session_id: str, data: dict) -> bool:
        """Upsert a session record.

        Args:
            session_id: Unique session identifier.
            data: Serialisable session payload.

        Returns:
            True on success, False if no client or on error.
        """
        if not self.client:
            return False
        try:
            self.client.table("sessions").upsert({"id": session_id, **data}).execute()
            return True
        except Exception as exc:
            logger.warning("save_session failed: %s", exc)
            return False

    async def get_session(self, session_id: str) -> Optional[dict]:
        """Fetch a session record by ID.

        Args:
            session_id: The session to retrieve.

        Returns:
            Session dict or None if not found / no client.
        """
        if not self.client:
            return None
        try:
            result = (
                self.client.table("sessions")
                .select("*")
                .eq("id", session_id)
                .single()
                .execute()
            )
            return result.data
        except Exception as exc:
            logger.debug("get_session: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Messages
    # ------------------------------------------------------------------

    async def save_message(self, session_id: str, message: dict) -> bool:
        """Append a transcript message to the session's message log.

        Args:
            session_id: Parent session identifier.
            message: Serialisable TranscriptMessage payload.

        Returns:
            True on success, False otherwise.
        """
        if not self.client:
            return False
        try:
            self.client.table("messages").insert(
                {"session_id": session_id, **message}
            ).execute()
            return True
        except Exception as exc:
            logger.warning("save_message failed: %s", exc)
            return False

    # ------------------------------------------------------------------
    # User preferences
    # ------------------------------------------------------------------

    async def get_user_preferences(self, user_id: str) -> dict:
        """Retrieve persisted preferences for a user.

        Includes voice_id, favourite_phrases, emergency_info, and
        preferred_mode so the pipeline can personalise output on reconnect.

        Args:
            user_id: Authenticated user identifier.

        Returns:
            Preferences dict with keys: voice_id, favourite_phrases,
            emergency_info, preferred_mode.  Empty defaults if not found.
        """
        defaults: dict = {
            "voice_id": "21m00Tcm4TlvDq8ikWAM",
            "favourite_phrases": [],
            "emergency_info": {},
            "preferred_mode": None,
        }
        if not self.client:
            return defaults
        try:
            result = (
                self.client.table("user_preferences")
                .select("*")
                .eq("user_id", user_id)
                .single()
                .execute()
            )
            if result.data:
                return {**defaults, **result.data}
            return defaults
        except Exception as exc:
            logger.debug("get_user_preferences: %s", exc)
            return defaults

    async def save_user_preferences(self, user_id: str, prefs: dict) -> bool:
        """Upsert user preferences.

        Args:
            user_id: Authenticated user identifier.
            prefs: Preference fields to persist.

        Returns:
            True on success, False otherwise.
        """
        if not self.client:
            return False
        try:
            self.client.table("user_preferences").upsert(
                {"user_id": user_id, **prefs}
            ).execute()
            return True
        except Exception as exc:
            logger.warning("save_user_preferences failed: %s", exc)
            return False
