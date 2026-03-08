"use client";

import { Message } from "../types";

interface Props {
  message: Message;
}

export default function MessageBubble({ message }: Props) {
  const isUser = message.sender === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-3 shadow-sm ${
          isUser
            ? "bg-blue-500 text-white"
            : "border border-gray-200 bg-white text-gray-900"
        }`}
      >
        <p className="text-sm leading-relaxed">{message.text}</p>
        <p className={`mt-2 text-[11px] ${isUser ? "text-blue-100" : "text-gray-400"}`}>
          {message.timestamp}
        </p>
      </div>
    </div>
  );
}