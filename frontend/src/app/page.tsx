'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { useSession } from '@/context/SessionContext';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useSpeechRecognition } from '@/hooks/useSpeechRecognition';
import { useAudioPlayer } from '@/hooks/useAudioPlayer';
import TranscriptPanel from '@/components/TranscriptPanel';
import PredictionTiles from '@/components/PredictionTiles';
import TextInput from '@/components/TextInput';
import EmergencyButton from '@/components/EmergencyButton';
import StatusBar from '@/components/StatusBar';
import PacingAlert from '@/components/PacingAlert';
import VoicePlayer from '@/components/VoicePlayer';
import SessionRecap from '@/components/SessionRecap';
import type { RecapCard } from '@/lib/types';
import { generateRecap, preloadDemo } from '@/lib/api';

export default function ConversationPage() {
  const { sessionId, preferences } = useSession();

  const {
    connected,
    messages,
    predictions,
    partialPredictions,
    currentMode,
    detectedContext,
    pacingAlert,
    emergencyActive,
    latencyMs,
    voiceAudioUrl,
    sendMessage,
    sendPartialTranscript,
    sendTap,
    sendEmergency,
    clearEmergency,
    commitStreamingPredictions,
    addOptimisticMessage,
  } = useWebSocket(sessionId, preferences);

  const lang = preferences.language ? `${preferences.language}-US` : 'en-US';

  // User's own mic — only needed in hearing_only mode (they can speak)
  const {
    isListening: isUserListening,
    transcript: userTranscript,
    partialTranscript: userPartial,
    startListening: startUserMic,
    stopListening: stopUserMic,
    clearTranscript: clearUserTranscript,
  } = useSpeechRecognition(lang);

  // Other person's mic — all modes: captures their speech → STT → predictions
  const {
    isListening: isOtherListening,
    transcript: otherTranscript,
    partialTranscript: otherPartial,
    startListening: startOtherMic,
    stopListening: stopOtherMic,
    clearTranscript: clearOtherTranscript,
  } = useSpeechRecognition(lang);

  const { play, stop: stopAudio, isPlaying } = useAudioPlayer();

  const [recap, setRecap] = useState<RecapCard | null>(null);

  // ── Demo mode ────────────────────────────────────────────────────────────
  const [demoMode, setDemoMode] = useState(false);
  const [demoTapCount, setDemoTapCount] = useState(0);
  const [showStats, setShowStats] = useState(false);
  const [demoSimText, setDemoSimText] = useState('');
  const demoTapTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  function handleBrandTap() {
    const next = demoTapCount + 1;
    if (next >= 3) {
      setDemoTapCount(0);
      if (demoTapTimerRef.current) clearTimeout(demoTapTimerRef.current);
      if (!demoMode) {
        setDemoMode(true);
        void preloadDemo();
      } else {
        setDemoMode(false);
        setShowStats(false);
      }
      return;
    }
    setDemoTapCount(next);
    if (demoTapTimerRef.current) clearTimeout(demoTapTimerRef.current);
    demoTapTimerRef.current = setTimeout(() => setDemoTapCount(0), 800);
  }

  const lastUserTranscriptRef = useRef('');
  const lastOtherTranscriptRef = useRef('');
  const lastOtherPartialRef = useRef('');
  const partialTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Auto-play TTS audio when backend sends voice
  useEffect(() => {
    if (voiceAudioUrl) void play(voiceAudioUrl);
  }, [voiceAudioUrl, play]);

  // Other person's partial speech → streaming predictions
  useEffect(() => {
    if (!isOtherListening || !otherPartial || otherPartial === lastOtherPartialRef.current) return;
    if (partialTimerRef.current) clearTimeout(partialTimerRef.current);
    partialTimerRef.current = setTimeout(() => {
      if (otherPartial !== lastOtherPartialRef.current) {
        lastOtherPartialRef.current = otherPartial;
        sendPartialTranscript(otherPartial);
      }
    }, 200);
    return () => {
      if (partialTimerRef.current) clearTimeout(partialTimerRef.current);
    };
  }, [isOtherListening, otherPartial, sendPartialTranscript]);

  // Other person's final speech → message as 'other'.
  // Instantly lock in streaming predictions so tiles solidify the moment speech ends,
  // then send the full pipeline to upgrade them with context-aware final predictions.
  useEffect(() => {
    if (otherTranscript && otherTranscript !== lastOtherTranscriptRef.current) {
      lastOtherTranscriptRef.current = otherTranscript;
      commitStreamingPredictions();
      addOptimisticMessage(otherTranscript, 'other');
      sendMessage(otherTranscript, 'other');
      clearOtherTranscript();
    }
  }, [otherTranscript, sendMessage, clearOtherTranscript, commitStreamingPredictions, addOptimisticMessage]);

  // User's own speech (hearing mode) → message as 'user' — no predictions
  useEffect(() => {
    if (userTranscript && userTranscript !== lastUserTranscriptRef.current) {
      lastUserTranscriptRef.current = userTranscript;
      addOptimisticMessage(userTranscript, 'user');
      sendMessage(userTranscript, 'user');
      clearUserTranscript();
    }
  }, [userTranscript, sendMessage, clearUserTranscript, addOptimisticMessage]);

  const handleSend = useCallback(
    (text: string) => {
      if (text.trim()) {
        addOptimisticMessage(text.trim(), 'user');
        sendMessage(text);
      }
    },
    [sendMessage, addOptimisticMessage],
  );

  const handleTap = useCallback(
    (replyId: string) => {
      const pool = partialPredictions.length > 0 ? partialPredictions : predictions;
      const pred = pool.find((p) => p.id === replyId);
      if (pred) addOptimisticMessage(pred.text, 'user');
      sendTap(replyId);
    },
    [sendTap, addOptimisticMessage, predictions, partialPredictions],
  );

  const handleRecap = useCallback(async () => {
    if (!sessionId) return;
    try {
      const card = await generateRecap(sessionId);
      setRecap(card);
    } catch {
      setRecap({
        session_id: sessionId,
        summary: 'Session complete.',
        topics: [],
        action_items: [],
        duration_seconds: 0,
        turn_count: messages.length,
        prediction_accuracy: 0,
      });
    }
  }, [sessionId, messages.length]);

  // ── Loading states ───────────────────────────────────────────────────────

  if (!sessionId) {
    return (
      <main className="flex flex-col flex-1 items-center justify-center bg-navy">
        <div className="text-center space-y-3">
          <div className="w-12 h-12 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-lg text-slate-400">Starting session…</p>
        </div>
      </main>
    );
  }

  if (!connected && messages.length === 0) {
    return (
      <main className="flex flex-col flex-1 items-center justify-center bg-navy">
        <div className="text-center space-y-3">
          <div className="w-12 h-12 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-lg text-slate-400">Connecting to EchoBridge…</p>
          <p className="text-sm text-slate-500">Make sure the backend is running</p>
        </div>
      </main>
    );
  }

  const activePredictions =
    partialPredictions.length > 0 ? partialPredictions : predictions;
  const showPartial = partialPredictions.length > 0;

  return (
    <main className="flex flex-col flex-1 bg-navy overflow-hidden">
      {/* ── Status bar ──────────────────────────────────────────────────── */}
      <StatusBar
        connected={connected}
        detectedContext={detectedContext}
        currentMode={currentMode}
        emergencyActive={emergencyActive}
        latencyMs={latencyMs}
        isListening={(isUserListening || isOtherListening) && !demoMode}
        isSpeaking={isPlaying}
        demoMode={demoMode}
        onBrandTap={handleBrandTap}
      />

      {/* ── Reconnecting banner (mid-session disconnect) ──────────────── */}
      {!connected && messages.length > 0 && (
        <div className="flex items-center gap-2 px-4 py-2 bg-amber-500/15 border-b border-amber-500/30 text-amber-300 text-sm animate-slide-down">
          <span>⚡</span> Reconnecting
          <span className="flex gap-1 ml-1">
            {[0, 1, 2].map((i) => (
              <span
                key={i}
                className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-blink"
                style={{ animationDelay: `${i * 0.2}s` }}
              />
            ))}
          </span>
        </div>
      )}

      {/* ── Pacing alert (always rendered, fades in/out) ─────────────── */}
      <PacingAlert message={pacingAlert} />

      {/* ── Demo sim input ───────────────────────────────────────────── */}
      {demoMode && (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (demoSimText.trim()) {
              sendMessage(demoSimText, 'other');
              setDemoSimText('');
            }
          }}
          className="flex gap-2 px-4 py-2 bg-amber-500/10 border-b border-amber-500/20"
        >
          <input
            value={demoSimText}
            onChange={(e) => setDemoSimText(e.target.value)}
            placeholder="Simulate: other person says…"
            className="flex-1 bg-slate-800 text-warm-white rounded-xl px-3 py-2 text-sm border border-slate-700 focus:outline-none focus:border-amber-400"
          />
          <button
            type="submit"
            className="px-4 py-2 bg-amber-500 text-black font-bold rounded-xl text-sm"
          >
            Send
          </button>
        </form>
      )}

      {/* ── Transcript ──────────────────────────────────────────────────── */}
      <div className="flex-1 min-h-0 overflow-hidden flex flex-col">
        <TranscriptPanel messages={messages} />
      </div>

      {/* ── Bottom panel ────────────────────────────────────────────────── */}
      <div className="flex-shrink-0 border-t border-slate-700/50 bg-slate-900/80 backdrop-blur-sm">
        {/* Voice playing indicator */}
        <VoicePlayer isPlaying={isPlaying} onStop={stopAudio} />

        {/* Prediction tiles */}
        {/* Other person speaking button — all modes */}
        <div className="px-3 pt-2">
          <button
            onClick={() => isOtherListening ? stopOtherMic() : startOtherMic()}
            aria-label={isOtherListening ? 'Stop listening to other person' : 'Listen to other person speaking'}
            aria-pressed={isOtherListening}
            className={[
              'w-full min-h-[52px] rounded-2xl border font-semibold text-base',
              'flex items-center justify-center gap-3 transition-all duration-150 active:scale-[0.99]',
              isOtherListening
                ? 'bg-emerald-600/20 border-emerald-500/60 text-emerald-300 animate-pulse-urgent'
                : 'bg-slate-800/60 border-slate-700/40 text-slate-400 hover:border-slate-500 hover:text-slate-300',
            ].join(' ')}
          >
            <svg className="w-5 h-5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path d="M7 4a3 3 0 016 0v6a3 3 0 11-6 0V4z" />
              <path d="M5.5 9.643a.75.75 0 00-1.5 0V10c0 3.06 2.29 5.585 5.25 5.954V17.5h-1.5a.75.75 0 000 1.5h4.5a.75.75 0 000-1.5H10.5v-1.546A6.001 6.001 0 0016 10v-.357a.75.75 0 00-1.5 0V10a4.5 4.5 0 01-9 0v-.357z" />
            </svg>
            <span>
              {isOtherListening
                ? otherPartial
                  ? `"${otherPartial.slice(0, 40)}${otherPartial.length > 40 ? '…' : ''}"`
                  : 'Listening to other person…'
                : 'Tap to listen to other person'}
            </span>
          </button>
        </div>

        <PredictionTiles
          predictions={activePredictions}
          partialText={isOtherListening ? otherPartial : undefined}
          isPartial={showPartial}
          onTap={handleTap}
          outputMode={preferences.output_mode}
        />

        {/* Text input + recap button */}
        <div className="px-3 pt-2 pb-1">
          <TextInput
            onSend={handleSend}
            isListening={isUserListening}
            onMicStart={startUserMic}
            onMicStop={stopUserMic}
            partialTranscript={userPartial}
            showMic={currentMode === 'hearing_only'}
          />
        </div>

        {/* Recap link (subtle) */}
        {messages.length >= 4 && (
          <div className="flex justify-center pb-1">
            <button
              onClick={handleRecap}
              className="text-sm text-slate-500 hover:text-slate-300 py-1 px-3 transition-colors min-h-[0]"
            >
              End session & get recap →
            </button>
          </div>
        )}

        {/* Emergency button — full width, always at the bottom */}
        <div className="px-3 pb-4 pt-1">
          <EmergencyButton
            onTrigger={sendEmergency}
            onDismiss={clearEmergency}
            active={emergencyActive}
            emergencyInfo={
              preferences.emergency_info &&
              typeof preferences.emergency_info === 'object' &&
              Object.keys(preferences.emergency_info).length > 0
                ? (preferences.emergency_info as Record<string, string>)
                : undefined
            }
          />
        </div>
      </div>

      {/* ── Demo stats overlay ───────────────────────────────────────── */}
      {demoMode && (
        <>
          <button
            onClick={() => setShowStats((v) => !v)}
            className="fixed bottom-6 left-6 z-40 px-3 py-2 bg-slate-800 border border-slate-600 rounded-xl text-sm text-slate-300 hover:bg-slate-700 transition-colors"
          >
            {showStats ? 'Hide' : 'Stats'}
          </button>
          {showStats && (
            <div className="fixed bottom-20 left-6 z-40 bg-slate-900 border border-slate-700 rounded-2xl p-4 text-sm space-y-1 animate-fade-in">
              <p className="text-slate-400">Latency: <span className="text-warm-white font-mono">{latencyMs}ms</span></p>
              <p className="text-slate-400">Context: <span className="text-warm-white">{detectedContext}</span></p>
              <p className="text-slate-400">Turns: <span className="text-warm-white">{messages.length}</span></p>
              <p className="text-slate-400">Mode: <span className="text-warm-white">{currentMode}</span></p>
            </div>
          )}
        </>
      )}

      {/* ── Session recap modal ──────────────────────────────────────── */}
      {recap && <SessionRecap recap={recap} onClose={() => setRecap(null)} />}
    </main>
  );
}
