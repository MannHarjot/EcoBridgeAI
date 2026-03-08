"use client";

import { useRef, useState } from "react";
import { speakText } from "@/lib/api";
import { Voice } from "@/lib/types";

interface Props {
  voice: Voice;
  selected: boolean;
  onSelect: () => void;
}

export function VoiceCard({ voice, selected, onSelect }: Props) {
  const [previewing, setPreviewing] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  async function handlePreview(e: React.MouseEvent) {
    e.stopPropagation();
    if (previewing) {
      audioRef.current?.pause();
      setPreviewing(false);
      return;
    }
    try {
      setPreviewing(true);
      const blob = await speakText("Hello, nice to meet you.", voice.voice_id);
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audioRef.current = audio;
      audio.onended = () => {
        URL.revokeObjectURL(url);
        setPreviewing(false);
        audioRef.current = null;
      };
      audio.onerror = () => {
        URL.revokeObjectURL(url);
        setPreviewing(false);
        audioRef.current = null;
      };
      await audio.play();
    } catch {
      setPreviewing(false);
    }
  }

  return (
    <button
      type="button"
      onClick={onSelect}
      className={[
        "flex min-h-24 w-full flex-col justify-between rounded-xl border-2 p-4 text-left transition-all",
        selected
          ? "border-emerald-500 bg-emerald-500/10"
          : "border-slate-700 bg-slate-800 hover:border-slate-500",
      ].join(" ")}
    >
      <div className="flex items-start justify-between gap-2">
        <span className="text-base font-bold text-bridge-text">{voice.name}</span>
        {voice.recommended && (
          <span className="flex-shrink-0 rounded-full bg-emerald-600/30 px-2 py-0.5 text-xs font-medium text-emerald-300">
            Recommended
          </span>
        )}
      </div>

      <button
        type="button"
        onClick={handlePreview}
        disabled={false}
        className={[
          "mt-3 self-start rounded-lg px-3 py-1.5 text-sm font-medium transition-colors",
          previewing
            ? "bg-amber-500/20 text-amber-300"
            : "bg-slate-700 text-bridge-muted hover:bg-slate-600 hover:text-bridge-text",
        ].join(" ")}
      >
        {previewing ? "Playing…" : "Preview ▶"}
      </button>
    </button>
  );
}
