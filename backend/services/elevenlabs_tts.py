"""ElevenLabs text-to-speech service client."""

from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)

_BASE = "https://api.elevenlabs.io"


class ElevenLabsClient:
    """Async HTTP client for the ElevenLabs TTS API.

    Converts text into natural-sounding speech for users with hearing
    impairments who need audio output for others in the conversation.
    """

    def __init__(self, api_key: str, model_id: str = "eleven_multilingual_v2") -> None:
        self._client = httpx.AsyncClient(
            base_url=_BASE,
            headers={"xi-api-key": api_key},
            timeout=30.0,
        )
        self._model_id = model_id

    async def text_to_speech(self, text: str, voice_id: str) -> bytes:
        """Synthesise speech from text using a specified ElevenLabs voice.

        Args:
            text: The text to convert to audio.
            voice_id: ElevenLabs voice identifier.

        Returns:
            Raw MP3 audio bytes.
        """
        response = await self._client.post(
            f"/v1/text-to-speech/{voice_id}",
            headers={"Accept": "audio/mpeg"},
            json={
                "text": text,
                "model_id": self._model_id,
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75,
                },
            },
        )
        response.raise_for_status()
        return response.content

    async def list_voices(self) -> list[dict]:
        """Retrieve all available voices from the ElevenLabs library.

        Returns:
            A list of voice metadata dicts from the API.
        """
        response = await self._client.get("/v1/voices")
        response.raise_for_status()
        return response.json().get("voices", [])

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()
