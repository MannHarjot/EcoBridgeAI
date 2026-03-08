'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

// ── Browser Speech Recognition types ─────────────────────────────────────
// The Web Speech API is not universally typed across all TS DOM lib versions;
// we use `any` to stay compatible and let the runtime guard handle it.
/* eslint-disable @typescript-eslint/no-explicit-any */
type SpeechRecognitionInstance = any;
declare global {
  interface Window {
    SpeechRecognition: any;
    webkitSpeechRecognition: any;
  }
}
/* eslint-enable @typescript-eslint/no-explicit-any */

export interface UseSpeechRecognitionReturn {
  isListening: boolean;
  transcript: string;
  partialTranscript: string;
  startListening: () => void;
  stopListening: () => void;
  clearTranscript: () => void;
  error: string | null;
  supported: boolean;
}

export function useSpeechRecognition(
  language = 'en-US',
): UseSpeechRecognitionReturn {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [partialTranscript, setPartialTranscript] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [supported, setSupported] = useState(false);

  const recognitionRef = useRef<SpeechRecognitionInstance>(null);

  useEffect(() => {
    setSupported(
      typeof window !== 'undefined' &&
        ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window),
    );
  }, []);

  const startListening = useCallback(() => {
    const SpeechRecognitionAPI =
      window.SpeechRecognition ?? window.webkitSpeechRecognition;

    if (!SpeechRecognitionAPI) {
      setError('Speech recognition is not supported in this browser.');
      return;
    }

    // Stop any existing session
    recognitionRef.current?.stop();

    const recognition = new SpeechRecognitionAPI();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = language;
    recognition.maxAlternatives = 1;

    recognition.onresult = (event: {
      resultIndex: number;
      results: { isFinal: boolean; [i: number]: { transcript: string } }[];
    }) => {
      let finalText = '';
      let interimText = '';

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        const text = result[0].transcript;
        if (result.isFinal) {
          finalText += text;
        } else {
          interimText += text;
        }
      }

      if (finalText) {
        setTranscript((prev) => (prev ? `${prev} ${finalText}` : finalText).trim());
        setPartialTranscript('');
      }
      if (interimText) {
        setPartialTranscript(interimText);
      }
    };

    recognition.onerror = (event: { error: string }) => {
      setError(event.error);
      setIsListening(false);
    };

    recognition.onend = () => {
      setIsListening(false);
      setPartialTranscript('');
    };

    recognitionRef.current = recognition;
    recognition.start();
    setIsListening(true);
    setError(null);
  }, [language]);

  const stopListening = useCallback(() => {
    recognitionRef.current?.stop();
    recognitionRef.current = null;
    setIsListening(false);
    setPartialTranscript('');
  }, []);

  const clearTranscript = useCallback(() => {
    setTranscript('');
    setPartialTranscript('');
  }, []);

  useEffect(() => {
    return () => {
      recognitionRef.current?.stop();
    };
  }, []);

  return {
    isListening,
    transcript,
    partialTranscript,
    startListening,
    stopListening,
    clearTranscript,
    error,
    supported,
  };
}
