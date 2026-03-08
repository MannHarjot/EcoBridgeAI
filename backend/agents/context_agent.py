"""Context understanding agent — simplifies text and classifies intent."""

from __future__ import annotations

from agents.base import BaseAgent
from models.schemas import SessionState


class ContextAgent(BaseAgent):
    """Simplifies incoming text and classifies intent and urgency.

    In production this will call Backboard / Claude to:
    - Rewrite complex language into AAC-friendly short sentences
    - Classify intent (question, request, confirmation, …)
    - Assess urgency from semantic content and conversation history
    - Summarise growing context to keep the session context window lean
    """

    name = "context_understanding"
    description = "Simplifies text, classifies intent and urgency for AAC users."

    async def process(self, input_data: dict, session: SessionState) -> dict:
        """Simplify text and classify intent.

        Args:
            input_data: Pipeline state; reads ``normalized_text`` or ``text_data``.
            session: Live session state.

        Returns:
            Updated dict with ``simplified_text``, ``intent``,
            ``urgency``, and ``context_note`` added.
        """
        text = input_data.get("normalized_text") or input_data.get("text_data") or ""
        input_data.update(
            {
                "simplified_text": text,
                "intent": "QUESTION",
                "urgency": "LOW",
                "context_note": "General conversation",
                "detected_context": "UNKNOWN",
                "pacing_alert": None,
            }
        )
        return input_data
