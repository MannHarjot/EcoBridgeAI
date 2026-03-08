"""Google Cloud Speech-to-Text service client."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class GoogleSTTClient:
    """Async wrapper around the Google Cloud Speech-to-Text API.

    Transcribes raw audio bytes from users with speech impairments into
    text that can then be routed through the EchoBridge pipeline.
    """

    def __init__(self, project_id: str, credentials_path: str) -> None:
        self._project_id = project_id
        self._credentials_path = credentials_path
        self._client = None
        self._initialised = False

    def _ensure_client(self) -> None:
        """Lazily initialise the Google Speech client on first use."""
        if self._initialised:
            return
        try:
            import os
            from google.cloud import speech

            if self._credentials_path:
                os.environ.setdefault(
                    "GOOGLE_APPLICATION_CREDENTIALS", self._credentials_path
                )
            self._speech = speech
            self._client = speech.SpeechClient()
            self._initialised = True
            logger.info("Google STT client initialised (project=%s)", self._project_id)
        except ImportError:
            logger.warning(
                "google-cloud-speech not installed; STT will return empty strings"
            )
            self._initialised = True

    async def transcribe(
        self,
        audio_bytes: bytes,
        language: str = "en-US",
    ) -> tuple[str, float]:
        """Transcribe audio bytes to text.

        Args:
            audio_bytes: Raw LINEAR16 or FLAC audio data.
            language: BCP-47 language code for the audio.

        Returns:
            A (transcript, confidence) tuple, or ("", 0.0) on failure.
        """
        self._ensure_client()

        if self._client is None:
            return ("", 0.0)

        try:
            audio = self._speech.RecognitionAudio(content=audio_bytes)
            config = self._speech.RecognitionConfig(
                encoding=self._speech.RecognitionConfig.AudioEncoding.LINEAR16,
                language_code=language,
                enable_automatic_punctuation=True,
            )
            # google-cloud-speech is synchronous; run in thread pool in production
            response = self._client.recognize(config=config, audio=audio)

            if not response.results:
                return ("", 0.0)

            best = response.results[0].alternatives[0]
            return (best.transcript, best.confidence)
        except Exception as exc:
            logger.error("STT transcription failed: %s", exc)
            return ("", 0.0)
