import { RecapCard } from "@/lib/types";

function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  if (m === 0) return `${s}s`;
  return `${m}m ${s}s`;
}

export function RecapView({ recap }: { recap: RecapCard }) {
  return (
    <div className="space-y-4 rounded-xl border border-slate-700 bg-slate-800 p-4">
      {recap.image_url && (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={recap.image_url}
          alt="Session recap visual"
          className="w-full rounded-lg object-cover"
          style={{ maxHeight: 200 }}
        />
      )}

      <p className="text-base leading-relaxed text-bridge-text">{recap.summary}</p>

      <div className="flex flex-wrap gap-2 text-sm text-bridge-muted">
        <span>{recap.turn_count} turns</span>
        <span>·</span>
        <span>{formatDuration(recap.duration_seconds)}</span>
        <span>·</span>
        <span>{Math.round(recap.prediction_accuracy * 100)}% accuracy</span>
      </div>

      {recap.topics.length > 0 && (
        <div>
          <p className="mb-1.5 text-xs font-bold uppercase tracking-wide text-bridge-muted">Topics</p>
          <div className="flex flex-wrap gap-1.5">
            {recap.topics.map((topic) => (
              <span
                key={topic}
                className="rounded-full border border-emerald-600/40 bg-emerald-600/15 px-2.5 py-0.5 text-sm text-emerald-300"
              >
                {topic}
              </span>
            ))}
          </div>
        </div>
      )}

      {recap.action_items.length > 0 && (
        <div>
          <p className="mb-1.5 text-xs font-bold uppercase tracking-wide text-bridge-muted">Action Items</p>
          <ul className="space-y-1">
            {recap.action_items.map((item) => (
              <li key={item} className="flex items-start gap-2 text-sm text-bridge-text">
                <span className="mt-0.5 text-emerald-400" aria-hidden="true">
                  ✓
                </span>
                {item}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
