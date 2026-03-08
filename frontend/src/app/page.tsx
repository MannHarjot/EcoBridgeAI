"use client";

import { useMemo, useState } from "react";
import AppHeader from "../components/AppHeader";
import BottomNav from "../components/BottomNav";
import ConversationSection from "../components/ConversationSection";
import ModeIndicator from "../components/ModeIndicator";
import PredictionTiles from "../components/PredictionTiles";
import StatusBar from "../components/StatusBar";
import TextInputBar from "../components/TextInputBar";
import TranscriptPanel from "../components/TranscriptPanel";
import { mockMessages, suggestionsByMode, transcriptByMode } from "../data/mockData";
import { Message, Mode, Status } from "../types";

export default function Home() {
  const [mode, setMode] = useState<Mode>("general");
  const [status] = useState<Status>("listening");
  const [messages, setMessages] = useState<Message[]>(mockMessages);

  const transcriptData = useMemo(() => transcriptByMode[mode], [mode]);
  const suggestions = useMemo(() => suggestionsByMode[mode], [mode]);

  const addUserMessage = (text: string) => {
    const newMessage: Message = {
      id: Date.now(),
      sender: "user",
      text,
      timestamp: new Date().toLocaleTimeString([], {
        hour: "numeric",
        minute: "2-digit",
      }),
    };

    setMessages((prev) => [...prev, newMessage]);
  };

  return (
    <main className="min-h-screen bg-gradient-to-b from-gray-50 to-gray-100 pb-24">
      <AppHeader />
      <ModeIndicator currentMode={mode} setMode={setMode} />
      <StatusBar status={status} />

      <TranscriptPanel
        transcript={transcriptData.transcript}
        simplified={transcriptData.simplified}
        urgency={transcriptData.urgency}
      />

      <PredictionTiles suggestions={suggestions} onSelect={addUserMessage} />
      <TextInputBar onSend={addUserMessage} />
      <ConversationSection messages={messages} />

      <BottomNav />
    </main>
  );
}