"use client";

interface Props {
  suggestions: string[];
  onSelect: (value: string) => void;
}

export default function PredictionTiles({ suggestions, onSelect }: Props) {
  return (
    <section className="mx-auto w-full max-w-md px-4 pt-4">
      <div className="rounded-3xl border border-gray-200 bg-white p-5 shadow-sm">
        <div className="mb-4">
          <p className="text-sm font-semibold text-gray-500">Quick replies</p>
          <h2 className="text-lg font-bold text-gray-900">Tap a response</h2>
        </div>

        <div className="grid grid-cols-1 gap-3">
          {suggestions.map((item) => (
            <button
              key={item}
              onClick={() => onSelect(item)}
              className="rounded-2xl border border-gray-200 bg-gray-50 px-4 py-4 text-left text-base font-medium text-gray-800 transition hover:bg-gray-100"
            >
              {item}
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}