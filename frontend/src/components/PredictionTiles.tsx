'use client';

import type { PredictedReply, PredictionConfidence } from '@/lib/types';

interface Props {
  predictions: PredictedReply[];
  partialText?: string; // partial transcript driving the predictions
  isPartial?: boolean;  // true when showing streaming partial predictions
  onTap: (replyId: string) => void;
}

// Opacity & border style based on prediction confidence stage
const STAGE_STYLES: Record<PredictionConfidence, string> = {
  speculative: 'opacity-50 border-slate-600/40',
  likely:      'opacity-75 border-slate-500/60',
  confident:   'opacity-100 border-slate-600/80',
};

const STAGE_RING: Record<PredictionConfidence, string> = {
  speculative: '',
  likely:      'hover:ring-1 hover:ring-amber-500/40',
  confident:   'hover:ring-2 hover:ring-indigo-500/60',
};

const CATEGORY_COLORS: Record<string, string> = {
  medical:      'text-indigo-400',
  emergency:    'text-rose-400',
  question:     'text-blue-400',
  confirmation: 'text-emerald-400',
  request:      'text-amber-400',
  greeting:     'text-cyan-400',
  farewell:     'text-violet-400',
};

export default function PredictionTiles({
  predictions,
  partialText,
  isPartial = false,
  onTap,
}: Props) {
  if (predictions.length === 0) {
    return (
      <div className="px-4 py-2">
        <p className="text-sm text-slate-500 text-center">
          Predictions will appear as you receive messages
        </p>
      </div>
    );
  }

  return (
    <div className="px-3 py-2 space-y-1">
      {/* Header row */}
      <div className="flex items-center gap-2 px-1 mb-1">
        <span className="text-xs text-slate-500 font-medium uppercase tracking-wide">
          {isPartial ? 'Streaming predictions' : 'Tap to reply'}
        </span>
        {isPartial && partialText && (
          <span className="text-xs text-amber-400/70 truncate max-w-[200px]">
            — "{partialText}"
          </span>
        )}
        {isPartial && (
          <span className="ml-auto flex gap-1">
            {[0, 1, 2].map((i) => (
              <span
                key={i}
                className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-blink"
                style={{ animationDelay: `${i * 0.2}s` }}
              />
            ))}
          </span>
        )}
      </div>

      {/* Tile grid — 2 rows × 3 columns */}
      <div className="grid grid-cols-3 gap-2">
        {predictions.slice(0, 6).map((pred, idx) => {
          const stage = pred.prediction_stage ?? 'confident';
          const catColor = CATEGORY_COLORS[pred.category] ?? 'text-slate-400';

          return (
            <button
              key={pred.id}
              onClick={() => onTap(pred.id)}
              className={[
                'min-h-[72px] px-3 py-3 rounded-xl border text-left',
                'bg-slate-800/80 active:scale-95 transition-all duration-150',
                'flex flex-col justify-between gap-1',
                'animate-tile-in',
                STAGE_STYLES[stage],
                STAGE_RING[stage],
              ].join(' ')}
              style={{ animationDelay: `${idx * 30}ms` }}
              aria-label={`Reply: ${pred.text}`}
            >
              <span className="text-base font-medium text-warm-white leading-tight line-clamp-2">
                {pred.text}
              </span>
              <div className="flex items-center justify-between">
                <span className={`text-xs capitalize ${catColor}`}>
                  {pred.category}
                </span>
                <span className="text-xs text-slate-500">
                  {Math.round(pred.confidence * 100)}%
                </span>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
