'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import type {
  ConversationContext,
  ImpairmentMode,
  OutputMode,
  PredictedReply,
  TranscriptMessage,
} from '@/lib/types';

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL ?? 'http://localhost:8000';

function toWsUrl(base: string): string {
  return base.replace(/^http/, 'ws').replace(/\/$/, '');
}

const WS_BASE = toWsUrl(BACKEND_URL);
const MAX_RETRIES = 5;
const RETRY_DELAY_MS = 2000;

// ── Public interface ──────────────────────────────────────────────────────

export interface UseWebSocketReturn {
  connected: boolean;
  messages: TranscriptMessage[];
  predictions: PredictedReply[];
  partialPredictions: PredictedReply[];
  currentMode: ImpairmentMode;
  detectedContext: ConversationContext;
  pacingAlert: string | null;
  emergencyActive: boolean;
  latencyMs: number;
  voiceAudioUrl: string | null;
  sendMessage: (text: string, speaker?: 'user' | 'other') => void;
  sendPartialTranscript: (partial: string) => void;
  sendTap: (replyId: string) => void;
  sendEmergency: () => void;
  clearEmergency: () => void;
  commitStreamingPredictions: () => void;
  addOptimisticMessage: (text: string, speaker: 'user' | 'other') => void;
}

// ── Hook ──────────────────────────────────────────────────────────────────

interface SessionPreferences {
  preferred_mode?: ImpairmentMode;
  output_mode?: OutputMode;
  voice_id?: string;
}

