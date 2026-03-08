"""EchoBridge AI — FastAPI application entry point."""

from __future__ import annotations

import asyncio
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
    ImpairmentMode,
    InputType,
    OutputMode,
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
    elevenlabs = (
        ElevenLabsClient(
            settings.ELEVENLABS_API_KEY,
            model_id=settings.ELEVENLABS_MODEL_ID,
        )
        if settings.ELEVENLABS_API_KEY
        else None
    )
    google_stt = (
        GoogleSTTClient(settings.GOOGLE_CLOUD_PROJECT_ID, settings.GOOGLE_APPLICATION_CREDENTIALS)
        if settings.GOOGLE_CLOUD_PROJECT_ID and settings.GOOGLE_APPLICATION_CREDENTIALS
        else None
    )
    backboard = (
        BackboardClient(
            settings.BACKBOARD_API_KEY,
            base_url=settings.BACKBOARD_BASE_URL,
        )
        if settings.BACKBOARD_API_KEY
        else None
    )
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
    app.state.backboard = backboard
    app.state.cloudinary = cloudinary

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
    try:
        audio_bytes = await elevenlabs.text_to_speech(request.text, request.voice_id)
    except Exception as exc:
        logger.warning("ElevenLabs TTS request failed: %s", exc)
        raise HTTPException(status_code=502, detail="ElevenLabs TTS request failed")
    return Response(content=audio_bytes, media_type="audio/mpeg")


# ---------------------------------------------------------------------------
# Voices
# ---------------------------------------------------------------------------


