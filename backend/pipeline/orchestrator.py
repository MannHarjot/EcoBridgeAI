"""Central pipeline orchestrator that routes inputs through processing stages."""

from __future__ import annotations

import logging

from models.schemas import PipelineInput, PipelineOutput

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """Coordinates the full EchoBridge processing pipeline.

    The pipeline is responsible for transforming raw user input (audio,
    text, or tap events) into enriched output containing transcripts,
    intent classification, reply predictions, and optional TTS audio —
    all within the <3 second latency target.

    Stages (to be implemented):
        1. STT  — Google Cloud Speech-to-Text (speech_audio path)
        2. NLP  — intent + urgency classification via Backboard / Claude
        3. Simplification — AAC-friendly language reduction
        4. Reply prediction — contextual phrase suggestions
        5. TTS  — ElevenLabs voice synthesis (hearing-impaired path)
        6. Emergency dispatch — notify caregivers / contacts
    """

    def __init__(self) -> None:
        pass

    async def process(self, pipeline_input: PipelineInput) -> PipelineOutput:
        """Process a single user input event and return enriched output.

        Args:
            pipeline_input: Validated input payload from the WebSocket or
                            REST endpoint.

        Returns:
            A PipelineOutput with all available enrichments populated.
            Returns a safe default when no processing stages are wired up.
        """
        logger.debug(
            "Processing input type=%s session=%s",
            pipeline_input.input_type,
            pipeline_input.session_id,
        )

        # TODO: wire up processing stages
        return PipelineOutput()
