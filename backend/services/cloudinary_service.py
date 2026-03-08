"""Cloudinary media service for visual communication assets."""

from __future__ import annotations

import logging
import urllib.parse

import cloudinary
import cloudinary.utils

from models.schemas import RecapCard

logger = logging.getLogger(__name__)

# Category → background colour mapping for visual phrase cards
_CATEGORY_COLORS: dict[str, str] = {
    "greeting": "4A90D9",
    "farewell": "7B68EE",
    "confirmation": "27AE60",
    "help": "E74C3C",
    "urgency": "C0392B",
    "request": "F39C12",
    "question": "8E44AD",
    "information": "16A085",
    "scheduling": "2980B9",
    "default": "34495E",
}


class CloudinaryClient:
    """Client for generating visual communication assets via Cloudinary.

    Creates text-overlay images used in dual-impairment mode where visual
    cards supplement or replace text and audio output.
    """

    def __init__(
        self,
        cloud_name: str,
        api_key: str,
        api_secret: str,
    ) -> None:
        cloudinary.config(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret,
            secure=True,
        )
        self._cloud_name = cloud_name

    def _base_url(self) -> str:
        return f"https://res.cloudinary.com/{self._cloud_name}/image/upload"

    async def generate_recap_card(self, recap: RecapCard) -> str:
        """Build a Cloudinary URL for a session recap summary card.

        Uses text overlay transformations to render the session summary,
        top topics, and action items onto a styled background image.

        Args:
            recap: Populated RecapCard for the finished session.

        Returns:
            A fully qualified Cloudinary delivery URL.
        """
        topics_str = " | ".join(recap.topics[:3]) if recap.topics else "General"
        summary_encoded = urllib.parse.quote(recap.summary[:80], safe="")
        topics_encoded = urllib.parse.quote(topics_str, safe="")

        transformations = (
            "w_800,h_400,c_fill,b_rgb:1A1A2E/"
            f"l_text:Arial_28_bold:{summary_encoded},co_rgb:FFFFFF,g_north,y_60,w_720,c_fit/"
            f"l_text:Arial_20:{topics_encoded},co_rgb:A0AEC0,g_south,y_80,w_720,c_fit"
        )

        url = f"{self._base_url()}/{transformations}/echobridge_recap_bg.png"
        logger.debug("Generated recap card URL for session %s", recap.session_id)
        return url

    async def generate_icon_url(self, phrase: str, category: str) -> str:
        """Generate a visual communication icon card for a phrase.

        Creates a large, high-contrast image card for dual-impairment mode
        where visual symbols supplement both text and audio.

        Args:
            phrase: The communication phrase to display.
            category: Semantic category controlling the card's colour scheme.

        Returns:
            A fully qualified Cloudinary delivery URL for the phrase card.
        """
        color = _CATEGORY_COLORS.get(category.lower(), _CATEGORY_COLORS["default"])
        phrase_encoded = urllib.parse.quote(phrase[:40], safe="")
        category_encoded = urllib.parse.quote(category.upper(), safe="")

        transformations = (
            f"w_400,h_400,c_fill,b_rgb:{color}/"
            f"l_text:Arial_48_bold:{phrase_encoded},co_rgb:FFFFFF,g_center,w_360,c_fit/"
            f"l_text:Arial_20:{category_encoded},co_rgb:FFFFFFCC,g_south,y_20"
        )

        url = f"{self._base_url()}/{transformations}/echobridge_icon_bg.png"
        logger.debug("Generated icon URL for phrase '%s' (category=%s)", phrase, category)
        return url
