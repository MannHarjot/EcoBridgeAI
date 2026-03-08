import type {
  EmergencyPayload,
  PipelineInput,
  PipelineOutput,
  RecapCard,
  SessionState,
  SessionStats,
  UserPreferences,
  Voice,
} from './types';

const API_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL ?? 'http://localhost:8000';

async function request<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    throw new Error(`API ${options?.method ?? 'GET'} ${path} → ${res.status}`);
  }
  return res.json() as Promise<T>;
}

// ── Message processing ────────────────────────────────────────────────────

export async function processMessage(
  input: PipelineInput,
): Promise<PipelineOutput> {
  return request<PipelineOutput>('/api/message/process', {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

// ── TTS ───────────────────────────────────────────────────────────────────

export async function speakText(
  text: string,
  voiceId?: string,
): Promise<Blob> {
  const res = await fetch(`${API_URL}/api/reply/speak`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, voice_id: voiceId }),
  });
  if (!res.ok) throw new Error(`speakText → ${res.status}`);
  return res.blob();
}

// ── Session ───────────────────────────────────────────────────────────────

export async function getSession(sessionId: string): Promise<SessionState> {
  return request<SessionState>(`/api/session/${sessionId}`);
}

export async function getSessionStats(
  sessionId: string,
): Promise<SessionStats> {
  return request<SessionStats>(`/api/session/${sessionId}/stats`);
}

export async function generateRecap(sessionId: string): Promise<RecapCard> {
  return request<RecapCard>(`/api/session/${sessionId}/recap`, {
    method: 'POST',
  });
}

// ── User preferences ──────────────────────────────────────────────────────

export async function getPreferences(
  userId: string,
): Promise<UserPreferences> {
  return request<UserPreferences>(`/api/user/${userId}/preferences`);
}

export async function savePreferences(
  userId: string,
  prefs: Partial<UserPreferences>,
): Promise<void> {
  await request(`/api/user/${userId}/preferences`, {
    method: 'POST',
    body: JSON.stringify(prefs),
  });
}

// ── Voices ────────────────────────────────────────────────────────────────

export async function getVoices(): Promise<Voice[]> {
  const data = await request<{ voices: Voice[] }>('/api/voices');
  return data.voices ?? [];
}

// ── Emergency ─────────────────────────────────────────────────────────────

export async function triggerEmergency(
  sessionId: string,
): Promise<EmergencyPayload> {
  return request<EmergencyPayload>(`/api/emergency/${sessionId}`, {
    method: 'POST',
  });
}

// ── Demo ──────────────────────────────────────────────────────────────────

export async function preloadDemo(): Promise<void> {
  await request('/api/demo/preload', { method: 'POST' });
}
