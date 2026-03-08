'use client';

import { useState } from 'react';

interface Props {
  onTrigger: () => void;
  active?: boolean;
}

export default function EmergencyButton({ onTrigger, active = false }: Props) {
  const [confirming, setConfirming] = useState(false);

  const handlePress = () => {
    if (active) return; // already triggered

    if (!confirming) {
      // First press — ask to confirm
      setConfirming(true);
      setTimeout(() => setConfirming(false), 3000);
    } else {
      // Second press — fire
      setConfirming(false);
      onTrigger();
    }
  };

  return (
    <button
      onClick={handlePress}
      aria-label={
        active
          ? 'Emergency activated'
          : confirming
          ? 'Press again to confirm emergency'
          : 'Trigger emergency alert'
      }
      aria-pressed={active}
      className={[
        'w-full min-h-[56px] rounded-2xl font-bold text-lg tracking-wide',
        'flex items-center justify-center gap-3',
        'transition-all duration-200 active:scale-[0.98]',
        active
          ? 'bg-rose-600 text-white animate-pulse-urgent border-2 border-rose-400'
          : confirming
          ? 'bg-rose-500 text-white border-2 border-rose-300 scale-[1.01]'
          : 'bg-rose-900/70 text-rose-300 border-2 border-rose-800 hover:bg-rose-800/80 hover:text-rose-200',
      ].join(' ')}
    >
      {/* Icon */}
      <span className="text-2xl" aria-hidden="true">
        {active ? '🆘' : confirming ? '⚠️' : '🚨'}
      </span>

      {/* Label */}
      <span>
        {active
          ? 'EMERGENCY ACTIVE'
          : confirming
          ? 'TAP AGAIN TO CONFIRM'
          : 'EMERGENCY'}
      </span>
    </button>
  );
}
