'use client';

import Link from 'next/link';
import type { ConversationContext, ImpairmentMode } from '@/lib/types';
import ContextBadge from './ContextBadge';
import ModeIndicator from './ModeIndicator';

interface Props {
  connected: boolean;
  detectedContext: ConversationContext;
  currentMode: ImpairmentMode;
  emergencyActive?: boolean;
  latencyMs?: number;
}

export default function StatusBar({
  connected,
  detectedContext,
  currentMode,
  emergencyActive = false,
  latencyMs = 0,
}: Props) {
  return (
    <header
      className={[
        'flex items-center justify-between px-4 py-3',
        'border-b border-slate-700/50',
        emergencyActive
          ? 'bg-rose-950/80 border-rose-800'
          : 'bg-slate-900/80 backdrop-blur-sm',
      ].join(' ')}
    >
      {/* Left: app name + connection dot */}
      <div className="flex items-center gap-3">
        <Link
          href="/"
          className="flex items-center gap-2 min-h-[0] focus-visible:ring-2 focus-visible:ring-amber-400 rounded-lg"
        >
          <span className="text-xl font-bold text-warm-white tracking-tight">
            EchoBridge
          </span>
          <span className="text-xl font-bold text-amber-400">AI</span>
        </Link>

        {/* Connection indicator */}
        <div className="flex items-center gap-1.5" title={connected ? 'Connected' : 'Reconnecting…'}>
          <span
            className={[
              'w-2.5 h-2.5 rounded-full',
              connected
                ? 'bg-emerald-400 shadow-[0_0_6px_rgba(16,185,129,0.6)]'
                : 'bg-amber-400 animate-blink',
            ].join(' ')}
          />
          <span className="text-xs text-slate-400 hidden sm:block">
            {connected ? 'Live' : 'Connecting…'}
          </span>
        </div>

        {/* Latency badge (only when non-zero) */}
        {latencyMs > 0 && (
          <span className="hidden sm:block text-xs text-slate-500 font-mono">
            {latencyMs}ms
          </span>
        )}
      </div>

      {/* Center: context + mode */}
      <div className="flex items-center gap-2">
        <ContextBadge context={detectedContext} />
        <ModeIndicator mode={currentMode} compact />
      </div>

      {/* Right: nav icons */}
      <div className="flex items-center gap-1">
        <Link
          href="/history"
          className="p-2 rounded-lg text-slate-400 hover:text-warm-white hover:bg-slate-800/60 transition-colors min-h-[0]"
          aria-label="Session history"
          title="History"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </Link>

        <Link
          href="/settings"
          className="p-2 rounded-lg text-slate-400 hover:text-warm-white hover:bg-slate-800/60 transition-colors min-h-[0]"
          aria-label="Settings"
          title="Settings"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 011.37.49l1.296 2.247a1.125 1.125 0 01-.26 1.431l-1.003.827c-.293.24-.438.613-.431.992a6.759 6.759 0 010 .255c-.007.378.138.75.43.99l1.005.828c.424.35.534.954.26 1.43l-1.298 2.247a1.125 1.125 0 01-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.57 6.57 0 01-.22.128c-.331.183-.581.495-.644.869l-.213 1.28c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.02-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 01-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 01-1.369-.49l-1.297-2.247a1.125 1.125 0 01.26-1.431l1.004-.827c.292-.24.437-.613.43-.992a6.932 6.932 0 010-.255c.007-.378-.138-.75-.43-.99l-1.004-.828a1.125 1.125 0 01-.26-1.43l1.297-2.247a1.125 1.125 0 011.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.087.22-.128.332-.183.582-.495.644-.869l.214-1.281z" />
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        </Link>
      </div>
    </header>
  );
}
