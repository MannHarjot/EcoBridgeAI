"""EchoBridge AI — FastAPI application entry point."""

from __future__ import annotations

import logging
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="EchoBridge AI",
    version="1.0.0",
    description=(
        "Real-time communication bridge reducing conversational response time "
        "from 30 seconds to under 3 seconds for people with speech, hearing, "
        "or dual impairments."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


@app.get("/api/health")
async def health() -> dict:
    """Return service status and which third-party integrations are configured.

    Returns:
        A dict with ``status``, ``environment``, ``version``, and a
        ``services`` map showing which API keys are present.
    """
    return {
        "status": "ok",
        "environment": settings.ENVIRONMENT,
        "version": "1.0.0",
        "services": {
            "backboard": bool(settings.BACKBOARD_API_KEY),
            "elevenlabs": bool(settings.ELEVENLABS_API_KEY),
            "google_cloud_speech": bool(settings.GOOGLE_CLOUD_PROJECT_ID),
            "cloudinary": bool(settings.CLOUDINARY_API_KEY),
            "supabase": bool(settings.SUPABASE_URL and settings.SUPABASE_KEY),
            "auth0": bool(settings.AUTH0_DOMAIN),
        },
    }


# ---------------------------------------------------------------------------
# Dev server
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info",
    )
