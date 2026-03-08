'use client';

interface Props {
  isPlaying: boolean;
  onStop: () => void;
}

export default function VoicePlayer({ isPlaying, onStop }: Props) {
  if (!isPlaying) return null;

  return (
    <div className="flex items-center gap-3 px-4 py-2 bg-emerald-900/30 border-b border-emerald-800/40 animate-slide-up">
      {/* Waveform animation */}
      <div className="flex items-end gap-0.5 h-5" aria-hidden="true">
        {[0.4, 0.8, 1, 0.6, 0.9, 0.5, 0.7].map((h, i) => (
          <span
            key={i}
            className="w-1 bg-emerald-400 rounded-full animate-blink"
            style={{
              height: `${h * 100}%`,
              animationDelay: `${i * 100}ms`,
              animationDuration: '0.6s',
            }}
          />
        ))}
      </div>

      <span className="text-base text-emerald-300 font-medium flex-1">
        Speaking…
      </span>

      <button
        onClick={onStop}
        aria-label="Stop audio playback"
        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-800/50 hover:bg-emerald-700/50 text-emerald-300 text-sm transition-colors min-h-[0]"
      >
        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
          <rect x="5" y="5" width="10" height="10" rx="2" />
        </svg>
        Stop
      </button>
    </div>
  );
}
