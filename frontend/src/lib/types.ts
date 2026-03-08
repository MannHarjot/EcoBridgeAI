// ── Enums as string unions (mirrors backend Python enums) ─────────────────

export type ImpairmentMode =
  | 'hearing_only'
  | 'speech_only'
  | 'dual_impairment';

export type InputType =
  | 'speech_audio'
  | 'text_input'
  | 'quick_tap'
  | 'emergency_tap'
  | 'partial_speech';

export type IntentType =
  | 'question'
  | 'request'
  | 'confirmation'
  | 'help'
  | 'urgency'
  | 'scheduling'
  | 'greeting'
  | 'farewell'
  | 'information';

export type UrgencyLevel = 'low' | 'medium' | 'high' | 'emergency';

export type OutputMode =
  | 'text_only'
  | 'voice_only'
  | 'text_and_voice'
  | 'visual_only';

export type ConversationContext =
  | 'medical'
  | 'retail'
  | 'emergency'
  | 'casual'
  | 'professional'
  | 'unknown';

export type PredictionConfidence = 'speculative' | 'likely' | 'confident';

// ── Core models ───────────────────────────────────────────────────────────

export interface TranscriptMessage {
  id: string;
  speaker: 'user' | 'other';
  raw_text: string;
  simplified_text?: string;
  intent?: IntentType;
  urgency?: UrgencyLevel;
  confidence: number;
  language: string;
  timestamp: string;
}

export interface PredictedReply {
  id: string;
  text: string;
  category: string;
  confidence: number;
  is_favourite: boolean;
  prediction_stage: PredictionConfidence;
}

export interface PipelineInput {
  session_id: string;
  input_type: InputType;
  audio_data?: string;
  text_data?: string;
  selected_reply_id?: string;
  voice_id?: string;
  partial_transcript?: string;
}

export interface PipelineOutput {
  transcript?: TranscriptMessage;
  simplified_text?: string;
  intent?: IntentType;
  urgency?: UrgencyLevel;
  predictions: PredictedReply[];
  voice_audio_url?: string;
  mode: ImpairmentMode;
  output_mode: OutputMode;
  detected_context: ConversationContext;
  emergency_triggered: boolean;
  is_partial: boolean;
  prediction_latency_ms: number;
  pacing_alert?: string;
}

export interface WebSocketMessage {
  type: string;
  payload: Record<string, unknown>;
}

export interface EmergencyPayload {
  message: string;
  medical_info: Record<string, unknown>;
  spoken_audio_url?: string;
}

export interface UserPreferences {
  user_id: string;
  preferred_mode?: ImpairmentMode;
  voice_id: string;
  favourite_phrases: Array<{ text: string; category: string }>;
  emergency_info: Record<string, unknown>;
  language: string;
}

export interface SessionState {
  session_id: string;
  user_id?: string;
  mode: ImpairmentMode;
  output_mode: OutputMode;
  detected_context: ConversationContext;
  messages: TranscriptMessage[];
  context_summary: string;
  active: boolean;
  created_at: string;
  learning_stats: Record<string, unknown>;
}

export interface SessionStats {
  session_id: string;
  total_turns: number;
  prediction_accuracy_top1: number;
  prediction_accuracy_top3: number;
  avg_response_time_ms: number;
  contexts_detected: string[];
  context_switches: number;
  streaming_updates_sent: number;
  favourite_phrases_used: number;
}

export interface RecapCard {
  session_id: string;
  summary: string;
  topics: string[];
  action_items: string[];
  duration_seconds: number;
  turn_count: number;
  prediction_accuracy: number;
  image_url?: string;
}

export interface Voice {
  voice_id: string;
  name: string;
  description?: string;
  recommended?: boolean;
}
