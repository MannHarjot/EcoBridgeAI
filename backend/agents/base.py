"""Abstract base class for all EchoBridge AI agents."""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod

from models.schemas import SessionState

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Contract and timing harness for every pipeline agent.

    Each agent receives a dict of accumulated pipeline state and the live
    SessionState, mutates or extends that dict, and returns it.  The
    ``run()`` wrapper measures wall-clock latency so the orchestrator can
    log end-to-end performance toward the <3 s target.
    """

    name: str
    description: str

    @abstractmethod
    async def process(self, input_data: dict, session: SessionState) -> dict:
        """Execute the agent's core logic.

        Args:
            input_data: Accumulated outputs from prior pipeline stages.
            session: Live session state for context.

        Returns:
            Updated ``input_data`` dict with this agent's results merged in.
        """

    async def run(self, input_data: dict, session: SessionState) -> dict:
        """Time and delegate to ``process()``, then log elapsed time.

        Args:
            input_data: Pipeline state dict passed in from the orchestrator.
            session: Live session state.

        Returns:
            The dict returned by ``process()``.
        """
        start = time.perf_counter()
        result = await self.process(input_data, session)
        elapsed = time.perf_counter() - start
        logger.info("[%s] completed in %.3fs", self.name, elapsed)
        return result