export function useWebSocket(sessionId: string, preferences?: SessionPreferences): UseWebSocketReturn {
  const [connected, setConnected] = useState(false);
  const [messages, setMessages] = useState<TranscriptMessage[]>([]);
  const [predictions, setPredictions] = useState<PredictedReply[]>([]);
  const [partialPredictions, setPartialPredictions] = useState<PredictedReply[]>([]);
  const [currentMode, setCurrentMode] = useState<ImpairmentMode>('dual_impairment');
  const [detectedContext, setDetectedContext] = useState<ConversationContext>('unknown');
  const [pacingAlert, setPacingAlert] = useState<string | null>(null);
  const [emergencyActive, setEmergencyActive] = useState(false);
  const [latencyMs, setLatencyMs] = useState(0);
  const [voiceAudioUrl, setVoiceAudioUrl] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const retriesRef = useRef(0);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mountedRef = useRef(true);
  const pacingTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const preferencesRef = useRef(preferences);
  preferencesRef.current = preferences;

  const clearTimer = () => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  };

  const connect = useCallback(() => {
    if (!sessionId || !mountedRef.current) return;

    const ws = new WebSocket(`${WS_BASE}/ws/session/${sessionId}`);
    wsRef.current = ws;

    ws.onopen = () => {
      if (!mountedRef.current) return;
      setConnected(true);
      retriesRef.current = 0;
    };

    ws.onmessage = (event: MessageEvent) => {
      if (!mountedRef.current) return;
      try {
        const msg = JSON.parse(event.data as string) as {
          type: string;
          payload: Record<string, unknown>;
        };

        switch (msg.type) {
          case 'session_start':
          case 'session_restored': {
            const p = msg.payload;
            if (p.mode) setCurrentMode(p.mode as ImpairmentMode);
            if (p.detected_context) setDetectedContext(p.detected_context as ConversationContext);
            // Apply user's saved preferences to the backend session
            const prefs = preferencesRef.current;
            if (prefs?.preferred_mode || prefs?.output_mode) {
              const mode = prefs.preferred_mode ?? 'dual_impairment';
              ws.send(JSON.stringify({
                type: 'configure',
                mode,
                output_mode: prefs.output_mode ?? 'text_and_voice',
              }));
              setCurrentMode(mode);
            }
            break;
          }

          case 'pipeline_result': {
            const p = msg.payload as Record<string, unknown>;
            if (p.transcript) {
              const incoming = p.transcript as TranscriptMessage;
              setMessages((prev) => {
                // Replace any optimistic placeholder for this speaker; add if none
                const idx = prev.findLastIndex(
                  (m) => (m.id as string).startsWith('_opt_') && m.speaker === incoming.speaker,
                );
                if (idx !== -1) {
                  const next = [...prev];
                  next[idx] = incoming;
                  return next;
                }
                return [...prev, incoming];
              });
            }
            if (Array.isArray(p.predictions)) {
              setPredictions(p.predictions as PredictedReply[]);
              setPartialPredictions([]); // clear partials once we have a final result
            }
            if (p.detected_context) setDetectedContext(p.detected_context as ConversationContext);
            if (p.mode) setCurrentMode(p.mode as ImpairmentMode);
            if (typeof p.prediction_latency_ms === 'number') setLatencyMs(p.prediction_latency_ms);
            if (p.pacing_alert) {
              setPacingAlert(p.pacing_alert as string);
              if (pacingTimerRef.current) clearTimeout(pacingTimerRef.current);
              pacingTimerRef.current = setTimeout(() => setPacingAlert(null), 5000);
            }
            if (typeof p.voice_audio_url === 'string' && p.voice_audio_url) {
              setVoiceAudioUrl(p.voice_audio_url);
            }
            break;
          }

          case 'partial_predictions': {
            const p = msg.payload as Record<string, unknown>;
            if (Array.isArray(p.predictions)) {
              setPartialPredictions(p.predictions as PredictedReply[]);
            }
            break;
          }

          case 'transcript_update': {
            const p = msg.payload as Record<string, unknown>;
            if (p.message) {
              setMessages((prev) => {
                const msg = p.message as TranscriptMessage;
                const exists = prev.some((m) => m.id === msg.id);
                return exists ? prev : [...prev, msg];
              });
            }
            break;
          }

          case 'context_detected': {
            const p = msg.payload as Record<string, unknown>;
            if (p.context) setDetectedContext(p.context as ConversationContext);
            break;
          }

          case 'pacing_alert': {
            const p = msg.payload as Record<string, unknown>;
            if (p.message) {
              setPacingAlert(p.message as string);
              if (pacingTimerRef.current) clearTimeout(pacingTimerRef.current);
              pacingTimerRef.current = setTimeout(() => setPacingAlert(null), 5000);
            }
            break;
          }

          case 'emergency':
          case 'emergency_triggered': {
            setEmergencyActive(true);
            break;
          }

          default:
            break;
        }
      } catch {
        // ignore malformed messages
      }
    };

    ws.onclose = () => {
      if (!mountedRef.current) return;
      setConnected(false);
      if (retriesRef.current < MAX_RETRIES) {
        retriesRef.current += 1;
        timerRef.current = setTimeout(connect, RETRY_DELAY_MS);
      }
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [sessionId]);

  useEffect(() => {
    mountedRef.current = true;
    if (sessionId) connect();

    return () => {
      mountedRef.current = false;
      clearTimer();
      if (pacingTimerRef.current) clearTimeout(pacingTimerRef.current);
      wsRef.current?.close();
    };
  }, [connect, sessionId]);

  // ── Send helpers ────────────────────────────────────────────────────────

  const send = useCallback((data: object) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  }, []);

  // Re-apply preferences whenever they change mid-session (e.g. user changes output mode in Settings)
  const prefMode = preferences?.preferred_mode;
  const prefOutputMode = preferences?.output_mode;
  useEffect(() => {
    if (!connected || (!prefMode && !prefOutputMode)) return;
    const mode = prefMode ?? 'dual_impairment';
    send({ type: 'configure', mode, output_mode: prefOutputMode ?? 'text_and_voice' });
    setCurrentMode(mode);
  }, [prefMode, prefOutputMode, connected, send]);

  const sendMessage = useCallback(
    (text: string, speaker: 'user' | 'other' = 'user') => {
      send({ session_id: sessionId, input_type: 'text_input', text_data: text, speaker });
    },
    [send, sessionId],
  );

  const sendPartialTranscript = useCallback(
    (partial: string) => {
      send({ session_id: sessionId, input_type: 'partial_speech', partial_transcript: partial });
    },
    [send, sessionId],
  );

  const sendTap = useCallback(
    (replyId: string) => {
      const voice_id = preferencesRef.current?.voice_id;
      send({ session_id: sessionId, input_type: 'quick_tap', selected_reply_id: replyId, speaker: 'user', ...(voice_id ? { voice_id } : {}) });
    },
    [send, sessionId],
  );

  const sendEmergency = useCallback(() => {
    send({ session_id: sessionId, input_type: 'emergency_tap' });
  }, [send, sessionId]);

  const clearEmergency = useCallback(() => {
    setEmergencyActive(false);
  }, []);

  // Instantly promote streaming (partial) predictions to final so tiles lock in
  // the moment speech ends — the full pipeline then upgrades them in the background.
  const commitStreamingPredictions = useCallback(() => {
    setPartialPredictions((prev) => {
      if (prev.length > 0) setPredictions(prev);
      return [];
    });
  }, []);

  // Add a message immediately to the chat without waiting for the pipeline.
  // The pipeline_result handler will replace it with the enriched version.
  const addOptimisticMessage = useCallback((text: string, speaker: 'user' | 'other') => {
    const msg: TranscriptMessage = {
      id: `_opt_${Date.now()}`,
      speaker,
      raw_text: text,
      simplified_text: text,
      confidence: 1.0,
      language: 'en',
      timestamp: new Date().toISOString() as unknown as TranscriptMessage['timestamp'],
    };
    setMessages((prev) => [...prev, msg]);
  }, []);

  return {
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
  };
}
