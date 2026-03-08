"use client";

import { ImpairmentMode } from "@/lib/types";

function EarOffIcon({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <path d="M6 12a6 6 0 0 1 11.4-2.5" />
      <path d="M12 6a6 6 0 0 1 5.3 3.1" />
      <path d="M18 12a6 6 0 0 1-3 5.2v.8a2 2 0 0 1-2 2H9" />
      <path d="M12 18v-3a2 2 0 0 1 2-2" />
      <line x1="2" y1="2" x2="22" y2="22" />
    </svg>
  );
}

function MicOffIcon({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <line x1="2" y1="2" x2="22" y2="22" />
      <path d="M18.89 13.23A7.12 7.12 0 0 0 19 12v-2" />
      <path d="M5 10v2a7 7 0 0 0 12 5" />
      <path d="M15 9.34V5a3 3 0 0 0-5.68-1.33" />
      <path d="M9 9v3a3 3 0 0 0 5.12 2.12" />
      <line x1="12" y1="19" x2="12" y2="22" />
      <line x1="8" y1="22" x2="16" y2="22" />
    </svg>
  );
}

const MODE_META: Record<ImpairmentMode, { title: string; subtitle: string; icons: ("ear" | "mic")[] }> = {
  hearing_only: {
    title: "I have difficulty hearing",
    subtitle: "EchoBridge uses visual cues and text",
    icons: ["ear"],
  },
  speech_only: {
    title: "I have difficulty speaking",
    subtitle: "EchoBridge listens and suggests replies",
    icons: ["mic"],
  },
  dual_impairment: {
    title: "I have difficulty with both",
    subtitle: "EchoBridge handles everything for you",
    icons: ["ear", "mic"],
  },
};

interface Props {
  mode: ImpairmentMode;
  selected: boolean;
  onSelect: () => void;
}

export function ModeCard({ mode, selected, onSelect }: Props) {
  const meta = MODE_META[mode];

  return (
    <button
      type="button"
      onClick={onSelect}
      className={[
        "flex w-full items-center gap-4 rounded-xl border-2 p-4 text-left transition-all",
        selected
          ? "border-emerald-500 bg-emerald-500/10"
          : "border-slate-700 bg-slate-800 hover:border-slate-500",
      ].join(" ")}
    >
      <div className="flex gap-1.5 flex-shrink-0">
        {meta.icons.includes("ear") && (
          <EarOffIcon
            className={[
              "h-7 w-7",
              selected ? "text-emerald-400" : "text-bridge-muted",
            ].join(" ")}
          />
        )}
        {meta.icons.includes("mic") && (
          <MicOffIcon
            className={[
              "h-7 w-7",
              selected ? "text-emerald-400" : "text-bridge-muted",
            ].join(" ")}
          />
        )}
      </div>

      <div className="min-w-0">
        <p className="text-base font-bold text-bridge-text">{meta.title}</p>
        <p className="mt-0.5 text-sm text-bridge-muted">{meta.subtitle}</p>
      </div>

      {selected && (
        <span className="ml-auto flex-shrink-0 text-emerald-400" aria-hidden="true">
          ✓
        </span>
      )}
    </button>
  );
}
