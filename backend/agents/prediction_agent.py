"""Reply prediction agent — surfaces contextual phrase suggestions."""

from __future__ import annotations

import json
import logging
import re
import uuid

from agents.base import BaseAgent
from models.schemas import ConversationContext, PredictedReply, PredictionConfidence, SessionState

logger = logging.getLogger(__name__)

# Context-specific quick replies for fallback / streaming partial path
_CONTEXT_REPLIES: dict[ConversationContext, list[dict]] = {
    ConversationContext.MEDICAL: [
        {"text": "I have pain here", "category": "medical", "confidence": 0.92},
        {"text": "Can you explain that?", "category": "request", "confidence": 0.88},
        {"text": "I need medication", "category": "medical", "confidence": 0.85},
        {"text": "When is my appointment?", "category": "question", "confidence": 0.80},
        {"text": "Yes, I understand", "category": "confirmation", "confidence": 0.78},
        {"text": "I need more time", "category": "request", "confidence": 0.72},
    ],
    ConversationContext.RETAIL: [
        {"text": "How much does this cost?", "category": "question", "confidence": 0.92},
        {"text": "I would like to buy this", "category": "request", "confidence": 0.88},
        {"text": "Do you have this in my size?", "category": "question", "confidence": 0.85},
        {"text": "I need a receipt", "category": "request", "confidence": 0.80},
        {"text": "Can I return this?", "category": "question", "confidence": 0.75},
        {"text": "Thank you", "category": "social", "confidence": 0.70},
    ],
    ConversationContext.EMERGENCY: [
        {"text": "Call 911 now", "category": "emergency", "confidence": 0.98},
        {"text": "I need help immediately", "category": "emergency", "confidence": 0.95},
        {"text": "I am injured", "category": "emergency", "confidence": 0.92},
        {"text": "Please hurry", "category": "emergency", "confidence": 0.90},
        {"text": "I cannot breathe", "category": "emergency", "confidence": 0.88},
        {"text": "Stay with me", "category": "emergency", "confidence": 0.85},
    ],
    ConversationContext.PROFESSIONAL: [
        {"text": "Can we schedule a meeting?", "category": "request", "confidence": 0.90},
        {"text": "I agree with that", "category": "confirmation", "confidence": 0.88},
        {"text": "Can you send me that?", "category": "request", "confidence": 0.85},
        {"text": "I need more information", "category": "request", "confidence": 0.80},
        {"text": "Let me check my schedule", "category": "statement", "confidence": 0.75},
        {"text": "I will follow up", "category": "statement", "confidence": 0.72},
    ],
}

_DEFAULT_REPLIES: list[dict] = [
    {"text": "Yes", "category": "confirmation", "confidence": 0.95},
    {"text": "No", "category": "confirmation", "confidence": 0.90},
    {"text": "Can you repeat that?", "category": "request", "confidence": 0.85},
    {"text": "I need more time", "category": "request", "confidence": 0.75},
    {"text": "I need help", "category": "help", "confidence": 0.70},
    {"text": "Thank you", "category": "social", "confidence": 0.65},
]

_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has", "have",
    "how", "i", "in", "is", "it", "me", "my", "of", "on", "or", "our", "that", "the",
    "this", "to", "we", "what", "when", "where", "who", "why", "with", "you", "your",
}
_GREETING_WORDS = {"hi", "hello", "hey", "goodmorning", "goodafternoon", "goodevening"}

_PREDICTION_PROMPT = """\
You are a communication assistant for someone using AAC (Augmentative and Alternative Communication).
Generate 6 short, natural reply phrases the AAC user might want to say next.

Rules:
- Each phrase must be ≤ 10 words
- Include: 2 context-specific, 2 alternatives, 1 follow-up question, 1 exit/escape phrase
- Return a JSON array of objects with keys: text (string), category (string), confidence (0.0-1.0)
- category must be one of: confirmation, question, request, statement, social, help, emergency
- Return ONLY the JSON array. No markdown, no extra text.

Context: {context}
Intent: {intent}
Urgency: {urgency}
Recent conversation:
{history}
Current message to respond to: {text}"""


def _parse_predictions(response: str) -> list[dict]:
    """Extract a JSON array from Backboard response."""
    cleaned = re.sub(r"```(?:json)?\s*", "", response).strip()
    try:
        result = json.loads(cleaned)
        if isinstance(result, list):
            return result
    except json.JSONDecodeError:
        pass
    match = re.search(r"\[.*\]", cleaned, re.DOTALL)
    if match:
        try:
            result = json.loads(match.group())
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass
    return []


