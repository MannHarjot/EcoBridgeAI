"""Adaptive router agent — decides which pipeline stages to activate."""

from __future__ import annotations

import logging
from typing import Optional

from agents.base import BaseAgent
from models.schemas import ConversationContext, OutputMode, SessionState

logger = logging.getLogger(__name__)

# Keyword sets for automatic context detection
_CONTEXT_KEYWORDS: dict[ConversationContext, set[str]] = {
    ConversationContext.MEDICAL: {
        "pain", "doctor", "nurse", "hospital", "medication", "prescription",
        "appointment", "surgery", "symptom", "symptoms", "diagnose", "diagnosis",
        "treatment", "pharmacy", "medicine", "ill", "sick", "injury", "hurt",
        "blood", "pressure", "heart", "breathe", "breathing", "clinic",
    },
    ConversationContext.RETAIL: {
        "buy", "purchase", "price", "store", "shop", "order", "return", "refund",
        "product", "checkout", "receipt", "sale", "discount", "cost", "pay",
        "payment", "card", "cash", "item", "stock", "aisle", "shelf",
    },
    ConversationContext.EMERGENCY: {
        "emergency", "help", "911", "urgent", "ambulance", "fire", "police",
        "danger", "crash", "accident", "now", "quickly", "serious", "dying",
    },
    ConversationContext.PROFESSIONAL: {
        "meeting", "project", "deadline", "report", "office", "client", "contract",
        "schedule", "presentation", "budget", "email", "conference", "agenda",
        "colleague", "manager", "proposal", "invoice",
    },
}


def _detect_context(messages: list, current_text: str) -> ConversationContext:
    """Score last 5 messages + current text against keyword sets."""
    texts = [current_text.lower()]
    for msg in messages[-5:]:
        raw = getattr(msg, "raw_text", None) or ""
        texts.append(raw.lower())

    scores: dict[ConversationContext, int] = {ctx: 0 for ctx in _CONTEXT_KEYWORDS}
    for text in texts:
        words = set(text.split())
        for ctx, keywords in _CONTEXT_KEYWORDS.items():
            scores[ctx] += len(words & keywords)

    best = max(scores, key=lambda c: scores[c])
    return best if scores[best] >= 1 else ConversationContext.UNKNOWN


class RouterAgent(BaseAgent):
    """Inspects session state and input to decide which pipeline stages run.

    Uses keyword scoring across the last 5 messages to auto-detect conversation
    context (MEDICAL / RETAIL / EMERGENCY / PROFESSIONAL) and sets routing
    flags for downstream agents based on input type and session output mode.
    """

    name = "adaptive_router"
    description = "Routes input to the appropriate pipeline stages based on impairment mode and context."

    def __init__(self, backboard=None) -> None:
        # backboard reserved for future memory-backed context persistence
        self.backboard = backboard

    async def process(self, input_data: dict, session: SessionState) -> dict:
        """Return routing flags and detected context for downstream agents.

        Args:
            input_data: Accumulated pipeline state.
            session: Live session (mode, output_mode, messages checked here).

        Returns:
            Updated dict with routing keys and detected_context added.
        """
        input_type = input_data.get("input_type", "")
        text = input_data.get("text_data", "")

        # Auto-detect context; preserve existing non-UNKNOWN context when
        # keyword scoring returns UNKNOWN (avoids flickering between turns)
        detected = _detect_context(session.messages, text)
        if detected == ConversationContext.UNKNOWN and session.detected_context != ConversationContext.UNKNOWN:
            detected = session.detected_context

        # quick_tap doesn't need prediction (user already picked a phrase)
        run_predictions = input_type != "quick_tap"
        # TTS only when session output mode includes voice
        run_tts = session.output_mode in (OutputMode.VOICE_ONLY, OutputMode.TEXT_AND_VOICE)
        # Speech normalisation runs for all non-emergency, non-partial inputs
        run_speech = input_type in ("speech_audio", "text_input", "quick_tap")

        input_data.update(
            {
                "mode": session.mode.value,
                "output_mode": session.output_mode.value,
                "detected_context": detected.value,
                "run_speech": run_speech,
                "run_tts": run_tts,
                "run_predictions": run_predictions,
            }
        )
        return input_data
