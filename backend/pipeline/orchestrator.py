"""Central pipeline orchestrator that routes inputs through processing stages."""

from __future__ import annotations

import logging
import time
from typing import Optional

from agents.context_agent import ContextAgent
from agents.output_agent import OutputAgent
from agents.prediction_agent import PredictionAgent
from agents.router_agent import RouterAgent
from agents.speech_agent import SpeechAgent
from models.schemas import (
    ConversationContext,
    InputType,
    PipelineInput,
    PipelineOutput,
    PredictedReply,
    PredictionConfidence,
    SessionState,
    UrgencyLevel,
)
from services.backboard import BackboardClient
from services.cloudinary_service import CloudinaryClient
from services.elevenlabs_tts import ElevenLabsClient
from services.google_stt import GoogleSTTClient
from services.supabase_client import SupabaseClient

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """Coordinates the full EchoBridge processing pipeline.

    Pipeline stages (all async, chained via a shared ``input_data`` dict):
        1. Router   — decides which downstream stages are active
        2. STT      — Google Cloud Speech-to-Text (speech_audio path only)
        3. Speech   — text normalisation and language detection
        4. Context  — intent + urgency classification, AAC simplification
        5. Predict  — contextual reply phrase suggestions
        6. Output   — assembles final PipelineOutput, appends to session

    Emergency tap short-circuits the entire pipeline and returns an
    EMERGENCY-flagged PipelineOutput immediately.
    """

    def __init__(
        self,
        router: RouterAgent,
        speech: SpeechAgent,
        context: ContextAgent,
        prediction: PredictionAgent,
        output: OutputAgent,
        elevenlabs: Optional[ElevenLabsClient] = None,
        google_stt: Optional[GoogleSTTClient] = None,
        backboard: Optional[BackboardClient] = None,
        cloudinary: Optional[CloudinaryClient] = None,
        supabase: Optional[SupabaseClient] = None,
    ) -> None:
        self.router = router
        self.speech = speech
        self.context = context
        self.prediction = prediction
        self.output = output
        self.elevenlabs = elevenlabs
        self.google_stt = google_stt
        self.backboard = backboard
        self.cloudinary = cloudinary
        self.supabase = supabase

    async def process(
        self,
        pipeline_input: PipelineInput,
        session: SessionState,
    ) -> PipelineOutput:
        """Process a single user input event and return enriched output.

        Emergency taps bypass all NLP stages and return immediately with
        ``emergency_triggered=True`` and ``urgency=EMERGENCY``.

        Args:
            pipeline_input: Validated input payload from the WebSocket or REST endpoint.
            session: Live session state mutated by the output agent.

        Returns:
            Fully populated PipelineOutput.
        """
        wall_start = time.perf_counter()

        logger.info(
            "Pipeline start — type=%s session=%s",
            pipeline_input.input_type,
            pipeline_input.session_id,
        )

        # ── Emergency short-circuit ──────────────────────────────────────────
        if pipeline_input.input_type == InputType.EMERGENCY_TAP:
            logger.warning("EMERGENCY TAP received for session %s", pipeline_input.session_id)
            return PipelineOutput(
                emergency_triggered=True,
                urgency=UrgencyLevel.EMERGENCY,
                predictions=[],
            )

        # ── Partial speech → streaming prediction path ───────────────────────
        if pipeline_input.input_type == InputType.PARTIAL_SPEECH:
            partial = pipeline_input.partial_transcript or pipeline_input.text_data or ""
            return await self.process_partial(partial, session)

        # ── Seed the shared pipeline state dict ─────────────────────────────
        data: dict = {
            "session_id": pipeline_input.session_id,
            "input_type": pipeline_input.input_type.value,
            "text_data": pipeline_input.text_data or "",
            "audio_data": pipeline_input.audio_data,
            "selected_reply_id": pipeline_input.selected_reply_id,
            "voice_id": pipeline_input.voice_id,
        }

        # ── Stage 1: Router ──────────────────────────────────────────────────
        data = await self.router.run(data, session)

        # ── Stage 2: STT (audio path) ────────────────────────────────────────
        if (
            data.get("run_speech")
            and pipeline_input.input_type == InputType.SPEECH_AUDIO
            and pipeline_input.audio_data
            and self.google_stt
        ):
            import base64

            try:
                audio_bytes = base64.b64decode(pipeline_input.audio_data)
                transcript, confidence = await self.google_stt.transcribe(audio_bytes)
                if transcript:
                    data["text_data"] = transcript
                    data["confidence"] = confidence
                    logger.debug("STT transcript: '%s' (%.2f)", transcript, confidence)
            except Exception as exc:
                logger.warning("STT stage failed: %s", exc)

        # ── Stage 3: Speech normalisation ────────────────────────────────────
        data = await self.speech.run(data, session)

        # ── Stage 4: Context / intent / simplification ───────────────────────
        data = await self.context.run(data, session)

        # ── Stage 5: Reply predictions (timed for latency tracking) ────────
        pred_start = time.perf_counter()
        if data.get("run_predictions"):
            data = await self.prediction.run(data, session)
        data["prediction_latency_ms"] = int((time.perf_counter() - pred_start) * 1000)

        # ── Stage 6: TTS (voice output path) ─────────────────────────────────
        if data.get("run_tts") and self.elevenlabs:
            tts_text = data.get("simplified_text") or data.get("text_data") or ""
            voice_id = (
                pipeline_input.voice_id
                or session.output_mode.value  # fallback — will be a string, not a voice ID
            )
            # Resolve actual voice ID from preferences or config default
            from config import settings

            voice_id = pipeline_input.voice_id or settings.ELEVENLABS_VOICE_ID
            if tts_text:
                try:
                    import base64

                    audio_bytes = await self.elevenlabs.text_to_speech(tts_text, voice_id)
                    # Store as data URI so the client can play directly
                    b64 = base64.b64encode(audio_bytes).decode()
                    data["voice_audio_url"] = f"data:audio/mpeg;base64,{b64}"
                    logger.debug("TTS generated %d bytes for session %s", len(audio_bytes), pipeline_input.session_id)
                except Exception as exc:
                    logger.warning("TTS stage failed: %s", exc)

        # ── Learning stats: record which prediction rank user tapped ────────
        selected_id = pipeline_input.selected_reply_id
        if selected_id:
            predictions = data.get("predictions", [])
            for rank, p in enumerate(predictions):
                pid = p.get("id") if isinstance(p, dict) else getattr(p, "id", None)
                if pid == selected_id:
                    stats = session.learning_stats
                    stats["total_taps"] = stats.get("total_taps", 0) + 1
                    if rank == 0:
                        stats["top_1_taps"] = stats.get("top_1_taps", 0) + 1
                    if rank < 3:
                        stats["top_3_taps"] = stats.get("top_3_taps", 0) + 1
                    if rank < 5:
                        stats["top_5_taps"] = stats.get("top_5_taps", 0) + 1
                    break

        # ── Stage 7: Output assembly ─────────────────────────────────────────
        data = await self.output.run(data, session)

        elapsed = time.perf_counter() - wall_start
        logger.info(
            "Pipeline complete — session=%s total=%.3fs",
            pipeline_input.session_id,
            elapsed,
        )

        raw = data.get("pipeline_output", {})
        return PipelineOutput(**raw) if isinstance(raw, dict) else PipelineOutput()

    async def process_partial(
        self,
        partial_text: str,
        session: SessionState,
    ) -> PipelineOutput:
        """Lightweight streaming path — runs while the other person is still speaking.

        This is the key differentiator: prediction tiles appear and sharpen in
        real-time BEFORE the speaker finishes their sentence.  Skips STT, TTS,
        and full output assembly to stay under 200 ms per call.

        Confidence staging is based on word count so short fragments produce
        ghost tiles that sharpen as more words arrive:
        - < 5 words  → SPECULATIVE (ghost tiles, very low opacity)
        - 5-10 words → LIKELY      (medium opacity, topmost is bold)
        - > 10 words → CONFIDENT   (full opacity, ready to tap immediately)

        Args:
            partial_text: Incomplete transcript received so far.
            session: Live session state for context.

        Returns:
            PipelineOutput with is_partial=True and word-count-staged predictions.
        """
        import uuid as _uuid

        start = time.perf_counter()

        # Stage by word count — feels more natural than character count
        words = partial_text.strip().split()
        word_count = len(words)
        if word_count < 5:
            stage = PredictionConfidence.SPECULATIVE
        elif word_count <= 10:
            stage = PredictionConfidence.LIKELY
        else:
            stage = PredictionConfidence.CONFIDENT

        # Lightweight context hint from the partial (real version calls ContextAgent)
        data = {"text_data": partial_text, "normalized_text": partial_text}
        data = await self.context.run(data, session)
        data["run_predictions"] = True
        data = await self.prediction.run(data, session)

        # Stamp all predictions with the current confidence stage
        raw_preds = data.get("predictions", [])
        predictions = []
        for p in raw_preds:
            if isinstance(p, dict):
                p["prediction_stage"] = stage.value
                predictions.append(PredictedReply(**p))
            else:
                p.prediction_stage = stage
                predictions.append(p)

        latency_ms = int((time.perf_counter() - start) * 1000)
        logger.debug(
            "process_partial: %d words → %s in %dms (session=%s)",
            word_count, stage.value, latency_ms, session.session_id,
        )

        return PipelineOutput(
            is_partial=True,
            predictions=predictions,
            detected_context=session.detected_context,
            prediction_latency_ms=latency_ms,
        )

