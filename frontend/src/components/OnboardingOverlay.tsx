"use client";

import { useEffect, useState } from "react";
import { getVoices } from "@/lib/api";
import { ImpairmentMode, UserPreferences, Voice } from "@/lib/types";
import { ModeCard } from "./ModeCard";
import { VoiceCard } from "./VoiceCard";

interface Props {
  onComplete: (prefs: Partial<UserPreferences>) => void;
}

const MODES: ImpairmentMode[] = ["hearing_only", "speech_only", "dual_impairment"];

export function OnboardingOverlay({ onComplete }: Props) {
  const [step, setStep] = useState(0);
  const [voices, setVoices] = useState<Voice[]>([]);
  const [selectedVoiceId, setSelectedVoiceId] = useState<string | null>(null);
  const [selectedMode, setSelectedMode] = useState<ImpairmentMode>("dual_impairment");

  useEffect(() => {
    getVoices()
      .then((v) => setVoices(v.slice(0, 3)))
      .catch(() => {});
  }, []);

  function handleComplete() {
    onComplete({
      ...(selectedVoiceId ? { voice_id: selectedVoiceId } : {}),
      preferred_mode: selectedMode,
    });
  }

  return (
    <div className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-bridge-bg px-4">
      {/* Progress dots */}
      <div className="mb-8 flex gap-2" role="list" aria-label="Onboarding progress">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            role="listitem"
            className={[
              "h-2 rounded-full transition-all",
              i === step ? "w-6 bg-emerald-400" : i < step ? "w-2 bg-emerald-600" : "w-2 bg-slate-600",
            ].join(" ")}
          />
        ))}
      </div>

      {/* Step 1 — Welcome */}
      {step === 0 && (
        <div className="flex w-full max-w-sm flex-col items-center gap-4 text-center">
          <span className="text-6xl" aria-hidden="true">🌉</span>
          <h1 className="text-4xl font-bold text-bridge-text">EchoBridge</h1>
          <p className="text-xl text-bridge-muted">Real-time communication bridge</p>
          <p className="mt-2 text-base text-bridge-muted">
            Helping people with hearing and speech differences communicate in real-time. Let&apos;s set up in 30 seconds.
          </p>
          <button
            type="button"
            onClick={() => setStep(1)}
            className="mt-4 w-full rounded-xl bg-emerald-600 py-3.5 text-lg font-bold text-white transition-colors hover:bg-emerald-500"
          >
            Get Started →
          </button>
        </div>
      )}

      {/* Step 2 — Voice */}
      {step === 1 && (
        <div className="flex w-full max-w-sm flex-col gap-4">
          <div className="text-center">
            <h2 className="text-2xl font-bold text-bridge-text">Choose your voice</h2>
            <p className="mt-1 text-sm text-bridge-muted">Choose a voice that feels like you.</p>
          </div>

          <div className="space-y-3">
            {voices.length === 0 ? (
              <p className="text-center text-sm text-bridge-muted">Loading voices…</p>
            ) : (
              voices.map((v) => (
                <VoiceCard
                  key={v.voice_id}
                  voice={v}
                  selected={selectedVoiceId === v.voice_id}
                  onSelect={() => setSelectedVoiceId(v.voice_id)}
                />
              ))
            )}
          </div>

          <p className="text-center text-xs text-bridge-muted">You can change this anytime in Settings.</p>

          <button
            type="button"
            onClick={() => setStep(2)}
            className="w-full rounded-xl bg-emerald-600 py-3.5 text-lg font-bold text-white transition-colors hover:bg-emerald-500"
          >
            Next →
          </button>
        </div>
      )}

      {/* Step 3 — Mode */}
      {step === 2 && (
        <div className="flex w-full max-w-sm flex-col gap-4">
          <div className="text-center">
            <h2 className="text-2xl font-bold text-bridge-text">How do you communicate?</h2>
            <p className="mt-1 text-sm text-bridge-muted">
              EchoBridge adapts automatically, but this helps us start right.
            </p>
          </div>

          <div className="space-y-3">
            {MODES.map((m) => (
              <ModeCard key={m} mode={m} selected={selectedMode === m} onSelect={() => setSelectedMode(m)} />
            ))}
          </div>

          <button
            type="button"
            onClick={handleComplete}
            className="w-full rounded-xl bg-emerald-600 py-3.5 text-lg font-bold text-white transition-colors hover:bg-emerald-500"
          >
            Start Talking →
          </button>
        </div>
      )}
    </div>
  );
}
