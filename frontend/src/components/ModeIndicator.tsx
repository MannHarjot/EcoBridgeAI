"use client";

import { Mode } from "../types";

interface Props {
  currentMode: Mode;
  setMode: (mode: Mode) => void;
}

const modes: { label: string; value: Mode }[] = [
  { label: "General", value: "general" },
  { label: "Hospital", value: "hospital" },
  { label: "Transit", value: "transit" },
  { label: "Emergency", value: "emergency" },
];

export default function ModeIndicator({ currentMode, setMode }: Props) {
  return (
    <div className="mx-auto w-full max-w-md px-4 pt-4">
      <div className="grid grid-cols-2 gap-3">
        {modes.map((mode) => {
          const isActive = currentMode === mode.value;

          return (
            <button
              key={mode.value}
              onClick={() => setMode(mode.value)}
              className={`rounded-2xl border px-4 py-4 text-sm font-semibold transition ${
                isActive
                  ? "border-blue-500 bg-blue-500 text-white shadow-md"
                  : "border-gray-200 bg-white text-gray-700 hover:bg-gray-50"
              }`}
            >
              {mode.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}