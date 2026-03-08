"""Backboard AI platform client for EchoBridge AI.

Each pipeline agent gets a dedicated Backboard assistant with a purpose-built
model and system prompt.  Assistants are created lazily on first use and cached
so subsequent calls hit the same fine-tuned context.
"""

from __future__ import annotations

import logging
import time

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://api.backboard.io/v1"

# ---------------------------------------------------------------------------
# Assistant registry — one entry per pipeline role
# ---------------------------------------------------------------------------

ASSISTANTS: dict[str, dict] = {
    "router": {
        "model": "gpt-4o-mini",
        "system_prompt": (
            "You are an accessibility routing assistant for EchoBridge AI. "
            "Analyse the user's impairment mode and conversation context to "
            "determine which pipeline stages should be activated. "
            "Respond concisely with a single JSON object containing routing flags."
        ),
    },
    "context_understanding": {
        "model": "claude-3-5-sonnet-20241022",
        "system_prompt": (
            "You are a communication accessibility specialist for EchoBridge AI. "
            "Your role is to simplify complex language into short, clear sentences "
            "suitable for AAC users (≤12 words each), classify communication intent, "
            "assess urgency, and detect the conversation domain. "
            "Always prioritise clarity and brevity for people with communication impairments. "
            "Return structured JSON only."
        ),
    },
    "reply_prediction": {
        "model": "gpt-4o",
        "system_prompt": (
            "You generate contextual quick-reply phrases for AAC "
            "(Augmentative and Alternative Communication) users. "
            "Create natural, varied responses that fit the conversation context "
            "and the user's likely intent. Balance context-specific phrases with "
            "universal responses. Each phrase must be 10 words or fewer. "
            "Return a JSON array only."
        ),
    },
    "reply_prediction_fast": {
        "model": "gpt-4o-mini",
        "system_prompt": (
            "You generate quick-reply phrases for AAC users. "
            "Speed is critical — respond immediately with the 6 most likely replies. "
            "Each phrase must be 10 words or fewer. "
            "Return ONLY a JSON array: "
            '[{"text":"...","category":"...","confidence":0.0}]. '
            "No explanation, no markdown."
        ),
    },
    "recap_generator": {
        "model": "claude-3-5-sonnet-20241022",
        "system_prompt": (
            "You summarise accessibility communication sessions for EchoBridge AI. "
            "Create concise, meaningful summaries capturing key topics, action items, "
            "and how effectively the AI predictions supported the user. "
            "Focus on practical outcomes and communication effectiveness. "
            "Return structured JSON only."
        ),
    },
    "memory": {
        "model": "gpt-4o-mini",
        "system_prompt": (
            "You manage memory and preferences for AAC users. "
            "Extract and store relevant information about user preferences, "
            "frequent phrases, and communication patterns to improve "
            "future prediction accuracy. Respond with concise JSON."
        ),
    },
}


