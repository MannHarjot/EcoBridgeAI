export type Mode = "general" | "hospital" | "transit" | "emergency";

export type Urgency = "low" | "medium" | "high";

export type Status = "idle" | "listening" | "processing" | "speaking" | "offline";

export interface TranscriptData {
  transcript: string;
  simplified: string;
  urgency: Urgency;
}

export interface Message {
  id: number;
  sender: "user" | "other";
  text: string;
  timestamp: string;
}