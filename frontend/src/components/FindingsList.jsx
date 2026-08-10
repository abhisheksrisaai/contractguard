import { useState } from 'react';
import { ChevronDown, ChevronUp, AlertTriangle } from 'lucide-react';

const SEVERITY_COLORS = {
  CRITICAL: 'bg-red-500/20 text-red-400 border-red-500/30',
  HIGH: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
  MEDIUM: 'bg-amber-500/10 text-amber-300/80 border-amber-500/20',
  LOW: 'bg-white/5 text-white/50 border-white/10',
};
const PRIORITY_ORDER = { High: 0, Medium: 1, Low: 2 };

export default function FindingsList({ findings = [] }) {
  if (!findings || findings.length === 0) return null;

  const sorted = [...findings].sort(
    (a, b) => (PRIORITY_ORDER[a.priority || 'Low'] ?? 99) - (PRIORITY_ORDER[b.priority || 'Low'] ?? 99)
  );

  const critical = findings.filter((f) => f.severity === 'CRITICAL').length;
  const high = findings.filter((f) => f.severity === 'HIGH').length;
  const medium = findings.filter((f) => f.severity === 'MEDIUM').length;
  const low = findings.filter((f) => f.severity === 'LOW').length;

  return (
    <section className="space-y-3 animate-slide-up">
      <div className="flex items-center gap-2">
        <AlertTriangle className="w-5 h-5 text-amber-400" />
        <h3 className="text-lg font-bold text-white">Top Risk Findings</h3>
        <div className="flex gap-1.5 text-[10px] font-medium">
          {critical > 0 && <span className="text-red-400 bg-red-500/10 px-2 py-0.5 rounded-full">{critical} Critical</span>}
          {high > 0 && <span className="text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded-full">{high} High</span>}
          {medium > 0 && <span className="text-amber-300/70 bg-amber-500/5 px-2 py-0.5 rounded-full">{medium} Med</span>}
          {low > 0 && <span className="text-white/30 bg-white/5 px-2 py-0.5 rounded-full">{low} Low</span>}
        </div>
      </div>

      <div className="space-y-2">
        {sorted.map((f, i) => (
          <FindingCard key={i} finding={f} />
        ))}
      </div>
    </section>
  );
}

function FindingCard({ finding }) {
  const [expanded, setExpanded] = useState(false);
  const f = finding;
  const sevStyle = SEVERITY_COLORS[f.severity] || SEVERITY_COLORS.LOW;
  const hasExtra = f.industry_best_practice || f.suggested_negotiation || f.suggested_clause;

  return (
    <div className="card overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full text-left p-4 hover:bg-white/[0.02] transition-colors"
      >
        <div className="flex items-start gap-3">
          <span className={`text-[10px] font-bold uppercase tracking-wider shrink-0 px-2 py-0.5 rounded-full border ${sevStyle}`}>
            {f.severity}
          </span>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-white">{f.finding || f.pattern || ''}</p>
            {f.area && <p className="text-[10px] text-white/30 mt-0.5 uppercase tracking-wider">{f.area}</p>}
            {(f.why_it_matters || f.evidence) && (
              <p className="text-xs text-white/40 mt-1.5 line-clamp-2">
                {f.why_it_matters || f.evidence || ''}
              </p>
            )}
          </div>
          {hasExtra && (
            <span className="shrink-0">{expanded ? <ChevronUp className="w-4 h-4 text-white/30" /> : <ChevronDown className="w-4 h-4 text-white/30" />}</span>
          )}
        </div>
      </button>

      {expanded && hasExtra && (
        <div className="px-4 pb-4 pt-0 border-t border-white/5 space-y-3 animate-slide-up">
          {f.industry_best_practice && (
            <div className="bg-accent-500/5 rounded-lg p-3 border border-accent-500/10">
              <p className="text-[10px] uppercase tracking-wider text-accent-400 font-bold mb-1">Industry Best Practice</p>
              <p className="text-xs text-white/60">{f.industry_best_practice}</p>
            </div>
          )}
          {f.suggested_negotiation && (
            <div className="bg-emerald-500/5 rounded-lg p-3 border border-emerald-500/10">
              <p className="text-[10px] uppercase tracking-wider text-emerald-400 font-bold mb-1">Suggested Negotiation</p>
              <p className="text-xs text-white/60">{f.suggested_negotiation}</p>
            </div>
          )}
          {f.suggested_clause && (
            <div className="bg-white/5 rounded-lg p-3 border border-white/10 relative group">
              <p className="text-[10px] uppercase tracking-wider text-white/40 font-bold mb-1">Suggested Clause</p>
              <p className="text-xs text-white/50 font-mono">{f.suggested_clause}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
