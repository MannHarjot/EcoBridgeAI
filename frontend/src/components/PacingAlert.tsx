'use client';

interface Props {
  message: string;
}

export default function PacingAlert({ message }: Props) {
  return (
    <div
      role="alert"
      aria-live="assertive"
      className={[
        'flex items-center gap-3 px-4 py-3',
        'bg-amber-500/15 border-b border-amber-500/30',
        'animate-slide-up',
      ].join(' ')}
    >
      {/* Animated speed icon */}
      <span className="text-amber-400 text-xl flex-shrink-0" aria-hidden="true">
        ⚡
      </span>

      <div className="flex-1 min-w-0">
        <p className="text-base text-amber-300 font-medium leading-snug">
          {message}
        </p>
        <p className="text-sm text-amber-400/60 mt-0.5">
          You can ask them to slow down using the prediction tiles below.
        </p>
      </div>

      <span className="text-amber-400/50 text-sm flex-shrink-0 font-mono">
        Pacing
      </span>
    </div>
  );
}
