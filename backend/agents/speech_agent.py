"""Speech understanding agent — normalises raw transcribed text."""

from __future__ import annotations

from agents.base import BaseAgent
from models.schemas import SessionState


class SpeechAgent(BaseAgent):
    """Normalises raw speech-to-text output for downstream agents.

    In production this will:
    - Correct STT artefacts and filler words
    - Expand abbreviations common in AAC / augmentative communication
    - Detect language and set the language code for downstream use
    """

    name = "speech_understanding"
    description = "Normalises and enriches raw STT transcripts."

    async def process(self, input_data: dict, session: SessionState) -> dict:
        """Normalise raw transcript text.

        Args:
            input_data: Pipeline state; expects optional ``text_data`` key.
            session: Live session state.

        Returns:
            Updated dict with ``raw_text``, ``normalized_text``,
            ``confidence``, and ``language`` added.
        """
        text = input_data.get("text_data") or ""
        input_data.update(
            {
                "raw_text": text,
                "normalized_text": text,
                "confidence": 1.0,
                "language": "en",
            }
        )
        return input_data
