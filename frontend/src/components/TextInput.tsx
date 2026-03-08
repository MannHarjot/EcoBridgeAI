'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

interface Props {
  onSend: (text: string) => void;
  isListening: boolean;
  onMicStart: () => void;
  onMicStop: () => void;
  partialTranscript?: string;
  disabled?: boolean;
}

export default function TextInput({
  onSend,
  isListening,
  onMicStart,
  onMicStop,
  partialTranscript = '',
  disabled = false,
}: Props) {
  const [value, setValue] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Mirror partial transcript into input while mic is active
  useEffect(() => {
    if (isListening && partialTranscript) {
      setValue(partialTranscript);
    }
  }, [isListening, partialTranscript]);

  const handleSend = useCallback(() => {
    const text = value.trim();
    if (!text) return;
    onSend(text);
    setValue('');
    textareaRef.current?.focus();
  }, [value, onSend]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend],
  );

  const handleMicToggle = useCallback(() => {
    if (isListening) {
      onMicStop();
      // Send whatever was captured
      if (value.trim()) {
        onSend(value.trim());
        setValue('');
      }
    } else {
      setValue('');
      onMicStart();
    }
  }, [isListening, onMicStart, onMicStop, value, onSend]);

  return (
    <div
      className={[
        'flex items-end gap-2 rounded-2xl border px-3 py-2',
        'bg-slate-800/90 transition-colors duration-150',
        isListening
          ? 'border-rose-500/60 shadow-[0_0_0_2px_rgba(244,63,94,0.15)]'
          : 'border-slate-700/60 focus-within:border-indigo-500/60',
      ].join(' ')}
    >
      {/* Textarea */}
      <textarea
        ref={textareaRef}
        rows={1}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        disabled={disabled}
        placeholder={
          isListening
            ? 'Listening… speak now'
            : 'Type a message or tap the mic…'
        }
        aria-label="Message input"
        className={[
          'flex-1 resize-none bg-transparent text-warm-white placeholder-slate-500',
          'text-lg leading-6 outline-none max-h-32 overflow-y-auto',
          'min-h-[28px] py-1',
          isListening ? 'placeholder-rose-400/60' : '',
        ].join(' ')}
        style={{
          height: 'auto',
          overflowY: value.split('\n').length > 3 ? 'scroll' : 'hidden',
        }}
        onInput={(e) => {
          const el = e.currentTarget;
          el.style.height = 'auto';
          el.style.height = `${Math.min(el.scrollHeight, 128)}px`;
        }}
      />

      {/* Mic button */}
      <button
        onClick={handleMicToggle}
        disabled={disabled}
        aria-label={isListening ? 'Stop microphone' : 'Start microphone'}
        aria-pressed={isListening}
        className={[
          'flex-shrink-0 w-11 h-11 rounded-xl flex items-center justify-center',
          'transition-all duration-150 active:scale-95',
          isListening
            ? 'bg-rose-500 text-white animate-pulse-urgent'
            : 'bg-slate-700 text-slate-300 hover:bg-slate-600',
        ].join(' ')}
      >
        {isListening ? (
          // Stop icon
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
            <rect x="5" y="5" width="10" height="10" rx="2" />
          </svg>
        ) : (
          // Mic icon
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
            <path d="M7 4a3 3 0 016 0v6a3 3 0 11-6 0V4z" />
            <path d="M5.5 9.643a.75.75 0 00-1.5 0V10c0 3.06 2.29 5.585 5.25 5.954V17.5h-1.5a.75.75 0 000 1.5h4.5a.75.75 0 000-1.5H10.5v-1.546A6.001 6.001 0 0016 10v-.357a.75.75 0 00-1.5 0V10a4.5 4.5 0 01-9 0v-.357z" />
          </svg>
        )}
      </button>

      {/* Send button */}
      <button
        onClick={handleSend}
        disabled={!value.trim() || disabled}
        aria-label="Send message"
        className={[
          'flex-shrink-0 w-11 h-11 rounded-xl flex items-center justify-center',
          'transition-all duration-150 active:scale-95',
          value.trim()
            ? 'bg-indigo-600 hover:bg-indigo-500 text-white'
            : 'bg-slate-700/50 text-slate-600 cursor-not-allowed',
        ].join(' ')}
      >
        <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
        </svg>
      </button>
    </div>
  );
}
