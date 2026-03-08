"""Central pipeline orchestrator that routes inputs through processing stages."""

from __future__ import annotations

import logging
import time
from typing import Optional

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

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """Coordinates the full EchoBridge processing pipeline.

    Pipeline stages (all async, chained via a shared ``input_data`` dict):
        1. Router   — context detection, routing flags
        2. Speech   — STT (audio path), filler removal, pacing detection
        3. Context  — intent + urgency classification, AAC simplification
        4. Predict  — contextual reply phrase suggestions
        5. Output   — TTS (voice path), Supabase persistence, PipelineOutput assembly

    Emergency tap short-circuits the entire pipeline and returns an
    EMERGENCY-flagged PipelineOutput immediately.

    Partial speech events run a lightweight streaming path (no STT/TTS/output
    assembly) to keep round-trip latency under 200 ms.
    """

    def __init__(
        self,
        backboard=None,
        elevenlabs=None,
        google_stt=None,
        supabase=None,
        cloudinary=None,
    ) -> None:
        # Import here to avoid circular-import issues at module load time
        from agents.context_agent import ContextAgent
        from agents.output_agent import OutputAgent
        from agents.prediction_agent import PredictionAgent
        from agents.router_agent import RouterAgent
        from agents.speech_agent import SpeechAgent

        self.router = RouterAgent(backboard=backboard)
        self.speech = SpeechAgent(google_stt=google_stt)
        self.context = ContextAgent(backboard=backboard)
        self.prediction = PredictionAgent(backboard=backboard)
        self.output = OutputAgent(elevenlabs=elevenlabs, supabase=supabase)
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

        # ── Stage 2: Speech (STT + normalisation + pacing) ──────────────────
        data = await self.speech.run(data, session)

        # ── Stage 3: Context / intent / simplification ───────────────────────
        data = await self.context.run(data, session)

        # ── Learning stats: record which prediction rank user tapped ────────
        # Match selected_reply_id against the PREVIOUS turn's predictions stored
        # in session.learning_stats["_last_predictions"]. Must run BEFORE Stage 4
        # so the stored list still refers to the prior turn.
        selected_id = pipeline_input.selected_reply_id
        if selected_id:
            last_preds = session.learning_stats.get("_last_predictions", [])
            for rank, p in enumerate(last_preds):
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

        # ── Stage 4: Reply predictions (timed for latency tracking) ────────
        pred_start = time.perf_counter()
        if data.get("run_predictions"):
            data = await self.prediction.run(data, session)
        data["prediction_latency_ms"] = int((time.perf_counter() - pred_start) * 1000)

        # Persist current predictions so next turn's tap can match against them
        session.learning_stats["_last_predictions"] = data.get("predictions", [])

        # ── Stage 5: Output assembly (TTS + Supabase + PipelineOutput) ──────
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

        detected_context = session.detected_context

        # Use the prediction agent's dedicated partial path for scaled AI calls
        raw_preds = await self.prediction.process_partial(partial_text, detected_context, session)

        # Stamp all predictions with the orchestrator's word-count-based stage
        # (overrides the stage set inside process_partial for consistency)
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
            word_count,
            stage.value,
            latency_ms,
            session.session_id,
        )

        return PipelineOutput(
            is_partial=True,
            predictions=predictions,
            detected_context=detected_context,
            prediction_latency_ms=latency_ms,
        )
