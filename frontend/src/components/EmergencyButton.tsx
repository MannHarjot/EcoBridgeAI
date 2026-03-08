'use client';

import { useState } from 'react';

interface Props {
  onTrigger: () => void;
  onDismiss: () => void;
  active?: boolean;
  emergencyInfo?: Record<string, string>;
}

export default function EmergencyButton({ onTrigger, onDismiss, active = false, emergencyInfo }: Props) {
  const [confirming, setConfirming] = useState(false);

  const handlePress = () => {
    if (active) return; // already triggered

    if (!confirming) {
      setConfirming(true);
      setTimeout(() => setConfirming(false), 3000);
    } else {
      setConfirming(false);
      onTrigger();
    }
  };

  return (
    <>
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
            : 'bg-rose-900/70 text-rose-300 border-2 border-rose-800 hover:bg-rose-800/80 hover:text-rose-200 animate-idle-pulse',
        ].join(' ')}
      >
        <span className="text-2xl" aria-hidden="true">
          {active ? '🆘' : confirming ? '⚠️' : '🚨'}
        </span>
        <span>
          {active
            ? 'EMERGENCY ACTIVE'
            : confirming
            ? 'TAP AGAIN TO CONFIRM'
            : 'EMERGENCY'}
        </span>
      </button>

      {/* Active overlay — slides up from bottom */}
      {active && (
        <div
          className="fixed inset-0 z-50 flex flex-col items-start justify-end backdrop-blur-sm bg-navy/80 animate-slide-up"
          role="alertdialog"
          aria-label="Emergency active"
        >
          <div className="w-full px-4 pb-8 space-y-4">
            <div className="animate-fade-in" style={{ animationDelay: '0ms' }}>
              <h2 className="text-3xl font-bold text-rose-400">🚨 EMERGENCY ACTIVE</h2>
            </div>
            <div className="animate-fade-in" style={{ animationDelay: '150ms' }}>
              <p className="text-lg text-slate-300">Help is on the way.</p>
            </div>

            {emergencyInfo && Object.keys(emergencyInfo).length > 0 && (
              <div
                className="rounded-2xl border border-rose-800 bg-rose-950/60 p-4 space-y-2 animate-fade-in"
                style={{ animationDelay: '300ms' }}
              >
                {Object.entries(emergencyInfo).map(([key, value]) => (
                  <div key={key} className="flex gap-2">
                    <span className="text-sm text-rose-400/70 capitalize font-medium min-w-[80px]">{key}:</span>
                    <span className="text-sm text-rose-200">{value}</span>
                  </div>
                ))}
              </div>
            )}

            <div className="animate-fade-in pt-2 space-y-2" style={{ animationDelay: '300ms' }}>
              <div
                className="w-full min-h-[56px] rounded-2xl bg-rose-600 text-white font-bold text-lg border-2 border-rose-400 animate-pulse-urgent flex items-center justify-center"
                role="status"
                aria-label="Emergency still active"
              >
                🆘 EMERGENCY ACTIVE
              </div>
              <button
                onClick={onDismiss}
                className="w-full min-h-[48px] rounded-2xl bg-slate-700 hover:bg-slate-600 text-slate-200 font-medium text-base border border-slate-600 transition-colors"
                aria-label="Dismiss emergency overlay"
              >
                Dismiss
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
