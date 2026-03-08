"""Adaptive router agent — decides which pipeline stages to activate."""

from __future__ import annotations

from agents.base import BaseAgent
from models.schemas import SessionState


class RouterAgent(BaseAgent):
    """Inspects session state and user mode to decide which pipeline stages run.

    In the stub implementation every stage is activated.  The real version
    will read ``session.mode`` and ``session.output_mode`` to skip
    unnecessary stages (e.g. skip TTS for HEARING_ONLY mode).
    """

    name = "adaptive_router"
    description = "Routes input to the appropriate pipeline stages based on impairment mode."

    async def process(self, input_data: dict, session: SessionState) -> dict:
        """Return routing flags for downstream agents.

        Args:
            input_data: Accumulated pipeline state.
            session: Live session (mode, output_mode checked here).

        Returns:
            Updated dict with routing keys added.
        """
        input_data.update(
            {
                "mode": "DUAL_IMPAIRMENT",
                "output_mode": "TEXT_AND_VOICE",
                "detected_context": "UNKNOWN",
                "run_speech": True,
                "run_tts": True,
                "run_predictions": True,
            }
        )
        return input_data
