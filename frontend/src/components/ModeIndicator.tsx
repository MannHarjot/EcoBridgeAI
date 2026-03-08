'use client';

import type { ImpairmentMode } from '@/lib/types';

interface Props {
  mode: ImpairmentMode;
  compact?: boolean;
  className?: string;
}

const MODE_CONFIG: Record<
  ImpairmentMode,
  { label: string; shortLabel: string; icon: string; color: string }
> = {
  hearing_only:    { label: 'Hearing impairment',  shortLabel: 'Hearing',  icon: '🔇', color: 'text-cyan-400' },
  speech_only:     { label: 'Speech impairment',   shortLabel: 'Speech',   icon: '🔕', color: 'text-violet-400' },
  dual_impairment: { label: 'Dual impairment',     shortLabel: 'Dual',     icon: '♿', color: 'text-amber-400' },
};

export default function ModeIndicator({ mode, compact = false, className = '' }: Props) {
  const config = MODE_CONFIG[mode] ?? MODE_CONFIG.dual_impairment;

  if (compact) {
    return (
      <span
        className={`inline-flex items-center gap-1 text-sm ${config.color} ${className}`}
        title={config.label}
        aria-label={`Mode: ${config.label}`}
      >
        <span aria-hidden="true">{config.icon}</span>
        <span className="hidden md:inline">{config.shortLabel}</span>
      </span>
    );
  }

  return (
    <div
      className={[
        'inline-flex items-center gap-2 px-3 py-2 rounded-xl',
        'bg-slate-800/60 border border-slate-700/40',
        className,
      ].join(' ')}
      aria-label={`Accessibility mode: ${config.label}`}
    >
      <span className="text-xl" aria-hidden="true">{config.icon}</span>
      <div>
        <p className={`text-base font-medium ${config.color}`}>{config.label}</p>
      </div>
    </div>
  );
}