class BackboardClient:
    """Async HTTP client for the Backboard AI platform.

    Manages per-agent assistant instances, session routing, and memory
    through Backboard's agent orchestration API.

    Each agent role (router, context_understanding, reply_prediction, …) maps
    to a dedicated Backboard assistant with a purpose-specific model and system
    prompt.  Assistants are created on first use via ``ensure_assistant()`` and
    cached for the lifetime of this client.
    """

    def __init__(self, api_key: str) -> None:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        self._client = httpx.AsyncClient(
            base_url=BASE_URL,
            headers=headers,
            timeout=30.0,
        )
        # Separate client with tight timeout for streaming fast-path calls
        self._fast_client = httpx.AsyncClient(
            base_url=BASE_URL,
            headers=headers,
            timeout=httpx.Timeout(connect=5.0, read=2.0, write=2.0, pool=5.0),
        )
        # assistant_name → Backboard assistant_id
        self._assistant_ids: dict[str, str] = {}

    # ── Assistant management ─────────────────────────────────────────────────

    async def ensure_assistant(self, agent_name: str) -> str:
        """Return the Backboard assistant ID for ``agent_name``, creating it if needed.

        The result is cached so every call after the first is a pure dict lookup.

        Args:
            agent_name: Key in the ``ASSISTANTS`` registry.

        Returns:
            Backboard assistant ID string.
        """
        if agent_name in self._assistant_ids:
            return self._assistant_ids[agent_name]

        cfg = ASSISTANTS.get(agent_name, ASSISTANTS["reply_prediction"])
        start = time.perf_counter()

        response = await self._client.post(
            "/assistants",
            json={
                "name": f"echobridge_{agent_name}",
                "model": cfg["model"],
                "system_prompt": cfg["system_prompt"],
            },
        )
        response.raise_for_status()
        assistant_id: str = response.json()["assistant_id"]
        self._assistant_ids[agent_name] = assistant_id

        logger.info(
            "[Backboard] ensure_assistant | agent=%s model=%s | %.3fs | assistant_id=%s",
            agent_name,
            cfg["model"],
            time.perf_counter() - start,
            assistant_id[:12] + "...",
        )
        return assistant_id

    # ── Session ──────────────────────────────────────────────────────────────

    async def create_session(self, user_id: str) -> str:
        """Create a new Backboard session for a user.

        Args:
            user_id: Unique identifier for the user.

        Returns:
            The Backboard-issued session ID string.
        """
        start = time.perf_counter()
        response = await self._client.post(
            "/sessions",
            json={"user_id": user_id},
        )
        response.raise_for_status()
        session_id: str = response.json()["session_id"]
        logger.info(
            "[Backboard] create_session | user=%s | %.3fs | bb_session=%s",
            user_id,
            time.perf_counter() - start,
            session_id[:12] + "...",
        )
        return session_id

    # ── Messaging ────────────────────────────────────────────────────────────

    async def send_message(
        self,
        session_id: str,
        message: str,
        agent_name: str,
    ) -> str:
        """Send a message to a named agent assistant within a session.

        Args:
            session_id: The Backboard session to send into.
            message: The user or system message text.
            agent_name: Which pipeline agent handles this message
                        (key in ``ASSISTANTS``).

        Returns:
            The assistant's response text.
        """
        cfg = ASSISTANTS.get(agent_name, ASSISTANTS["reply_prediction"])
        start = time.perf_counter()

        assistant_id = await self.ensure_assistant(agent_name)
        response = await self._client.post(
            f"/sessions/{session_id}/messages",
            json={
                "message": message,
                "agent": agent_name,
                "assistant_id": assistant_id,
            },
        )
        response.raise_for_status()
        result: str = response.json()["response"]

        elapsed = time.perf_counter() - start
        logger.info(
            "[Backboard] send_message | agent=%s model=%s | %.3fs | response_len=%d chars",
            agent_name,
            cfg["model"],
            elapsed,
            len(result),
        )
        return result

    async def send_message_fast(
        self,
        session_id: str,
        message: str,
        agent_name: str,
    ) -> str:
        """Fast streaming path — uses the ``_fast`` model variant with a 2 s hard cap.

        Used exclusively by the partial-speech streaming prediction path.  If the
        round-trip exceeds 1.5 s the response is discarded and an empty string is
        returned so the caller can fall back to keyword-matched replies instantly.

        Args:
            session_id: The Backboard session to send into.
            message: The partial transcript or short prompt.
            agent_name: Base agent name (``reply_prediction``).  The ``_fast``
                        variant is selected automatically.

        Returns:
            Response string, or ``""`` if the call timed out or was too slow.
        """
        fast_agent = f"{agent_name}_fast" if f"{agent_name}_fast" in ASSISTANTS else agent_name
        cfg = ASSISTANTS.get(fast_agent, ASSISTANTS["reply_prediction_fast"])
        start = time.perf_counter()

        try:
            assistant_id = await self.ensure_assistant(fast_agent)
            response = await self._fast_client.post(
                f"/sessions/{session_id}/messages",
                json={
                    "message": message,
                    "agent": fast_agent,
                    "assistant_id": assistant_id,
                },
            )
            elapsed = time.perf_counter() - start
            response.raise_for_status()
            result: str = response.json()["response"]

            if elapsed > 1.5:
                logger.info(
                    "[Backboard] send_message_fast | agent=%s model=%s | %.3fs | SLOW — discarding, fallback to keywords",
                    fast_agent,
                    cfg["model"],
                    elapsed,
                )
                return ""

            logger.info(
                "[Backboard] send_message_fast | agent=%s model=%s | %.3fs | response_len=%d chars",
                fast_agent,
                cfg["model"],
                elapsed,
                len(result),
            )
            return result

        except httpx.TimeoutException:
            elapsed = time.perf_counter() - start
            logger.info(
                "[Backboard] send_message_fast | agent=%s model=%s | %.3fs | TIMEOUT — fallback to keywords",
                fast_agent,
                cfg["model"],
                elapsed,
            )
            return ""
        except Exception as exc:
            elapsed = time.perf_counter() - start
            logger.warning(
                "[Backboard] send_message_fast | agent=%s | %.3fs | ERROR: %s",
                fast_agent,
                elapsed,
                exc,
            )
            return ""

    # ── Memory ───────────────────────────────────────────────────────────────

    async def recall_memory(self, session_id: str, query: str) -> list[str]:
        """Retrieve relevant memories for a session.

        Args:
            session_id: The session whose memory store to query.
            query: Natural-language query used to retrieve related memories.

        Returns:
            A list of matching memory strings, empty if none found.
        """
        start = time.perf_counter()
        response = await self._client.get(
            f"/sessions/{session_id}/memory",
            params={"query": query},
        )
        response.raise_for_status()
        memories: list[str] = response.json().get("memories", [])

        logger.info(
            "[Backboard] recall_memory | session=%s | %.3fs | query=%r | results=%d",
            session_id[:8] + "...",
            time.perf_counter() - start,
            query[:40] + ("..." if len(query) > 40 else ""),
            len(memories),
        )
        return memories

    async def store_memory(self, session_id: str, key: str, value: str) -> bool:
        """Persist a key-value memory entry for a session.

        Args:
            session_id: The session to attach the memory to.
            key: Memory key / label.
            value: Content to store.

        Returns:
            True on success, False on failure.
        """
        start = time.perf_counter()
        try:
            response = await self._client.post(
                f"/sessions/{session_id}/memory",
                json={"key": key, "value": value},
            )
            response.raise_for_status()
            logger.info(
                "[Backboard] store_memory | session=%s | %.3fs | key=%r | success=True",
                session_id[:8] + "...",
                time.perf_counter() - start,
                key,
            )
            return True
        except httpx.HTTPError as exc:
            logger.warning(
                "[Backboard] store_memory | session=%s | %.3fs | key=%r | success=False | error=%s",
                session_id[:8] + "...",
                time.perf_counter() - start,
                key,
                exc,
            )
            return False

    # ── Lifecycle ────────────────────────────────────────────────────────────

    async def close(self) -> None:
        """Close both underlying HTTP clients."""
        await self._client.aclose()
        await self._fast_client.aclose()
