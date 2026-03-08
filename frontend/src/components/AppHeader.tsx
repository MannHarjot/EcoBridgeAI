"use client";

import EmergencyButton from "./EmergencyButton";

export default function AppHeader() {
  return (
    <header className="sticky top-0 z-30 border-b border-gray-200 bg-white/90 backdrop-blur">
      <div className="mx-auto flex max-w-md items-center justify-between px-4 py-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-blue-600">
            Accessibility Communication
          </p>
          <h1 className="text-2xl font-bold text-gray-900">EchoBridge</h1>
        </div>

        <EmergencyButton />
      </div>
    </header>
  );
}