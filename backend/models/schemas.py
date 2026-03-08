"""Pydantic v2 data models for EchoBridge AI."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ImpairmentMode(str, Enum):
    HEARING_ONLY = "hearing_only"
    SPEECH_ONLY = "speech_only"
    DUAL_IMPAIRMENT = "dual_impairment"


class InputType(str, Enum):
    SPEECH_AUDIO = "speech_audio"
    TEXT_INPUT = "text_input"
    QUICK_TAP = "quick_tap"
    EMERGENCY_TAP = "emergency_tap"
    PARTIAL_SPEECH = "partial_speech"  # streaming — frontend sends partials as heard


class IntentType(str, Enum):
    QUESTION = "question"
    REQUEST = "request"
    CONFIRMATION = "confirmation"
    HELP = "help"
    URGENCY = "urgency"
    SCHEDULING = "scheduling"
    GREETING = "greeting"
    FAREWELL = "farewell"
    INFORMATION = "information"


class UrgencyLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EMERGENCY = "emergency"


class OutputMode(str, Enum):
    TEXT_ONLY = "text_only"
    VOICE_ONLY = "voice_only"
    TEXT_AND_VOICE = "text_and_voice"
    VISUAL_ONLY = "visual_only"


class ConversationContext(str, Enum):
    MEDICAL = "medical"
    RETAIL = "retail"
    EMERGENCY = "emergency"
    CASUAL = "casual"
    PROFESSIONAL = "professional"
    UNKNOWN = "unknown"


class PredictionConfidence(str, Enum):
    SPECULATIVE = "speculative"  # early partial — low opacity tiles
    LIKELY = "likely"            # mid-speech — medium opacity
    CONFIDENT = "confident"      # full utterance — full opacity


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TranscriptMessage(BaseModel):
    """A single turn in the conversation transcript."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    speaker: str  # "user" | "other"
    raw_text: str
    simplified_text: Optional[str] = None
    intent: Optional[IntentType] = None
    urgency: Optional[UrgencyLevel] = None
    confidence: float = 1.0
    language: str = "en"
    timestamp: datetime = Field(default_factory=_utcnow)


class PredictedReply(BaseModel):
    """A suggested reply the user may select."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    text: str
    category: str
    confidence: float = 1.0
    is_favourite: bool = False
    prediction_stage: PredictionConfidence = PredictionConfidence.CONFIDENT


class SessionState(BaseModel):
    """Live state for a single EchoBridge session."""

    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = None
    mode: ImpairmentMode = ImpairmentMode.DUAL_IMPAIRMENT
    output_mode: OutputMode = OutputMode.TEXT_AND_VOICE
    detected_context: ConversationContext = ConversationContext.UNKNOWN
    messages: list[TranscriptMessage] = Field(default_factory=list)
    context_summary: str = ""
    active: bool = True
    created_at: datetime = Field(default_factory=_utcnow)
    learning_stats: dict = Field(
        default_factory=dict
    )  # tracks top-1 / top-5 / custom taps for accuracy


class UserPreferences(BaseModel):
    """Persisted preferences for a returning user."""

    user_id: str
    preferred_mode: Optional[ImpairmentMode] = None
    voice_id: str = "21m00Tcm4TlvDq8ikWAM"
    favourite_phrases: list[dict] = Field(
        default_factory=list
    )  # each dict: {"text": str, "category": str}
    emergency_info: dict = Field(
        default_factory=dict
    )  # name, condition, emergency_contact, allergies
    language: str = "en"


class PipelineInput(BaseModel):
    """Input payload routed to the processing pipeline."""

    session_id: str
    input_type: InputType
    audio_data: Optional[str] = None  # base64-encoded audio
    text_data: Optional[str] = None
    selected_reply_id: Optional[str] = None
    voice_id: Optional[str] = None
    partial_transcript: Optional[str] = None  # streaming: frontend sends partial speech


class PipelineOutput(BaseModel):
    """Fully processed output returned to the client."""

    transcript: Optional[TranscriptMessage] = None
    simplified_text: Optional[str] = None
    intent: Optional[IntentType] = None
    urgency: Optional[UrgencyLevel] = None
    predictions: list[PredictedReply] = Field(default_factory=list)
    voice_audio_url: Optional[str] = None
    mode: ImpairmentMode = ImpairmentMode.DUAL_IMPAIRMENT
    output_mode: OutputMode = OutputMode.TEXT_AND_VOICE
    detected_context: ConversationContext = ConversationContext.UNKNOWN
    emergency_triggered: bool = False
    is_partial: bool = False  # True when this is a streaming update from partial speech
    prediction_latency_ms: int = 0  # tracked and shown during demo
    pacing_alert: Optional[str] = None  # e.g. "The other person is speaking quickly."


class EmergencyPayload(BaseModel):
    """Payload broadcast when an emergency tap is detected."""

    message: str = "I need help. I have a communication disability."
    medical_info: dict = Field(default_factory=dict)
    spoken_audio_url: Optional[str] = None


class RecapCard(BaseModel):
    """End-of-session summary card."""

    session_id: str
    summary: str
    topics: list[str] = Field(default_factory=list)
    action_items: list[str] = Field(default_factory=list)
    duration_seconds: int = 0
    turn_count: int = 0
    prediction_accuracy: float = 0.0  # % of turns where user tapped top-1 prediction
    image_url: Optional[str] = None


class WebSocketMessage(BaseModel):
    """Envelope for all WebSocket messages.

    Valid types: pipeline_result, partial_predictions, transcript_update,
    voice_ready, session_start, session_end, session_restored,
    pacing_alert, context_detected, emergency
    """

    type: str
    payload: dict = Field(default_factory=dict)
