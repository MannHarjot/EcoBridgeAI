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
import { generateRecap } from '@/lib/api';

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
    sendMessage,
    sendPartialTranscript,
    sendTap,
    sendEmergency,
  } = useWebSocket(sessionId);

  const {
    isListening,
    transcript,
    partialTranscript,
    startListening,
    stopListening,
    clearTranscript,
  } = useSpeechRecognition(
    preferences.language ? `${preferences.language}-US` : 'en-US',
  );

  const { play, stop: stopAudio, isPlaying } = useAudioPlayer();

  const [recap, setRecap] = useState<RecapCard | null>(null);
  const lastTranscriptRef = useRef('');
  const lastPartialRef = useRef('');

  // Auto-play voice when backend sends audio
  useEffect(() => {
    const lastMsg = messages[messages.length - 1];
    if (lastMsg?.speaker === 'other') {
      // Check most recent pipeline output for voice URL via predictions
      // (voice_audio_url comes through WebSocket pipeline_result payload — handled in useWebSocket)
    }
  }, [messages]);

  // Feed partial transcript → WebSocket streaming predictions
  useEffect(() => {
    if (isListening && partialTranscript && partialTranscript !== lastPartialRef.current) {
      lastPartialRef.current = partialTranscript;
      sendPartialTranscript(partialTranscript);
    }
  }, [isListening, partialTranscript, sendPartialTranscript]);

  // Send completed transcript as a message
  useEffect(() => {
    if (transcript && transcript !== lastTranscriptRef.current) {
      lastTranscriptRef.current = transcript;
      sendMessage(transcript);
      clearTranscript();
    }
  }, [transcript, sendMessage, clearTranscript]);

  const handleSend = useCallback(
    (text: string) => {
      if (text.trim()) sendMessage(text);
    },
    [sendMessage],
  );

  const handleTap = useCallback(
    (replyId: string) => {
      sendTap(replyId);
    },
    [sendTap],
  );

  const handleRecap = useCallback(async () => {
    if (!sessionId) return;
    try {
      const card = await generateRecap(sessionId);
      setRecap(card);
    } catch {
      // Backend unavailable — show placeholder
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

  // Show session is not ready while session ID is being generated
  if (!sessionId) {
    return (
      <main className="flex flex-col h-screen items-center justify-center bg-navy">
        <div className="text-center space-y-3">
          <div className="w-12 h-12 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-lg text-slate-400">Starting session…</p>
        </div>
      </main>
    );
  }

  const activePredictions =
    partialPredictions.length > 0 ? partialPredictions : predictions;
  const showPartial = partialPredictions.length > 0;

  return (
    <main className="flex flex-col h-screen bg-navy overflow-hidden">
      {/* ── Status bar ──────────────────────────────────────────────────── */}
      <StatusBar
        connected={connected}
        detectedContext={detectedContext}
        currentMode={currentMode}
        emergencyActive={emergencyActive}
        latencyMs={latencyMs}
      />

      {/* ── Pacing alert (conditional) ───────────────────────────────── */}
      {pacingAlert && <PacingAlert message={pacingAlert} />}

      {/* ── Transcript ──────────────────────────────────────────────────── */}
      <div className="flex-1 min-h-0 overflow-hidden flex flex-col">
        <TranscriptPanel messages={messages} />
      </div>

      {/* ── Bottom panel ────────────────────────────────────────────────── */}
      <div className="flex-shrink-0 border-t border-slate-700/50 bg-slate-900/80 backdrop-blur-sm">
        {/* Voice playing indicator */}
        <VoicePlayer isPlaying={isPlaying} onStop={stopAudio} />

        {/* Prediction tiles */}
        <PredictionTiles
          predictions={activePredictions}
          partialText={isListening ? partialTranscript : undefined}
          isPartial={showPartial}
          onTap={handleTap}
        />

        {/* Text input + recap button */}
        <div className="px-3 pt-2 pb-1">
          <TextInput
            onSend={handleSend}
            isListening={isListening}
            onMicStart={startListening}
            onMicStop={stopListening}
            partialTranscript={partialTranscript}
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
          <EmergencyButton onTrigger={sendEmergency} active={emergencyActive} />
        </div>
      </div>

      {/* ── Session recap modal ──────────────────────────────────────── */}
      {recap && <SessionRecap recap={recap} onClose={() => setRecap(null)} />}
    </main>
  );
}
