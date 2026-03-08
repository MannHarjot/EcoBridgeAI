"""Output composer agent — assembles the final PipelineOutput."""

from __future__ import annotations

import logging

from agents.base import BaseAgent
from models.schemas import (
    ConversationContext,
    ImpairmentMode,
    IntentType,
    OutputMode,
    PipelineOutput,
    PredictedReply,
    SessionState,
    TranscriptMessage,
    UrgencyLevel,
)

logger = logging.getLogger(__name__)


def _safe_intent(value: str | None) -> IntentType | None:
    try:
        return IntentType(value.lower()) if value else None
    except ValueError:
        return None


def _safe_urgency(value: str | None) -> UrgencyLevel | None:
    try:
        return UrgencyLevel(value.lower()) if value else None
    except ValueError:
        return None


def _safe_context(value: str | None) -> ConversationContext:
    try:
        return ConversationContext(value.lower()) if value else ConversationContext.UNKNOWN
    except ValueError:
        return ConversationContext.UNKNOWN


class OutputAgent(BaseAgent):
    """Assembles all upstream agent results into a final PipelineOutput.

    Responsibilities:
    - Build a TranscriptMessage from the incoming text and append it to the session
    - Respect ``output_mode`` routing flags from the RouterAgent:
        TEXT_ONLY      → voice_audio_url stays None
        VOICE_ONLY     → simplified_text is still populated (accessibility fallback)
        TEXT_AND_VOICE → both populated when TTS runs
        VISUAL_ONLY    → same as TEXT_AND_VOICE; frontend renders large visual layout
    - Pack predictions, intent, urgency, and emergency flag into the output
    """

    name = "output_composer"
    description = "Packages all pipeline results into a structured PipelineOutput."

    async def process(self, input_data: dict, session: SessionState) -> dict:
        """Compose the final PipelineOutput from accumulated pipeline state.

        Args:
            input_data: Merged outputs from all prior agents.
            session: Live session whose ``messages`` list is mutated.

        Returns:
            Updated dict with a ``pipeline_output`` key containing a
            serialised PipelineOutput.
        """
        raw_text = input_data.get("raw_text") or input_data.get("text_data") or ""
        simplified = input_data.get("simplified_text") or raw_text
        intent = _safe_intent(input_data.get("intent"))
        urgency = _safe_urgency(input_data.get("urgency"))
        output_mode_str: str = input_data.get("output_mode", "TEXT_AND_VOICE")
        mode_str: str = input_data.get("mode", "DUAL_IMPAIRMENT")

        try:
            output_mode = OutputMode(output_mode_str.lower())
        except ValueError:
            output_mode = OutputMode.TEXT_AND_VOICE

        try:
            mode = ImpairmentMode(mode_str.lower())
        except ValueError:
            mode = ImpairmentMode.DUAL_IMPAIRMENT

        # Build and append the transcript message
        transcript: TranscriptMessage | None = None
        if raw_text:
            transcript = TranscriptMessage(
                speaker="other",
                raw_text=raw_text,
                simplified_text=simplified,
                intent=intent,
                urgency=urgency,
                confidence=float(input_data.get("confidence", 1.0)),
                language=input_data.get("language", "en"),
            )
            session.messages.append(transcript)
            logger.debug(
                "Appended message to session %s (total=%d)",
                session.session_id,
                len(session.messages),
            )

        # Respect output_mode — only expose voice URL if a TTS stage produced one
        voice_audio_url: str | None = input_data.get("voice_audio_url")
        if output_mode == OutputMode.TEXT_ONLY:
            voice_audio_url = None

        predictions = [
            PredictedReply(**p) if isinstance(p, dict) else p
            for p in input_data.get("predictions", [])
        ]

        detected_context = _safe_context(input_data.get("detected_context"))
        # Propagate detected context back to session for next turn
        if detected_context != ConversationContext.UNKNOWN:
            session.detected_context = detected_context

        output = PipelineOutput(
            transcript=transcript,
            simplified_text=simplified if raw_text else None,
            intent=intent,
            urgency=urgency,
            predictions=predictions,
            voice_audio_url=voice_audio_url,
            mode=mode,
            output_mode=output_mode,
            detected_context=detected_context,
            emergency_triggered=bool(input_data.get("emergency_triggered", False)),
            prediction_latency_ms=int(input_data.get("prediction_latency_ms", 0)),
            pacing_alert=input_data.get("pacing_alert"),
        )

        input_data["pipeline_output"] = output.model_dump()
        return input_data
