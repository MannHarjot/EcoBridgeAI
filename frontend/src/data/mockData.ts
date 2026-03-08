import { Message, Mode, TranscriptData } from "../types";

export const transcriptByMode: Record<Mode, TranscriptData> = {
  general: {
    transcript: "Hello, how can I help you today?",
    simplified: "The person is asking how they can help you.",
    urgency: "low",
  },
  hospital: {
    transcript: "Can you describe your symptoms for me?",
    simplified: "The doctor is asking what symptoms you have.",
    urgency: "medium",
  },
  transit: {
    transcript: "The next bus to Square One arrives in five minutes.",
    simplified: "Your bus will arrive in 5 minutes.",
    urgency: "low",
  },
  emergency: {
    transcript: "Are you in immediate danger right now?",
    simplified: "They are asking if you are in danger now.",
    urgency: "high",
  },
};

export const suggestionsByMode: Record<Mode, string[]> = {
  general: [
    "Please speak slowly",
    "Please repeat that",
    "Thank you",
    "I need help",
  ],
  hospital: [
    "I have a headache",
    "I feel dizzy",
    "I am in pain",
    "Please explain again",
  ],
  transit: [
    "Which platform is it?",
    "Please repeat the destination",
    "I need directions",
    "Thank you",
  ],
  emergency: [
    "I need help now",
    "Call emergency services",
    "Please stay with me",
    "I am not safe",
  ],
};

export const mockMessages: Message[] = [
  {
    id: 1,
    sender: "other",
    text: "Hello, how can I help you today?",
    timestamp: "10:01 AM",
  },
  {
    id: 2,
    sender: "user",
    text: "I am deaf or hard of hearing.",
    timestamp: "10:01 AM",
  },
  {
    id: 3,
    sender: "user",
    text: "Please speak toward the phone.",
    timestamp: "10:02 AM",
  },
];