def _make_predictions(raw: list[dict], stage: PredictionConfidence) -> list[dict]:
    return [
        PredictedReply(
            id=str(uuid.uuid4()),
            text=p.get("text", ""),
            category=p.get("category", "statement"),
            confidence=float(p.get("confidence", 0.8)),
            is_favourite=False,
            prediction_stage=stage,
        ).model_dump()
        for p in raw[:6]
        if p.get("text")
    ]


def _clip_words(text: str, limit: int = 10) -> str:
    words = text.split()
    return " ".join(words[:limit]) if len(words) > limit else text


def _topic_from_text(text: str) -> str:
    words = []
    for token in text.lower().split():
        cleaned = re.sub(r"[^a-z0-9']", "", token)
        if not cleaned or cleaned in _STOPWORDS or cleaned.isdigit():
            continue
        words.append(cleaned)
    unique = list(dict.fromkeys(words))
    return " ".join(unique[:2]) if unique else "this"


def _is_greeting(text: str) -> bool:
    compact = re.sub(r"[^a-z]", "", text.lower())
    if compact in _GREETING_WORDS:
        return True
    return bool(re.search(r"\b(hi|hello|hey)\b", text.lower()))


def _local_fallback_predictions(text: str, ctx: ConversationContext) -> list[dict]:
    """Generate dynamic local predictions when Backboard is unavailable."""
    text_l = text.lower()
    topic = _topic_from_text(text)
    greeting = _is_greeting(text)
    is_question = "?" in text or bool(
        re.match(r"^(what|why|how|when|where|who|can|could|would|should|do|does|did|is|are)\b", text_l.strip())
    )

    if greeting:
        raw = [
            {"text": "Hi, I'm good. How are you?", "category": "social", "confidence": 0.95},
            {"text": "Nice to see you", "category": "social", "confidence": 0.90},
            {"text": "I'm doing well, thanks", "category": "social", "confidence": 0.88},
            {"text": "Can you speak a little slower?", "category": "request", "confidence": 0.84},
            {"text": "Could you repeat that once?", "category": "request", "confidence": 0.80},
            {"text": "I need a short break", "category": "help", "confidence": 0.74},
        ]
        return raw

    context_templates: dict[ConversationContext, tuple[str, str]] = {
        ConversationContext.MEDICAL: (
            f"Is {topic} serious?",
            f"I need help with {topic}",
        ),
        ConversationContext.RETAIL: (
            f"What is the price for {topic}?",
            f"Do you have another option for {topic}?",
        ),
        ConversationContext.EMERGENCY: (
            "I need immediate help now",
            f"This is urgent about {topic}",
        ),
        ConversationContext.PROFESSIONAL: (
            f"Can we discuss {topic} next?",
            f"I need details about {topic}",
        ),
        ConversationContext.CASUAL: (
            f"Tell me more about {topic}",
            f"I understand, it is about {topic}",
        ),
        ConversationContext.UNKNOWN: (
            f"Can you explain {topic}?",
            f"I need more details on {topic}",
        ),
    }
    c1, c2 = context_templates.get(ctx, context_templates[ConversationContext.UNKNOWN])

    if topic in {"this", "that"}:
        c1, c2 = (
            "Can you explain that clearly?",
            "I need a bit more detail",
        )

    if is_question:
        alt1, alt2 = "Yes, that works", "No, not right now"
    else:
        alt1, alt2 = "I understand, thank you", "Can you repeat that slowly?"

    raw: list[dict] = [
        {"text": _clip_words(c1), "category": "question", "confidence": 0.90},
        {"text": _clip_words(c2), "category": "request", "confidence": 0.86},
        {"text": _clip_words(alt1), "category": "confirmation", "confidence": 0.82},
        {"text": _clip_words(alt2), "category": "request", "confidence": 0.78},
        {"text": _clip_words(f"What should I do about {topic}?"), "category": "question", "confidence": 0.74},
        {"text": "I need a short break", "category": "help", "confidence": 0.70},
    ]
    # Keep unique phrases and ensure exactly 6 outputs.
    seen: set[str] = set()
    unique_raw = []
    for item in raw:
        t = item["text"].strip()
        if t and t not in seen:
            seen.add(t)
            unique_raw.append(item)
    for item in _DEFAULT_REPLIES:
        if len(unique_raw) >= 6:
            break
        if item["text"] not in seen:
            unique_raw.append(item)
            seen.add(item["text"])
    return unique_raw[:6]


