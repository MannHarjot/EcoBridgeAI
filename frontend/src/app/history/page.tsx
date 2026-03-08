'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import type { SessionStats } from '@/lib/types';

interface HistoryEntry {
  session_id: string;
  date: string;
  turns: number;
  accuracy: number;
  context: string;
}

// Loads recent sessions from localStorage (set when recap is generated)
function loadHistory(): HistoryEntry[] {
  try {
    const raw = localStorage.getItem('echobridge_history');
    return raw ? (JSON.parse(raw) as HistoryEntry[]) : [];
  } catch {
    return [];
  }
}

export default function HistoryPage() {
  const [entries, setEntries] = useState<HistoryEntry[]>([]);

  useEffect(() => {
    setEntries(loadHistory());
  }, []);

  return (
    <main className="flex flex-col h-screen bg-navy">
      {/* Header */}
      <header className="flex items-center gap-4 px-4 py-4 border-b border-slate-700/50 bg-slate-900/80">
        <Link
          href="/"
          className="p-2 rounded-xl text-slate-400 hover:text-warm-white hover:bg-slate-800/60 transition-colors min-h-[0]"
          aria-label="Back to conversation"
        >
          <svg className="w-6 h-6" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
          </svg>
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-warm-white">Session History</h1>
          <p className="text-base text-slate-400">Past EchoBridge conversations</p>
        </div>
      </header>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-4 py-4">
        {entries.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center space-y-4 py-16 opacity-50">
            <span className="text-6xl">📋</span>
            <h2 className="text-xl font-semibold text-slate-300">No sessions yet</h2>
            <p className="text-base text-slate-500 max-w-xs">
              Complete a conversation and tap "End session & get recap" to save it here.
            </p>
            <Link
              href="/"
              className="mt-2 px-5 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-lg font-medium transition-colors"
            >
              Start a conversation
            </Link>
          </div>
        ) : (
          <div className="space-y-3 max-w-lg mx-auto">
            {entries.map((entry) => (
              <div
                key={entry.session_id}
                className="p-4 rounded-2xl bg-slate-800/60 border border-slate-700/40 space-y-2"
              >
                <div className="flex items-center justify-between">
                  <span className="text-base text-slate-300 font-medium">
                    {new Date(entry.date).toLocaleDateString([], {
                      weekday: 'short', month: 'short', day: 'numeric',
                    })}
                  </span>
                  <span className="text-sm text-slate-500">
                    {new Date(entry.date).toLocaleTimeString([], {
                      hour: '2-digit', minute: '2-digit',
                    })}
                  </span>
                </div>

                <div className="flex items-center gap-4">
                  <div className="text-center">
                    <p className="text-2xl font-bold text-emerald-400">
                      {Math.round(entry.accuracy * 100)}%
                    </p>
                    <p className="text-xs text-slate-500">Accuracy</p>
                  </div>
                  <div className="text-center">
                    <p className="text-2xl font-bold text-indigo-400">{entry.turns}</p>
                    <p className="text-xs text-slate-500">Turns</p>
                  </div>
                  {entry.context && entry.context !== 'unknown' && (
                    <div className="text-center">
                      <p className="text-base font-medium text-slate-300 capitalize">{entry.context}</p>
                      <p className="text-xs text-slate-500">Context</p>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
