"""Context understanding agent — simplifies text and classifies intent via Backboard."""

from __future__ import annotations

import json
import logging
import re

from agents.base import BaseAgent
from models.schemas import SessionState

logger = logging.getLogger(__name__)

_FALLBACK = {
    "simplified_text": "",
    "intent": "QUESTION",
    "urgency": "LOW",
    "context_note": "General conversation",
    "detected_context": "UNKNOWN",
    "pacing_alert": None,
}

_SYSTEM_PROMPT = """\
You are a communication assistant helping someone with a speech or hearing impairment.

Analyse the conversation and return a JSON object with these exact keys:
{
  "simplified_text": "<rewrite in short, clear sentences of ≤12 words each>",
  "intent": "<one of: QUESTION, REQUEST, CONFIRMATION, GREETING, FAREWELL, STATEMENT, COMPLAINT, EMERGENCY>",
  "urgency": "<one of: LOW, MEDIUM, HIGH, EMERGENCY>",
  "context_note": "<one sentence describing the conversation topic>",
  "detected_context": "<one of: MEDICAL, RETAIL, EMERGENCY, CASUAL, PROFESSIONAL, UNKNOWN>"
}

Return ONLY the JSON object. No markdown fences, no extra text."""


def _parse_json(text: str) -> dict:
    """Extract JSON from response, handling markdown code blocks."""
    cleaned = re.sub(r"```(?:json)?\s*", "", text).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return {}


class ContextAgent(BaseAgent):
    """Simplifies incoming text and classifies intent and urgency.

    When Backboard is configured sends the current message plus up to 3 prior
    turns to Claude via the ``context_understanding`` agent and parses the
    structured JSON response.  Falls back to stub values if the API call fails.
    """

    name = "context_understanding"
    description = "Simplifies text, classifies intent and urgency for AAC users."

    def __init__(self, backboard=None) -> None:
        self.backboard = backboard

    async def process(self, input_data: dict, session: SessionState) -> dict:
        """Simplify text and classify intent/urgency.

        Args:
            input_data: Pipeline state; reads ``normalized_text`` or ``text_data``.
            session: Live session state.

        Returns:
            Updated dict with ``simplified_text``, ``intent``, ``urgency``,
            ``context_note``, ``detected_context``, and ``pacing_alert`` added.
        """
        text = input_data.get("normalized_text") or input_data.get("text_data") or ""

        result = dict(_FALLBACK)
        result["simplified_text"] = text
        # Carry pacing_alert from speech agent if already set
        result["pacing_alert"] = input_data.get("pacing_alert")
        # Preserve context already detected by RouterAgent (don't clobber it)
        upstream_context = input_data.get("detected_context", "UNKNOWN")
        if upstream_context != "UNKNOWN":
            result["detected_context"] = upstream_context

        if not text or not self.backboard:
            input_data.update(result)
            return input_data

        # Build recent history for richer context
        history_lines = []
        for msg in session.messages[-3:]:
            raw = getattr(msg, "raw_text", "") or ""
            if raw:
                history_lines.append(f"- {raw}")
        history = "\n".join(history_lines) if history_lines else "(no prior messages)"

        prompt = (
            f"{_SYSTEM_PROMPT}\n\n"
            f"Current conversation context: {session.detected_context.value}\n\n"
            f"Recent conversation:\n{history}\n\n"
            f"Current message: {text}"
        )

        try:
            bb_sid = session.learning_stats.get("_backboard_session_id")
            if not bb_sid:
                bb_sid = await self.backboard.create_session(
                    session.user_id or session.session_id
                )
                session.learning_stats["_backboard_session_id"] = bb_sid

            response = await self.backboard.send_message(
                bb_sid, prompt, agent_name="context_understanding"
            )
            parsed = _parse_json(response)
            if parsed:
                # Only override fallback keys that Backboard actually returned
                result.update({k: v for k, v in parsed.items() if v})
        except Exception as exc:
            logger.warning("ContextAgent Backboard call failed: %s", exc)

        input_data.update(result)
        return input_data