class PredictionAgent(BaseAgent):
    """Predicts the most likely replies the user may want to send.

    Full path: builds a context-rich Backboard prompt and parses 6 ranked
    reply phrases.  Falls back to context-specific hardcoded replies if the
    API call fails or no key is configured.

    Streaming path (``process_partial``): skips the full prompt for very short
    fragments and uses keyword-matched context replies instead, scaling up to a
    short then full Backboard prompt as more words arrive.
    """

    name = "reply_prediction"
    description = "Generates contextual reply predictions for AAC phrase selection."

    def __init__(self, backboard=None) -> None:
        self.backboard = backboard

    async def _ensure_bb_session(self, session: SessionState) -> str | None:
        """Return (and lazily create) the Backboard session ID."""
        if not self.backboard:
            return None
        bb_sid = session.learning_stats.get("_backboard_session_id")
        if not bb_sid:
            bb_sid = await self.backboard.create_session(
                session.user_id or session.session_id
            )
            session.learning_stats["_backboard_session_id"] = bb_sid
        return bb_sid

    async def process(self, input_data: dict, session: SessionState) -> dict:
        """Return a ranked list of predicted replies.

        Args:
            input_data: Pipeline state; reads ``simplified_text``, ``intent``,
                        ``urgency``, and ``detected_context``.
            session: Live session state.

        Returns:
            Updated dict with ``predictions`` key.
        """
        text = input_data.get("simplified_text") or input_data.get("text_data") or ""
        intent = input_data.get("intent", "QUESTION")
        urgency = input_data.get("urgency", "LOW")
        detected_context_str = input_data.get("detected_context", "UNKNOWN")
        try:
            detected_context = ConversationContext(detected_context_str.lower())
        except ValueError:
            detected_context = ConversationContext.UNKNOWN

        raw_preds: list[dict] = []

        if self.backboard and text:
            history_lines = [
                f"- {getattr(msg, 'raw_text', '') or ''}"
                for msg in session.messages[-5:]
                if getattr(msg, "raw_text", None)
            ]
            history = "\n".join(history_lines) if history_lines else "(no prior messages)"

            prompt = _PREDICTION_PROMPT.format(
                context=detected_context_str,
                intent=intent,
                urgency=urgency,
                history=history,
                text=text,
            )
            try:
                bb_sid = await self._ensure_bb_session(session)
                response = await self.backboard.send_message(
                    bb_sid, prompt, agent_name="reply_prediction"
                )
                raw_preds = _parse_predictions(response)
            except Exception as exc:
                logger.warning("PredictionAgent Backboard call failed: %s", exc)

        if not raw_preds:
            raw_preds = _local_fallback_predictions(text, detected_context)

        input_data["predictions"] = _make_predictions(raw_preds, PredictionConfidence.CONFIDENT)
        return input_data

    async def process_partial(
        self,
        partial_text: str,
        detected_context: ConversationContext,
        session: SessionState,
    ) -> list[dict]:
        """Lightweight streaming prediction path.

        Scales depth of AI call by word count so very short fragments return
        instantly while longer fragments get richer predictions:

        - < 4 words  : keyword-matched context replies (no API call)
        - 4-8 words  : short single-turn Backboard prompt
        - 8+ words   : full conversation-history prompt
        """
        words = partial_text.strip().split()
        word_count = len(words)

        # ── Instant path: keyword-matched replies only ────────────────────────
        if word_count < 4 or not self.backboard:
            replies = _CONTEXT_REPLIES.get(detected_context, _DEFAULT_REPLIES)
            return _make_predictions(replies, PredictionConfidence.SPECULATIVE)

        # ── Short prompt path ────────────────────────────────────────────────
        if word_count <= 8:
            prompt = (
                f"Give 6 short AAC reply phrases (≤10 words each) for responding to: \"{partial_text}\"\n"
                f"Context: {detected_context.value}\n"
                "Return ONLY a JSON array: "
                '[{"text":"...","category":"...","confidence":0.0}]'
            )
            stage = PredictionConfidence.LIKELY
        else:
            # ── Full prompt path ─────────────────────────────────────────────
            history_lines = [
                f"- {getattr(msg, 'raw_text', '') or ''}"
                for msg in session.messages[-3:]
                if getattr(msg, "raw_text", None)
            ]
            history = "\n".join(history_lines) or "(no prior messages)"
            prompt = _PREDICTION_PROMPT.format(
                context=detected_context.value,
                intent="QUESTION",
                urgency="LOW",
                history=history,
                text=partial_text,
            )
            stage = PredictionConfidence.CONFIDENT

        raw_preds: list[dict] = []
        try:
            bb_sid = await self._ensure_bb_session(session)
            response = await self.backboard.send_message_fast(
                bb_sid, prompt, agent_name="reply_prediction"
            )
            raw_preds = _parse_predictions(response)
        except Exception as exc:
            logger.warning("PredictionAgent partial Backboard call failed: %s", exc)

        if not raw_preds:
            raw_preds = _local_fallback_predictions(partial_text, detected_context)

        return _make_predictions(raw_preds, stage)
