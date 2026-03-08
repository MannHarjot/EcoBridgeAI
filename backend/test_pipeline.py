#!/usr/bin/env python3
"""EchoBridge AI — pipeline smoke test / hackathon demo.

Run from the backend/ directory:
    python test_pipeline.py

Demonstrates:
  1. Streaming refinement: SPECULATIVE → LIKELY → CONFIDENT
  2. Context detection switching (casual → medical)
  3. Learning stats (reply tap tracking)
  4. Emergency short-circuit
"""

from __future__ import annotations

import asyncio
import os
import sys
import time

# Ensure backend/ is on the path when run directly
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv

load_dotenv()

from config import settings
from models.schemas import (
    ImpairmentMode,
    InputType,
    OutputMode,
    PipelineInput,
    SessionState,
)
from pipeline.orchestrator import PipelineOrchestrator
from services.backboard import BackboardClient
from services.elevenlabs_tts import ElevenLabsClient
from services.google_stt import GoogleSTTClient
from services.supabase_client import SupabaseClient


# ── Helpers ───────────────────────────────────────────────────────────────────

def _sep(title: str = "") -> None:
    print(f"\n{'=' * 60}")
    if title:
        print(f"  {title}")
        print("=" * 60)


def _show_output(output, label: str = "") -> None:
    if label:
        print(f"\n  [{label}]")
    print(f"  Predictions ({len(output.predictions)}):")
    for i, p in enumerate(output.predictions[:4]):
        stage = getattr(p, "prediction_stage", "?")
        stage_val = stage.value if hasattr(stage, "value") else str(stage)
        print(f"    {i + 1}. [{stage_val:12s}] {p.text!r} ({p.confidence:.0%})")
    if output.simplified_text:
        print(f"  Simplified : {output.simplified_text!r}")
    if output.intent:
        intent_val = output.intent.value if hasattr(output.intent, "value") else str(output.intent)
        print(f"  Intent     : {intent_val}")
    if output.detected_context:
        ctx_val = output.detected_context.value if hasattr(output.detected_context, "value") else str(output.detected_context)
        print(f"  Context    : {ctx_val}")
    if output.pacing_alert:
        print(f"  ⚡ Pacing  : {output.pacing_alert}")
    print(f"  Latency    : {output.prediction_latency_ms} ms")


# ── Main ──────────────────────────────────────────────────────────────────────

