'use client';

import { useCallback, useRef, useState } from 'react';

export interface UseAudioPlayerReturn {
  play: (base64Audio: string) => Promise<void>;
  stop: () => void;
  isPlaying: boolean;
}

export function useAudioPlayer(): UseAudioPlayerReturn {
  const [isPlaying, setIsPlaying] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const objectUrlRef = useRef<string | null>(null);

  const stop = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.src = '';
      audioRef.current = null;
    }
    if (objectUrlRef.current) {
      URL.revokeObjectURL(objectUrlRef.current);
      objectUrlRef.current = null;
    }
    setIsPlaying(false);
  }, []);

  const play = useCallback(
    async (base64Audio: string) => {
      stop();

      try {
        // Strip "data:audio/mpeg;base64," prefix if present
        const b64 = base64Audio.includes(',')
          ? base64Audio.split(',')[1]
          : base64Audio;

        const binary = atob(b64);
        const bytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) {
          bytes[i] = binary.charCodeAt(i);
        }

        const blob = new Blob([bytes], { type: 'audio/mpeg' });
        const url = URL.createObjectURL(blob);
        objectUrlRef.current = url;

        const audio = new Audio(url);
        audioRef.current = audio;

        audio.onended = () => {
          setIsPlaying(false);
          URL.revokeObjectURL(url);
          objectUrlRef.current = null;
        };

        audio.onerror = () => {
          setIsPlaying(false);
          URL.revokeObjectURL(url);
          objectUrlRef.current = null;
        };

        await audio.play();
        setIsPlaying(true);
      } catch {
        setIsPlaying(false);
      }
    },
    [stop],
  );

  return { play, stop, isPlaying };
}
