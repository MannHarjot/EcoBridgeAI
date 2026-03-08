'use client';

import type { RecapCard } from '@/lib/types';

interface Props {
  recap: RecapCard;
  onClose: () => void;
}

export default function SessionRecap({ recap, onClose }: Props) {
  const accuracy = Math.round(recap.prediction_accuracy * 100);
  const minutes = Math.floor(recap.duration_seconds / 60);
  const seconds = recap.duration_seconds % 60;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Session recap"
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/60 backdrop-blur-sm animate-tile-in"
    >
      <div className="w-full max-w-lg bg-slate-900 rounded-t-3xl border border-slate-700/60 p-6 space-y-5 animate-slide-up max-h-[85vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-warm-white">Session Recap</h2>
            <p className="text-base text-slate-400 mt-0.5">
              {minutes}m {seconds}s · {recap.turn_count} turns
            </p>
          </div>
          <button
            onClick={onClose}
            aria-label="Close recap"
            className="p-2 rounded-xl text-slate-400 hover:text-warm-white hover:bg-slate-800 transition-colors"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Accuracy ring */}
        <div className="flex items-center gap-4 p-4 rounded-2xl bg-slate-800/60 border border-slate-700/40">
          <div className="relative w-16 h-16 flex-shrink-0">
            <svg className="w-16 h-16 -rotate-90" viewBox="0 0 64 64">
              <circle cx="32" cy="32" r="26" fill="none" stroke="#1E293B" strokeWidth="8" />
              <circle
                cx="32"
                cy="32"
                r="26"
                fill="none"
                stroke="#10B981"
                strokeWidth="8"
                strokeLinecap="round"
                strokeDasharray={`${2 * Math.PI * 26}`}
                strokeDashoffset={`${2 * Math.PI * 26 * (1 - recap.prediction_accuracy)}`}
              />
            </svg>
            <span className="absolute inset-0 flex items-center justify-center text-lg font-bold text-emerald-400">
              {accuracy}%
            </span>
          </div>
          <div>
            <p className="text-lg font-semibold text-warm-white">Prediction Accuracy</p>
            <p className="text-base text-slate-400">
              Top-1 match rate across {recap.turn_count} turns
            </p>
          </div>
        </div>

        {/* Summary */}
        {recap.summary && (
          <div className="space-y-2">
            <h3 className="text-lg font-semibold text-warm-white">Summary</h3>
            <p className="text-base text-slate-300 leading-relaxed">{recap.summary}</p>
          </div>
        )}

        {/* Topics */}
        {recap.topics.length > 0 && (
          <div className="space-y-2">
            <h3 className="text-lg font-semibold text-warm-white">Topics discussed</h3>
            <div className="flex flex-wrap gap-2">
              {recap.topics.map((topic, i) => (
                <span key={i} className="px-3 py-1.5 rounded-full bg-indigo-600/20 text-indigo-300 text-base border border-indigo-600/30">
                  {topic}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Action items */}
        {recap.action_items.length > 0 && (
          <div className="space-y-2">
            <h3 className="text-lg font-semibold text-warm-white">Action items</h3>
            <ul className="space-y-2">
              {recap.action_items.map((item, i) => (
                <li key={i} className="flex items-start gap-3 text-base text-slate-300">
                  <span className="mt-1 w-5 h-5 rounded-full bg-amber-500/20 border border-amber-500/40 flex items-center justify-center flex-shrink-0">
                    <span className="w-2 h-2 rounded-full bg-amber-400" />
                  </span>
                  {item}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Close CTA */}
        <button
          onClick={onClose}
          className="w-full min-h-[52px] rounded-2xl bg-indigo-600 hover:bg-indigo-500 text-white text-lg font-semibold transition-colors active:scale-[0.99]"
        >
          Start new session
        </button>
      </div>
    </div>
  );
}