@app.get("/api/voices")
async def list_voices() -> dict:
    """List available ElevenLabs voices for the voice selector UI.

    The first 5 voices are marked ``recommended: true`` so the frontend
    can highlight the highest-quality options by default.

    Returns:
        Dict with a ``voices`` list (each entry may include ``recommended``),
        or an empty list when ElevenLabs is not configured.
    """
    elevenlabs = app.state.elevenlabs
    if not elevenlabs:
        return {"voices": []}
    try:
        voices = await elevenlabs.list_voices()
    except Exception as exc:
        logger.warning("ElevenLabs list_voices failed: %s", exc)
        return {
            "voices": [],
            "error": "ElevenLabs key missing 'voices_read' permission or is invalid.",
        }
    # Keep only premade/professional voices; cap to 5
    premade = [v for v in voices if v.get("category") in ("premade", "professional")]
    filtered = premade[:5] if premade else voices[:5]
    for voice in filtered:
        voice["recommended"] = True
    return {"voices": filtered}


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
    """Generate an AI-powered recap card via Backboard.

    When Backboard is configured the full conversation is sent to the
    ``recap_generator`` assistant (claude-3-5-sonnet) which returns a
    structured summary including topics, action items, and a note on how
    effective the predictions were.  Falls back to a stats-only card when
    Backboard is unavailable.

    Args:
        session_id: Session to summarise.

    Returns:
        A RecapCard with AI summary and prediction accuracy stats.

    Raises:
        HTTPException 404 if the session does not exist.
    """
    import json as _json
    from datetime import datetime, timezone

    ws_manager: "ConnectionManager" = app.state.ws_manager
    backboard = app.state.backboard
    cloudinary = getattr(app.state, "cloudinary", None)

    session = ws_manager.session_states.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    now = datetime.now(timezone.utc)
    duration = int((now - session.created_at).total_seconds())
    stats = session.learning_stats
    total_taps = stats.get("total_taps", 0)
    top1_taps = stats.get("top_1_taps", 0)
    accuracy_pct = round((top1_taps / total_taps) * 100) if total_taps else 0
    accuracy = round(top1_taps / total_taps, 3) if total_taps else 0.0

    unique_contexts = list({
        m.intent.value for m in session.messages if m.intent
    } or {"general"})

    # ── Backboard AI summary ──────────────────────────────────────────────────
    summary = session.context_summary or f"Session with {len(session.messages)} messages."
    topics: list[str] = unique_contexts
    action_items: list[str] = []

    if backboard and session.messages:
        conv_lines = [
            f"[{m.speaker}] {m.raw_text}"
            for m in session.messages
        ]
        conversation_text = "\n".join(conv_lines)

        prompt = (
            "Summarize this accessibility communication session.\n\n"
            f"Conversation:\n{conversation_text}\n\n"
            f"Stats: {len(session.messages)} exchanges, "
            f"prediction accuracy {accuracy_pct}%, "
            f"context types detected: {', '.join(unique_contexts)}\n\n"
            "Respond ONLY with this JSON (no markdown, no extra text):\n"
            '{"summary":"2-3 sentences including how effective the AI predictions were",'
            '"topics":["topic1"],'
            '"action_items":["follow-up1"],'
            '"key_moments":["important exchange 1"]}'
        )

        try:
            bb_sid = stats.get("_backboard_session_id")
            if not bb_sid:
                bb_sid = await backboard.create_session(
                    session.user_id or session_id
                )
            response_text = await backboard.send_message(
                bb_sid, prompt, agent_name="recap_generator"
            )
            import re as _re
            cleaned = _re.sub(r"```(?:json)?\s*", "", response_text).strip()
            parsed = _json.loads(cleaned)
            summary = parsed.get("summary", summary)
            topics = parsed.get("topics", topics)
            action_items = parsed.get("action_items", [])
        except Exception as exc:
            logger.warning("Recap Backboard call failed: %s", exc)

    image_url: Optional[str] = None
    if cloudinary:
        try:
            from models.schemas import RecapCard as _RC
            tmp = _RC(
                session_id=session_id,
                summary=summary,
                topics=topics,
                action_items=action_items,
                duration_seconds=duration,
                turn_count=len(session.messages),
                prediction_accuracy=accuracy,
            )
            image_url = await cloudinary.generate_recap_card(tmp)
            logger.info("Cloudinary recap URL generated for session=%s", session_id)
        except Exception as exc:
            logger.warning("Cloudinary recap card failed: %s", exc)
    else:
        logger.info("Cloudinary client unavailable; skipping recap card generation")

    return RecapCard(
        session_id=session_id,
        summary=summary,
        topics=topics,
        action_items=action_items,
        duration_seconds=duration,
        turn_count=len(session.messages),
        prediction_accuracy=accuracy,
        image_url=image_url,
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
    """Return live prediction accuracy and engagement stats for a session.

    Judges can hit this endpoint during Q&A to see real-time AI performance.

    Args:
        session_id: Session to inspect.

    Returns:
        Dict with prediction accuracy, context switches, streaming updates,
        and other engagement metrics.

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

    latency_total = stats.get("_total_latency_ms", 0)
    latency_count = stats.get("_latency_count", 0)

    # Contexts seen: stored by WS handler when context switches occur
    contexts_seen: list[str] = list(stats.get("_contexts_seen", set()))
    if session.detected_context.value not in contexts_seen:
        contexts_seen.append(session.detected_context.value)

    return {
        "total_turns": len(session.messages),
        "prediction_accuracy_top1": round(top1 / total, 3) if total else 0.0,
        "prediction_accuracy_top3": round(top3 / total, 3) if total else 0.0,
        "avg_response_time_ms": round(latency_total / latency_count, 1) if latency_count else 0.0,
        "contexts_detected": contexts_seen,
        "context_switches": stats.get("context_switches", 0),
        "streaming_updates_sent": stats.get("streaming_updates_sent", 0),
        "favourite_phrases_used": stats.get("favourite_phrases_used", 0),
    }


# ---------------------------------------------------------------------------
# Demo preload — warm up Backboard assistants before presenting
# ---------------------------------------------------------------------------


class PreloadRequest(BaseModel):
    scenario: str = "medical"  # "medical" | "retail" | "emergency"


@app.post("/api/demo/preload")
async def demo_preload(body: PreloadRequest) -> dict:
    """Pre-warm all Backboard assistants to eliminate cold-start latency.

    Call this endpoint 30-60 seconds before the demo starts.  Each assistant
    receives a short warm-up message so the first real user interaction is fast.

    Args:
        body: Contains ``scenario`` (medical | retail | emergency) used to
              prime the prediction assistant with relevant context.

    Returns:
        ``{"status": "ready", "assistants_warmed": N}`` where N is the number
        of assistants successfully pre-warmed.
    """
    backboard = app.state.backboard
    if not backboard:
        return {"status": "ready", "assistants_warmed": 0, "note": "Backboard not configured — running in stub mode"}

    # Warm-up messages per assistant
    scenario_hints = {
        "medical": "doctor appointment pain medication",
        "retail": "price buy purchase store",
        "emergency": "help urgent call 911",
    }
    hint = scenario_hints.get(body.scenario, "general communication")

    warm_up_tasks = [
        ("router", f"Route input for {body.scenario} scenario."),
        ("context_understanding", f"Simplify: '{hint}'"),
        ("reply_prediction", f"Suggest replies for an AAC user in a {body.scenario} context."),
        ("reply_prediction_fast", f"Quick replies for: '{hint}'"),
        ("recap_generator", f"Ready to summarise a {body.scenario} session."),
    ]

    warmed = 0
    # Create a throwaway Backboard session for warm-up
    try:
        warm_session_id = await backboard.create_session("_warmup_")
    except Exception as exc:
        logger.warning("Preload: could not create warm-up session: %s", exc)
        return {"status": "degraded", "assistants_warmed": 0, "error": str(exc)}

    for agent_name, message in warm_up_tasks:
        try:
            await backboard.send_message(warm_session_id, message, agent_name=agent_name)
            warmed += 1
            logger.info("[Preload] warmed assistant=%s scenario=%s", agent_name, body.scenario)
        except Exception as exc:
            logger.warning("[Preload] failed to warm assistant=%s: %s", agent_name, exc)

    return {"status": "ready", "assistants_warmed": warmed}


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
# WebSocket helpers
# ---------------------------------------------------------------------------

_logger = logging.getLogger(__name__)


async def _process_and_send(
    orchestrator: "PipelineOrchestrator",
    ws_manager: "ConnectionManager",
    session: SessionState,
    session_id: str,
    pipeline_input: PipelineInput,
) -> None:
    """Run the full pipeline and push the result over WebSocket.

    Runs as an asyncio.create_task so the WS receive loop is not blocked.
    """
    prev_context = session.detected_context
    try:
        result: PipelineOutput = await orchestrator.process(pipeline_input, session)
    except Exception as exc:
        _logger.warning("Pipeline task error session=%s: %s", session_id, exc)
        return

    await ws_manager.send(
        session_id,
        WebSocketMessage(type="pipeline_result", payload=result.model_dump(mode="json")),
    )
    if result.prediction_latency_ms:
        s = session.learning_stats
        s["_total_latency_ms"] = s.get("_total_latency_ms", 0) + result.prediction_latency_ms
        s["_latency_count"] = s.get("_latency_count", 0) + 1
    if result.detected_context != prev_context:
        s = session.learning_stats
        s["context_switches"] = s.get("context_switches", 0) + 1
        contexts: set = s.get("_contexts_seen", set())
        contexts.add(result.detected_context.value)
        s["_contexts_seen"] = contexts
        await ws_manager.send_context_detected(session_id, result.detected_context)
    if result.pacing_alert:
        await ws_manager.send(
            session_id,
            WebSocketMessage(type="pacing_alert", payload={"message": result.pacing_alert}),
        )


async def _process_partial_and_send(
    orchestrator: "PipelineOrchestrator",
    ws_manager: "ConnectionManager",
    session: SessionState,
    session_id: str,
    partial_text: str,
) -> None:
    """Run process_partial and push partial_predictions over WebSocket.

    Drops stale results: if a newer partial has been queued since this task
    started, the result is discarded so the frontend only sees the latest.
    """
    stats = session.learning_stats
    # Record the text we're about to process; if it changes before we finish,
    # another task is processing a newer partial — discard our result.
    stats["_processing_partial"] = partial_text
    try:
        result: PipelineOutput = await orchestrator.process_partial(partial_text, session)
    except Exception as exc:
        _logger.warning("Partial pipeline error session=%s: %s", session_id, exc)
        return

    # Drop if superseded by a newer partial
    if stats.get("_processing_partial") != partial_text:
        return

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
    stats["streaming_updates_sent"] = stats.get("streaming_updates_sent", 0) + 1
    if result.prediction_latency_ms:
        stats["_total_latency_ms"] = stats.get("_total_latency_ms", 0) + result.prediction_latency_ms
        stats["_latency_count"] = stats.get("_latency_count", 0) + 1


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

            # ── Configure: update session modes from user preferences ───────
            if raw.get("type") == "configure":
                raw_mode = str(raw.get("mode", "")).lower()
                raw_output = str(raw.get("output_mode", "")).lower()
                try:
                    session.mode = ImpairmentMode(raw_mode)
                except ValueError:
                    pass
                try:
                    session.output_mode = OutputMode(raw_output)
                except ValueError:
                    pass
                logger.debug(
                    "Session configured: session=%s mode=%s output_mode=%s",
                    session_id, session.mode, session.output_mode,
                )
                continue

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

            # ── Streaming partial-speech predictions (non-blocking) ────────
            if pipeline_input.input_type == InputType.PARTIAL_SPEECH:
                partial_text = pipeline_input.partial_transcript or pipeline_input.text_data or ""
                asyncio.create_task(
                    _process_partial_and_send(orchestrator, ws_manager, session, session_id, partial_text)
                )
                continue

            # ── Normal pipeline (non-blocking) ─────────────────────────────
            # Fire the pipeline as a background task so the receive loop can
            # immediately pick up the next message without waiting 3-5s.
            asyncio.create_task(
                _process_and_send(orchestrator, ws_manager, session, session_id, pipeline_input)
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
