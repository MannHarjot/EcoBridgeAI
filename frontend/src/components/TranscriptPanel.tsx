"use client";

import { Urgency } from "../types";

interface Props {
  transcript: string;
  simplified: string;
  urgency: Urgency;
}

export default function TranscriptPanel({ transcript, simplified, urgency }: Props) {
  const urgencyStyle: Record<Urgency, string> = {
    low: "bg-green-100 text-green-700",
    medium: "bg-yellow-100 text-yellow-700",
    high: "bg-red-100 text-red-700",
  };

  return (
    <section className="mx-auto w-full max-w-md px-4 pt-4">
      <div className="rounded-3xl border border-gray-200 bg-white p-5 shadow-sm">
        <div className="mb-4 flex items-center justify-between">
          <p className="text-sm font-semibold text-gray-500">Live Speech</p>
          <span className={`rounded-full px-3 py-1 text-xs font-semibold ${urgencyStyle[urgency]}`}>
            {urgency}
          </span>
        </div>

        <p className="text-2xl font-bold leading-relaxed text-gray-900">
          {transcript}
        </p>

        <div className="mt-5 rounded-2xl bg-gray-50 p-4">
          <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-gray-500">
            Simplified meaning
          </p>
          <p className="text-lg font-medium leading-relaxed text-gray-800">
            {simplified}
          </p>
        </div>
      </div>
    </section>
  );
}