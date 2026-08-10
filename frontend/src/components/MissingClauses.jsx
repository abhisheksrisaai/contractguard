import { AlertTriangle } from 'lucide-react';

export default function MissingClauses({ missingClauses = [] }) {
  if (!missingClauses || missingClauses.length === 0) return null;

  return (
    <div className="card p-4 animate-slide-up">
      <div className="flex items-center gap-2 mb-3">
        <AlertTriangle className="w-4 h-4 text-amber-400" />
        <h3 className="text-sm font-bold text-white">Missing Clauses</h3>
        <span className="text-[10px] text-white/30">({missingClauses.length})</span>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {missingClauses.map((mc, i) => (
          <span key={i} className="text-[11px] bg-amber-500/10 text-amber-300/80 border border-amber-500/20 px-2.5 py-1 rounded-full">
            {mc}
          </span>
        ))}
      </div>
    </div>
  );
}
