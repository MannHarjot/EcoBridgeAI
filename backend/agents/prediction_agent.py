"""Reply prediction agent — surfaces contextual phrase suggestions."""

from __future__ import annotations

import uuid

from agents.base import BaseAgent
from models.schemas import PredictedReply, SessionState

_DEFAULT_PREDICTIONS: list[dict] = [
    {"text": "Yes", "category": "confirmation", "confidence": 0.95},
    {"text": "No", "category": "confirmation", "confidence": 0.90},
    {"text": "Can you repeat that?", "category": "request", "confidence": 0.85},
    {"text": "I need more time", "category": "request", "confidence": 0.75},
    {"text": "I need help", "category": "help", "confidence": 0.70},
]


class PredictionAgent(BaseAgent):
    """Predicts the most likely replies the user may want to send.

    In production this will:
    - Use conversation context + user's favourite phrases from Supabase
    - Call the Backboard prediction endpoint for contextual suggestions
    - Re-rank predictions by user history and current intent
    """

    name = "reply_prediction"
    description = "Generates contextual reply predictions for AAC phrase selection."

    async def process(self, input_data: dict, session: SessionState) -> dict:
        """Return a ranked list of predicted replies.

        Args:
            input_data: Pipeline state (intent and context used in production).
            session: Live session state.

        Returns:
            Updated dict with ``predictions`` key containing a list of
            ``PredictedReply``-shaped dicts.
        """
        predictions = [
            PredictedReply(
                id=str(uuid.uuid4()),
                text=p["text"],
                category=p["category"],
                confidence=p["confidence"],
                is_favourite=False,
            ).model_dump()
            for p in _DEFAULT_PREDICTIONS
        ]
        input_data["predictions"] = predictions
        return input_data
