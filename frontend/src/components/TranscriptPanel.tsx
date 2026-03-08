'use client';

import { useEffect, useRef } from 'react';
import type { TranscriptMessage, UrgencyLevel } from '@/lib/types';

interface Props {
  messages: TranscriptMessage[];
}

const URGENCY_COLORS: Record<UrgencyLevel, string> = {
  low:       'text-slate-400',
  medium:    'text-amber-400',
  high:      'text-amber-500',
  emergency: 'text-rose-500',
};

const URGENCY_LABELS: Record<UrgencyLevel, string> = {
  low:       'Low',
  medium:    'Medium',
  high:      'High',
  emergency: '🚨 Emergency',
};

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch {
    return '';
  }
}

export default function TranscriptPanel({ messages }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center px-6">
        <div className="text-center space-y-3 opacity-40">
          <div className="text-5xl">💬</div>
          <p className="text-lg text-slate-400">
            Waiting for conversation to begin…
          </p>
          <p className="text-base text-slate-500">
            Tap the mic or type a message below
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
      {messages.map((msg) => {
        const isUser = msg.speaker === 'user';

        return (
          <div
            key={msg.id}
            className={`flex animate-slide-up ${isUser ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[85%] rounded-2xl px-4 py-3 space-y-1 ${
                isUser
                  ? 'bg-indigo-600/80 text-white rounded-br-sm'
                  : 'bg-slate-800 text-warm-white rounded-bl-sm border border-slate-700/60'
              }`}
            >
              {/* Speaker label */}
              <div className="flex items-center justify-between gap-3">
                <span className="text-xs font-semibold uppercase tracking-wide opacity-60">
                  {isUser ? 'You' : 'Other person'}
                </span>
                <span className="text-xs opacity-40">{formatTime(msg.timestamp)}</span>
              </div>

              {/* Raw text */}
              <p className="text-lg leading-snug">{msg.raw_text}</p>

              {/* Simplified text — shown if different from raw */}
              {msg.simplified_text && msg.simplified_text !== msg.raw_text && (
                <div className="mt-1 pt-1 border-t border-white/10">
                  <p className="text-base text-slate-300 italic">
                    <span className="text-xs not-italic font-medium opacity-50 mr-1">
                      Simplified:
                    </span>
                    {msg.simplified_text}
                  </p>
                </div>
              )}

              {/* Badges row */}
              {(msg.intent || msg.urgency) && (
                <div className="flex flex-wrap gap-2 pt-1">
                  {msg.intent && (
                    <span className="px-2 py-0.5 rounded-full text-xs bg-white/10 capitalize">
                      {msg.intent.replace('_', ' ')}
                    </span>
                  )}
                  {msg.urgency && msg.urgency !== 'low' && (
                    <span
                      className={`px-2 py-0.5 rounded-full text-xs font-medium ${URGENCY_COLORS[msg.urgency]}`}
                    >
                      {URGENCY_LABELS[msg.urgency]}
                    </span>
                  )}
                </div>
              )}
            </div>
          </div>
        );
      })}
      <div ref={bottomRef} className="h-1" />
    </div>
  );
}
