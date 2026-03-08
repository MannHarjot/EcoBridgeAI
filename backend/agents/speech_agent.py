"""Speech understanding agent — transcribes audio, normalises text, detects pacing."""

from __future__ import annotations

import logging
import re
from typing import Optional

from agents.base import BaseAgent
from models.schemas import SessionState

logger = logging.getLogger(__name__)

# Filler words removed from transcripts before downstream NLP
_FILLERS = re.compile(
    r"\b(um+|uh+|er+|ah+|like|you know|basically|literally|actually|sort of|kind of|right)\b",
    re.IGNORECASE,
)

# WPM threshold that triggers a pacing alert to the other person
_FAST_SPEECH_WPM = 180

# Google STT outputs 16 kHz mono 16-bit LINEAR16 PCM → 32 000 bytes / second
_BYTES_PER_SECOND = 32_000


class SpeechAgent(BaseAgent):
    """Handles STT (if audio provided), normalises text, and detects pacing.

    Pipeline responsibilities:
    - Decode base64 audio and call Google STT when input_type == SPEECH_AUDIO
    - Strip filler words (um, uh, like, …) from the transcript
    - Estimate words-per-minute from audio duration and flag fast speech
    """

    name = "speech_understanding"
    description = "Transcribes audio, normalises text, and detects fast-paced speech."

    def __init__(self, google_stt=None) -> None:
        self.google_stt = google_stt

    async def process(self, input_data: dict, session: SessionState) -> dict:
        """Transcribe, normalise, and optionally detect fast pacing.

        Args:
            input_data: Pipeline state; reads ``text_data``, ``audio_data``,
                        ``input_type``, and ``run_speech``.
            session: Live session state.

        Returns:
            Updated dict with ``raw_text``, ``normalized_text``, ``confidence``,
            ``language``, and optionally ``pacing_alert`` added.
        """
        text = input_data.get("text_data") or ""
        confidence = float(input_data.get("confidence", 1.0))
        pacing_alert: str | None = None

        # ── STT (audio path) ─────────────────────────────────────────────────
        audio_data = input_data.get("audio_data")
        if (
            self.google_stt
            and audio_data
            and input_data.get("run_speech")
            and input_data.get("input_type") == "speech_audio"
        ):
            try:
                import base64

                audio_bytes = base64.b64decode(audio_data)
                transcript, stt_confidence = await self.google_stt.transcribe(audio_bytes)
                if transcript:
                    text = transcript
                    confidence = stt_confidence
                    logger.debug("STT: '%s' (%.2f)", text, confidence)

                    # Pacing detection: WPM from byte-length → estimated duration
                    if len(audio_bytes) > 0:
                        duration_secs = len(audio_bytes) / _BYTES_PER_SECOND
                        word_count = len(transcript.split())
                        if duration_secs > 0:
                            wpm = (word_count / duration_secs) * 60
                            if wpm > _FAST_SPEECH_WPM:
                                pacing_alert = (
                                    f"Speaking pace is fast ({int(wpm)} WPM). "
                                    "Slow down for better communication."
                                )
                                logger.info("Pacing alert triggered: %.0f WPM", wpm)
            except Exception as exc:
                logger.warning("SpeechAgent STT failed: %s", exc)

        # ── Text normalisation ────────────────────────────────────────────────
        normalized = _FILLERS.sub("", text).strip()
        # Collapse multiple spaces left by filler removal
        normalized = re.sub(r"\s{2,}", " ", normalized)

        input_data.update(
            {
                "raw_text": text,
                "normalized_text": normalized,
                "confidence": confidence,
                "language": input_data.get("language", "en"),
                "pacing_alert": pacing_alert,
            }
        )
        return input_data
