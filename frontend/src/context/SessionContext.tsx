'use client';

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from 'react';
import { getPreferences, savePreferences } from '@/lib/api';
import type { ImpairmentMode, UserPreferences } from '@/lib/types';

// ── Defaults ──────────────────────────────────────────────────────────────

const DEFAULT_PREFERENCES: UserPreferences = {
  user_id: 'local_user',
  preferred_mode: 'dual_impairment' as ImpairmentMode,
  voice_id: process.env.NEXT_PUBLIC_DEFAULT_VOICE_ID ?? '21m00Tcm4TlvDq8ikWAM',
  favourite_phrases: [],
  emergency_info: {},
  language: 'en',
};

// ── Context ───────────────────────────────────────────────────────────────

interface SessionContextValue {
  sessionId: string;
  userId: string;
  preferences: UserPreferences;
  updatePreferences: (prefs: Partial<UserPreferences>) => Promise<void>;
}

const SessionContext = createContext<SessionContextValue>({
  sessionId: '',
  userId: 'local_user',
  preferences: DEFAULT_PREFERENCES,
  updatePreferences: async () => {},
});

// ── Provider ──────────────────────────────────────────────────────────────

export function SessionProvider({ children }: { children: ReactNode }) {
  const [sessionId, setSessionId] = useState('');
  const [preferences, setPreferences] = useState<UserPreferences>(DEFAULT_PREFERENCES);

  useEffect(() => {
    // Generate a stable session ID using the Web Crypto API
    setSessionId(crypto.randomUUID());

    // Load preferences: localStorage first, then try API
    let loaded: UserPreferences = DEFAULT_PREFERENCES;
    try {
      const raw = localStorage.getItem('echobridge_prefs');
      if (raw) loaded = { ...DEFAULT_PREFERENCES, ...JSON.parse(raw) };
    } catch {
      // ignore parse errors
    }
    setPreferences(loaded);

    // Attempt to sync with backend (non-blocking)
    getPreferences(loaded.user_id)
      .then((prefs) => {
        const merged = { ...loaded, ...prefs };
        setPreferences(merged);
        localStorage.setItem('echobridge_prefs', JSON.stringify(merged));
      })
      .catch(() => {
        // Backend not available — local prefs are fine
      });
  }, []);

  const updatePreferences = useCallback(
    async (prefs: Partial<UserPreferences>) => {
      const updated = { ...preferences, ...prefs };
      setPreferences(updated);
      try {
        localStorage.setItem('echobridge_prefs', JSON.stringify(updated));
        await savePreferences(updated.user_id, updated);
      } catch {
        // persist locally even if API fails
      }
    },
    [preferences],
  );

  return (
    <SessionContext.Provider
      value={{
        sessionId,
        userId: preferences.user_id,
        preferences,
        updatePreferences,
      }}
    >
      {children}
    </SessionContext.Provider>
  );
}

export const useSession = () => useContext(SessionContext);
