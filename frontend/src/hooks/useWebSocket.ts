'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import type {
  ConversationContext,
  ImpairmentMode,
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
  sendMessage: (text: string) => void;
  sendPartialTranscript: (partial: string) => void;
  sendTap: (replyId: string) => void;
  sendEmergency: () => void;
}

// ── Hook ──────────────────────────────────────────────────────────────────

export function useWebSocket(sessionId: string): UseWebSocketReturn {
  const [connected, setConnected] = useState(false);
  const [messages, setMessages] = useState<TranscriptMessage[]>([]);
  const [predictions, setPredictions] = useState<PredictedReply[]>([]);
  const [partialPredictions, setPartialPredictions] = useState<PredictedReply[]>([]);
  const [currentMode, setCurrentMode] = useState<ImpairmentMode>('dual_impairment');
  const [detectedContext, setDetectedContext] = useState<ConversationContext>('unknown');
  const [pacingAlert, setPacingAlert] = useState<string | null>(null);
  const [emergencyActive, setEmergencyActive] = useState(false);
  const [latencyMs, setLatencyMs] = useState(0);

  const wsRef = useRef<WebSocket | null>(null);
  const retriesRef = useRef(0);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mountedRef = useRef(true);
  const pacingTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

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
            break;
          }

          case 'pipeline_result': {
            const p = msg.payload as Record<string, unknown>;
            if (p.transcript) {
              setMessages((prev) => [...prev, p.transcript as TranscriptMessage]);
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

          case 'emergency': {
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

  const sendMessage = useCallback(
    (text: string) => {
      send({ session_id: sessionId, input_type: 'text_input', text_data: text });
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
      send({ session_id: sessionId, input_type: 'quick_tap', selected_reply_id: replyId });
    },
    [send, sessionId],
  );

  const sendEmergency = useCallback(() => {
    send({ session_id: sessionId, input_type: 'emergency_tap' });
  }, [send, sessionId]);

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
    sendMessage,
    sendPartialTranscript,
    sendTap,
    sendEmergency,
  };
}
