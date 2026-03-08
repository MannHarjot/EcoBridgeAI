"""EchoBridge AI — FastAPI application entry point."""

from __future__ import annotations

import base64
import logging
from contextlib import asynccontextmanager
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

from config import settings
from models.schemas import (
    EmergencyPayload,
    InputType,
    PipelineInput,
    PipelineOutput,
    RecapCard,
    SessionState,
    UrgencyLevel,
    UserPreferences,
    WebSocketMessage,
)

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Enum fields that may arrive as UPPER_CASE from clients
_ENUM_FIELDS = ("input_type", "mode", "output_mode", "urgency", "intent")


def _normalize_input(raw: dict) -> dict:
    """Lowercase enum fields before Pydantic validation.

    Allows clients to send either ``"TEXT_INPUT"`` or ``"text_input"``.
    """
    return {
        k: (v.lower() if isinstance(v, str) and k in _ENUM_FIELDS else v)
        for k, v in raw.items()
    }


# ---------------------------------------------------------------------------
# Startup / shutdown
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise all service clients and agents on startup."""
    from pipeline.orchestrator import PipelineOrchestrator
    from services.backboard import BackboardClient
    from services.cloudinary_service import CloudinaryClient
    from services.elevenlabs_tts import ElevenLabsClient
    from services.google_stt import GoogleSTTClient
    from services.supabase_client import SupabaseClient
    from websocket.manager import ConnectionManager

    # ── Service clients (None when API keys are absent) ──────────────────────
    elevenlabs = ElevenLabsClient(settings.ELEVENLABS_API_KEY) if settings.ELEVENLABS_API_KEY else None
    google_stt = GoogleSTTClient(settings.GOOGLE_CLOUD_PROJECT_ID, settings.GOOGLE_APPLICATION_CREDENTIALS) if settings.GOOGLE_CLOUD_PROJECT_ID else None
    backboard = BackboardClient(settings.BACKBOARD_API_KEY) if settings.BACKBOARD_API_KEY else None
    cloudinary = (
        CloudinaryClient(
            settings.CLOUDINARY_CLOUD_NAME,
            settings.CLOUDINARY_API_KEY,
            settings.CLOUDINARY_API_SECRET,
        )
        if settings.CLOUDINARY_API_KEY
        else None
    )
    supabase = SupabaseClient(settings.SUPABASE_URL, settings.SUPABASE_KEY)

    # ── Orchestrator (creates agents internally with service deps) ───────────
    orchestrator = PipelineOrchestrator(
        backboard=backboard,
        elevenlabs=elevenlabs,
        google_stt=google_stt,
        supabase=supabase,
        cloudinary=cloudinary,
    )
    ws_manager = ConnectionManager()

    app.state.orchestrator = orchestrator
    app.state.ws_manager = ws_manager
    app.state.supabase = supabase
    app.state.elevenlabs = elevenlabs

    logger.info("EchoBridge AI started (env=%s)", settings.ENVIRONMENT)
    yield

    # ── Cleanup ──────────────────────────────────────────────────────────────
    if backboard:
        await backboard.close()
    if elevenlabs:
        await elevenlabs.close()
    logger.info("EchoBridge AI shutdown complete.")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="EchoBridge AI",
    version="1.0.0",
    description=(
        "Real-time communication bridge reducing conversational response time "
        "from 30 seconds to under 3 seconds for people with speech, hearing, "
        "or dual impairments."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Health
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
# Pipeline
# ---------------------------------------------------------------------------


@app.post("/api/message/process", response_model=PipelineOutput)
async def process_message(body: dict) -> PipelineOutput:
    """Process a user input event through the full pipeline.

    Accepts ``input_type`` in either UPPER_CASE or lower_case form.

    Args:
        body: Raw JSON dict that will be normalised and parsed as PipelineInput.

    Returns:
        Enriched PipelineOutput with transcript, predictions, and optional TTS.
    """
    pipeline_input = PipelineInput(**_normalize_input(body))
    orchestrator: "PipelineOrchestrator" = app.state.orchestrator
    ws_manager: "ConnectionManager" = app.state.ws_manager
    session: SessionState = ws_manager.get_or_create_session(pipeline_input.session_id)
    return await orchestrator.process(pipeline_input, session)


# ---------------------------------------------------------------------------
# TTS on-demand
# ---------------------------------------------------------------------------


class SpeakRequest(BaseModel):
    text: str
    voice_id: str = settings.ELEVENLABS_VOICE_ID


@app.post("/api/reply/speak")
async def speak(request: SpeakRequest) -> Response:
    """Convert arbitrary text to speech via ElevenLabs.

    Used when a user types a custom message and wants it spoken aloud.

    Args:
        request: Text and voice_id to synthesise.

    Returns:
        MP3 audio bytes with media type ``audio/mpeg``.
    """
    elevenlabs = app.state.elevenlabs
    if not elevenlabs:
        raise HTTPException(status_code=503, detail="ElevenLabs TTS not configured")
    audio_bytes = await elevenlabs.text_to_speech(request.text, request.voice_id)
    return Response(content=audio_bytes, media_type="audio/mpeg")


# ---------------------------------------------------------------------------
# Voices
# ---------------------------------------------------------------------------


@app.get("/api/voices")
async def list_voices() -> dict:
    """List available ElevenLabs voices for the voice selector UI.

    Returns:
        Dict with a ``voices`` list, or an empty list when ElevenLabs is not configured.
    """
    elevenlabs = app.state.elevenlabs
    if not elevenlabs:
        return {"voices": []}
    voices = await elevenlabs.list_voices()
    return {"voices": voices}


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------


@app.get("/api/session/{session_id}", response_model=SessionState)
async def get_session(session_id: str) -> SessionState:
    """Retrieve the current state of a session.

    Args:
        session_id: Session to look up.

    Returns:
        The live SessionState for that session.

    Raises:
        HTTPException 404 if the session does not exist.
    """
    ws_manager: "ConnectionManager" = app.state.ws_manager
    session = ws_manager.session_states.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@app.post("/api/session/{session_id}/recap", response_model=RecapCard)
async def session_recap(session_id: str) -> RecapCard:
    """Generate a recap card from session data.

    Args:
        session_id: Session to summarise.

    Returns:
        A RecapCard with basic stats derived from the session messages.

    Raises:
        HTTPException 404 if the session does not exist.
    """
    ws_manager: "ConnectionManager" = app.state.ws_manager
    session = ws_manager.session_states.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    duration = int((now - session.created_at).total_seconds())

    topics = list(
        {m.intent.value for m in session.messages if m.intent} or {"general"}
    )

    stats = session.learning_stats
    total = stats.get("total_taps", 0)
    top1 = stats.get("top_1_taps", 0)
    accuracy = round(top1 / total, 3) if total else 0.0

    return RecapCard(
        session_id=session_id,
        summary=session.context_summary or f"Session with {len(session.messages)} messages.",
        topics=topics,
        action_items=[],
        duration_seconds=duration,
        turn_count=len(session.messages),
        prediction_accuracy=accuracy,
    )


# ---------------------------------------------------------------------------
# User preferences
# ---------------------------------------------------------------------------


@app.get("/api/user/{user_id}/preferences")
async def get_preferences(user_id: str) -> dict:
    """Retrieve stored preferences for a user.

    Args:
        user_id: Authenticated user identifier.

    Returns:
        Dict containing voice_id, favourite_phrases, emergency_info, preferred_mode.
    """
    supabase = app.state.supabase
    return await supabase.get_user_preferences(user_id)


@app.post("/api/user/{user_id}/preferences", response_model=UserPreferences)
async def save_preferences(user_id: str, prefs: UserPreferences) -> UserPreferences:
    """Persist user preferences.

    Args:
        user_id: Authenticated user identifier (must match prefs.user_id).
        prefs: Preferences payload to store.

    Returns:
        The saved UserPreferences.
    """
    if prefs.user_id != user_id:
        raise HTTPException(status_code=400, detail="user_id mismatch")
    supabase = app.state.supabase
    await supabase.save_user_preferences(user_id, prefs.model_dump())
    return prefs


# ---------------------------------------------------------------------------
# Session stats
# ---------------------------------------------------------------------------


@app.get("/api/session/{session_id}/stats")
async def session_stats(session_id: str) -> dict:
    """Return live prediction accuracy and latency stats for a session.

    Useful on the judge demo screen to show the AI improving in real-time.

    Args:
        session_id: Session to inspect.

    Returns:
        Dict with prediction accuracy, tap breakdown, and context info.

    Raises:
        HTTPException 404 if the session does not exist.
    """
    ws_manager: "ConnectionManager" = app.state.ws_manager
    session = ws_manager.session_states.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    stats = session.learning_stats
    total = stats.get("total_taps", 0)
    top1 = stats.get("top_1_taps", 0)
    top3 = stats.get("top_3_taps", 0)
    top5 = stats.get("top_5_taps", 0)

    return {
        "session_id": session_id,
        "total_taps": total,
        "top_1_accuracy": round(top1 / total, 3) if total else 0.0,
        "top_3_accuracy": round(top3 / total, 3) if total else 0.0,
        "top_5_accuracy": round(top5 / total, 3) if total else 0.0,
        "detected_context": session.detected_context.value,
        "message_count": len(session.messages),
        "raw_stats": stats,
    }


# ---------------------------------------------------------------------------
# Emergency
# ---------------------------------------------------------------------------


@app.post("/api/emergency/{session_id}", response_model=EmergencyPayload)
async def trigger_emergency(session_id: str) -> EmergencyPayload:
    """Trigger emergency mode for a session.

    Generates a spoken version of the emergency message via ElevenLabs
    and returns the user's medical / contact info.

    Args:
        session_id: The active session triggering the emergency.

    Returns:
        EmergencyPayload with spoken_audio_url (base64 data URI) and medical_info.
    """
    ws_manager: "ConnectionManager" = app.state.ws_manager
    elevenlabs = app.state.elevenlabs
    supabase = app.state.supabase

    session = ws_manager.session_states.get(session_id)
    emergency_info: dict = {}

    if session and session.user_id:
        prefs = await supabase.get_user_preferences(session.user_id)
        emergency_info = prefs.get("emergency_info", {})

    message = "I need help. I have a communication disability."
    spoken_audio_url: Optional[str] = None

    if elevenlabs:
        try:
            audio_bytes = await elevenlabs.text_to_speech(
                message, settings.ELEVENLABS_VOICE_ID
            )
            b64 = base64.b64encode(audio_bytes).decode()
            spoken_audio_url = f"data:audio/mpeg;base64,{b64}"
        except Exception as exc:
            logger.warning("Emergency TTS failed: %s", exc)

    return EmergencyPayload(
        message=message,
        medical_info=emergency_info,
        spoken_audio_url=spoken_audio_url,
    )


# ---------------------------------------------------------------------------
# WebSocket
# ---------------------------------------------------------------------------


@app.websocket("/ws/session/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str) -> None:
    """Real-time bidirectional communication channel for a session.

    Message flow:
        Client sends PipelineInput JSON → server processes → sends PipelineOutput JSON.
        EMERGENCY_TAP is handled immediately without full pipeline.

    Args:
        websocket: Incoming WebSocket connection.
        session_id: Session identifier embedded in the URL path.
    """
    ws_manager: "ConnectionManager" = app.state.ws_manager
    orchestrator: "PipelineOrchestrator" = app.state.orchestrator

    session = await ws_manager.connect(websocket, session_id)

    await ws_manager.send(
        session_id,
        WebSocketMessage(
            type="session_start",
            payload={"session_id": session_id, "status": "connected"},
        ),
    )

    try:
        while True:
            raw = await websocket.receive_json()
            pipeline_input = PipelineInput(**_normalize_input(raw))

            # ── Emergency short-circuit via WebSocket ──────────────────────
            if pipeline_input.input_type == InputType.EMERGENCY_TAP:
                elevenlabs = app.state.elevenlabs
                supabase = app.state.supabase
                emergency_info: dict = {}

                if session.user_id:
                    prefs = await supabase.get_user_preferences(session.user_id)
                    emergency_info = prefs.get("emergency_info", {})

                message = "I need help. I have a communication disability."
                spoken_audio_url: Optional[str] = None

                if elevenlabs:
                    try:
                        audio_bytes = await elevenlabs.text_to_speech(
                            message, settings.ELEVENLABS_VOICE_ID
                        )
                        b64 = base64.b64encode(audio_bytes).decode()
                        spoken_audio_url = f"data:audio/mpeg;base64,{b64}"
                    except Exception as exc:
                        logger.warning("WS emergency TTS failed: %s", exc)

                await ws_manager.send(
                    session_id,
                    WebSocketMessage(
                        type="emergency_triggered",
                        payload=EmergencyPayload(
                            message=message,
                            medical_info=emergency_info,
                            spoken_audio_url=spoken_audio_url,
                        ).model_dump(mode="json"),
                    ),
                )
                continue

            # ── Streaming partial-speech predictions ───────────────────────
            # orchestrator.process() routes PARTIAL_SPEECH → process_partial internally
            if pipeline_input.input_type == InputType.PARTIAL_SPEECH:
                result = await orchestrator.process(pipeline_input, session)
                await ws_manager.send(
                    session_id,
                    WebSocketMessage(
                        type="partial_predictions",
                        payload={
                            "predictions": [p.model_dump(mode="json") for p in result.predictions],
                            "is_partial": True,
                            "prediction_latency_ms": result.prediction_latency_ms,
                        },
                    ),
                )
                continue

            # ── Normal pipeline ────────────────────────────────────────────
            prev_context = session.detected_context
            result: PipelineOutput = await orchestrator.process(pipeline_input, session)
            await ws_manager.send(
                session_id,
                WebSocketMessage(
                    type="pipeline_result",
                    payload=result.model_dump(mode="json"),
                ),
            )
            # Notify client if context auto-detection changed the domain
            if result.detected_context != prev_context:
                await ws_manager.send_context_detected(session_id, result.detected_context)
            # Pacing alert if the other person is speaking too fast
            if result.pacing_alert:
                await ws_manager.send(
                    session_id,
                    WebSocketMessage(
                        type="pacing_alert",
                        payload={"message": result.pacing_alert},
                    ),
                )

    except WebSocketDisconnect:
        await ws_manager.disconnect(session_id)
        logger.info("WebSocket disconnected: session=%s", session_id)
    except Exception as exc:
        logger.error("WebSocket error session=%s: %s", session_id, exc)
        await ws_manager.disconnect(session_id)


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