async def main() -> None:
    print("\n  EchoBridge AI — Pipeline Test")
    print("  Reducing response time from 30 s → < 3 s")

    # ── Init services (all degrade gracefully when keys are absent) ───────────
    backboard = BackboardClient(settings.BACKBOARD_API_KEY) if settings.BACKBOARD_API_KEY else None
    elevenlabs = ElevenLabsClient(settings.ELEVENLABS_API_KEY) if settings.ELEVENLABS_API_KEY else None
    google_stt = (
        GoogleSTTClient(settings.GOOGLE_CLOUD_PROJECT_ID, settings.GOOGLE_APPLICATION_CREDENTIALS)
        if settings.GOOGLE_CLOUD_PROJECT_ID
        else None
    )
    supabase = SupabaseClient(settings.SUPABASE_URL, settings.SUPABASE_KEY)

    ai_mode = bool(backboard)
    print(f"\n  Mode: {'AI (Backboard connected)' if ai_mode else 'Stub (no API keys — using hardcoded fallbacks)'}")

    orchestrator = PipelineOrchestrator(
        backboard=backboard,
        elevenlabs=elevenlabs,
        google_stt=google_stt,
        supabase=supabase,
    )

    # Use TEXT_ONLY so TTS doesn't slow the demo when ElevenLabs key is absent
    session = SessionState(
        user_id="demo_user",
        mode=ImpairmentMode.DUAL_IMPAIRMENT,
        output_mode=OutputMode.TEXT_ONLY,
    )

    # ── TEST 1: Streaming refinement ─────────────────────────────────────────
    _sep("TEST 1 — Streaming Refinement  (SPECULATIVE → LIKELY → CONFIDENT)")
    print("  Simulating the other person speaking word-by-word:\n")

    partials = [
        "Can",                                              # 1  → SPECULATIVE
        "Can you",                                          # 2  → SPECULATIVE
        "Can you help",                                     # 3  → SPECULATIVE
        "Can you help me",                                  # 4  → SPECULATIVE
        "Can you help me find",                             # 5  → LIKELY
        "Can you help me find the",                         # 6  → LIKELY
        "Can you help me find the doctor",                  # 7  → LIKELY
        "Can you help me find the doctor I need",           # 9  → LIKELY
        "Can you help me find the doctor I need to see",    # 11 → CONFIDENT
    ]

    for partial in partials:
        inp = PipelineInput(
            session_id=session.session_id,
            input_type=InputType.PARTIAL_SPEECH,
            partial_transcript=partial,
        )
        out = await orchestrator.process(inp, session)
        n_words = len(partial.split())
        stage = out.predictions[0].prediction_stage if out.predictions else "?"
        stage_val = stage.value if hasattr(stage, "value") else str(stage)
        top = out.predictions[0].text if out.predictions else "none"
        print(f"  [{n_words:2d} words] {stage_val:12s} | Top: {top!r}  ({out.prediction_latency_ms} ms)")

    # ── TEST 2: Context detection ─────────────────────────────────────────────
    _sep("TEST 2 — Context Detection  (casual → medical)")

    casual_inp = PipelineInput(
        session_id=session.session_id,
        input_type=InputType.TEXT_INPUT,
        text_data="How are you doing today?",
    )
    casual_out = await orchestrator.process(casual_inp, session)
    _show_output(casual_out, "Casual message")

    medical_inp = PipelineInput(
        session_id=session.session_id,
        input_type=InputType.TEXT_INPUT,
        text_data="I have chest pain and need to see a doctor urgently",
    )
    medical_out = await orchestrator.process(medical_inp, session)
    _show_output(medical_out, "Medical message")

    c1 = casual_out.detected_context.value if hasattr(casual_out.detected_context, "value") else str(casual_out.detected_context)
    c2 = medical_out.detected_context.value if hasattr(medical_out.detected_context, "value") else str(medical_out.detected_context)
    print(f"\n  Context switch: {c1} → {c2}")

    # ── TEST 3: Learning stats ────────────────────────────────────────────────
    _sep("TEST 3 — Learning Stats  (tap tracking)")

    pred_inp = PipelineInput(
        session_id=session.session_id,
        input_type=InputType.TEXT_INPUT,
        text_data="What time is my appointment?",
    )
    pred_out = await orchestrator.process(pred_inp, session)

    if pred_out.predictions:
        top_pred = pred_out.predictions[0]
        print(f"  Got {len(pred_out.predictions)} predictions. Top: {top_pred.text!r}")
        print(f"  User taps the top prediction (id={top_pred.id[:8]}...)")

        # The tap arrives with the NEXT message the user initiates.
        # selected_reply_id matches against _last_predictions stored in the session.
        followup_inp = PipelineInput(
            session_id=session.session_id,
            input_type=InputType.TEXT_INPUT,
            text_data="Good morning",
            selected_reply_id=top_pred.id,
        )
        await orchestrator.process(followup_inp, session)

        stats = session.learning_stats
        total = stats.get("total_taps", 0)
        top1 = stats.get("top_1_taps", 0)
        print(f"  Learning stats  : total_taps={total}, top_1_taps={top1}")
        if total > 0:
            print(f"  Top-1 accuracy  : {top1 / total:.0%}")
    else:
        print("  No predictions returned — skipping tap test")

    # ── TEST 4: Emergency short-circuit ──────────────────────────────────────
    _sep("TEST 4 — Emergency Short-Circuit")

    emergency_inp = PipelineInput(
        session_id=session.session_id,
        input_type=InputType.EMERGENCY_TAP,
    )
    t0 = time.perf_counter()
    emergency_out = await orchestrator.process(emergency_inp, session)
    elapsed_ms = int((time.perf_counter() - t0) * 1000)

    print(f"  emergency_triggered : {emergency_out.emergency_triggered}")
    urgency_val = emergency_out.urgency.value if emergency_out.urgency and hasattr(emergency_out.urgency, "value") else str(emergency_out.urgency)
    print(f"  urgency             : {urgency_val}")
    print(f"  Pipeline bypassed in: {elapsed_ms} ms")

    # ── Summary ───────────────────────────────────────────────────────────────
    _sep("Summary")
    ctx_val = session.detected_context.value if hasattr(session.detected_context, "value") else str(session.detected_context)
    print(f"  Session messages : {len(session.messages)}")
    print(f"  Session context  : {ctx_val}")
    print(f"  Learning stats   : {session.learning_stats}")
    print()

    # ── Cleanup ───────────────────────────────────────────────────────────────
    if backboard:
        await backboard.close()
    if elevenlabs:
        await elevenlabs.close()


if __name__ == "__main__":
    asyncio.run(main())
