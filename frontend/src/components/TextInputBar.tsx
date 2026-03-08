"use client";

import { useState } from "react";

interface Props {
  onSend: (value: string) => void;
}

export default function TextInputBar({ onSend }: Props) {
  const [input, setInput] = useState("");

  const handleSend = () => {
    if (!input.trim()) return;
    onSend(input.trim());
    setInput("");
  };

  return (
    <section className="mx-auto w-full max-w-md px-4 pt-4">
      <div className="rounded-3xl border border-gray-200 bg-white p-4 shadow-sm">
        <label className="mb-2 block text-sm font-semibold text-gray-500">
          Type your message
        </label>

        <div className="flex gap-3">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type a custom response..."
            className="flex-1 rounded-2xl border border-gray-200 px-4 py-3 text-base outline-none ring-0 placeholder:text-gray-400 focus:border-blue-500"
          />
          <button
            onClick={handleSend}
            className="rounded-2xl bg-blue-500 px-5 py-3 text-sm font-semibold text-white transition hover:bg-blue-600"
          >
            Send
          </button>
        </div>
      </div>
    </section>
  );
}