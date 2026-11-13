import { AlertTriangle } from 'lucide-react';

export default function MissingClauses({ missingClauses = [] }) {
  if (!missingClauses || missingClauses.length === 0) return null;

  return (
    <section className="border-y border-white/10 py-4 animate-slide-up">
      <div className="flex items-center gap-2">
        <AlertTriangle className="h-4 w-4 text-amber-400" />
        <h2 className="text-sm font-semibold text-white">Missing clauses</h2>
        <span className="text-[10px] tabular-nums text-white/30">{missingClauses.length}</span>
      </div>
      <div className="mt-3 flex flex-wrap gap-x-6 gap-y-2">
        {missingClauses.map((item, index) => (
          <span key={index} className="inline-flex items-center gap-2 text-sm text-white/50">
            <span className="h-1 w-1 shrink-0 bg-amber-500" />
            {item}
          </span>
        ))}
      </div>
    </section>
  );
}
