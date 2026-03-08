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
    - Optionally generate TTS audio via ElevenLabs for VOICE_ONLY / TEXT_AND_VOICE modes
    - Build a TranscriptMessage from the incoming text and append it to the session
    - Optionally persist the message to Supabase
    - Pack predictions, intent, urgency, and emergency flag into the output
    """

    name = "output_composer"
    description = "Packages all pipeline results into a structured PipelineOutput."

    def __init__(self, elevenlabs=None, supabase=None) -> None:
        self.elevenlabs = elevenlabs
        self.supabase = supabase

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

        # ── TTS (voice output) ────────────────────────────────────────────────
        voice_audio_url: str | None = input_data.get("voice_audio_url")
        if (
            not voice_audio_url
            and self.elevenlabs
            and output_mode in (OutputMode.VOICE_ONLY, OutputMode.TEXT_AND_VOICE)
            and input_data.get("run_tts")
        ):
            tts_text = simplified or raw_text
            if tts_text:
                try:
                    import base64

                    from config import settings

                    voice_id = input_data.get("voice_id") or settings.ELEVENLABS_VOICE_ID
                    audio_bytes = await self.elevenlabs.text_to_speech(tts_text, voice_id)
                    b64 = base64.b64encode(audio_bytes).decode()
                    voice_audio_url = f"data:audio/mpeg;base64,{b64}"
                    logger.debug("TTS generated %d bytes", len(audio_bytes))
                except Exception as exc:
                    logger.warning("OutputAgent TTS failed: %s", exc)

        # TEXT_ONLY mode — never expose voice URL regardless of TTS result
        if output_mode == OutputMode.TEXT_ONLY:
            voice_audio_url = None

        # ── Build and append transcript message ───────────────────────────────
        transcript: TranscriptMessage | None = None
        if raw_text:
            transcript = TranscriptMessage(
                speaker=input_data.get("speaker", "other"),
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

        # ── Supabase persistence ──────────────────────────────────────────────
        if self.supabase and transcript:
            try:
                await self.supabase.save_message(
                    session.session_id, transcript.model_dump(mode="json")
                )
            except Exception as exc:
                logger.warning("OutputAgent Supabase save failed: %s", exc)

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
