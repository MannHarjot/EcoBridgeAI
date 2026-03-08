"use client";

import { Message } from "../types";
import MessageBubble from "./MessageBubble";

interface Props {
  messages: Message[];
}

export default function ConversationSection({ messages }: Props) {
  return (
    <section className="mx-auto w-full max-w-md px-4 pt-4">
      <div className="rounded-3xl border border-gray-200 bg-white p-5 shadow-sm">
        <div className="mb-4">
          <p className="text-sm font-semibold text-gray-500">Conversation</p>
          <h2 className="text-lg font-bold text-gray-900">Recent messages</h2>
        </div>

        <div className="flex flex-col gap-3">
          {messages.map((message) => (
            <MessageBubble key={message.id} message={message} />
          ))}
        </div>
      </div>
    </section>
  );
}