import { useState } from 'react';
import { AlertTriangle, ChevronDown, ChevronUp } from 'lucide-react';

const SEVERITY = {
  CRITICAL: 'text-red-400',
  HIGH: 'text-amber-400',
  MEDIUM: 'text-amber-300/80',
  LOW: 'text-white/35',
};
const PRIORITY_ORDER = { High: 0, Medium: 1, Low: 2 };

export default function FindingsList({ findings = [] }) {
  if (!findings || findings.length === 0) return null;

  const sorted = [...findings].sort(
    (a, b) => (PRIORITY_ORDER[a.priority || 'Low'] ?? 99) - (PRIORITY_ORDER[b.priority || 'Low'] ?? 99)
  );

  const critical = findings.filter((finding) => finding.severity === 'CRITICAL').length;
  const high = findings.filter((finding) => finding.severity === 'HIGH').length;
  const medium = findings.filter((finding) => finding.severity === 'MEDIUM').length;
  const low = findings.filter((finding) => finding.severity === 'LOW').length;

  return (
    <section className="animate-slide-up">
      <div className="flex flex-col gap-3 border-b border-white/10 pb-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-accent-400">Top risk findings</p>
          <h2 className="mt-1 flex items-center gap-2 text-xl font-semibold tracking-tight text-white">
            <AlertTriangle className="h-4 w-4 text-amber-400" /> What needs attention
          </h2>
        </div>
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[10px] uppercase tracking-[0.12em]">
          {critical > 0 && <span className="text-red-400">{critical} critical</span>}
          {high > 0 && <span className="text-amber-400">{high} high</span>}
          {medium > 0 && <span className="text-amber-300/70">{medium} medium</span>}
          {low > 0 && <span className="text-white/30">{low} low</span>}
        </div>
      </div>

      <div className="divide-y divide-white/5 border-b border-white/5">
        {sorted.map((finding, index) => (
          <FindingRow key={index} finding={finding} index={index} />
        ))}
      </div>
    </section>
  );
}

function FindingRow({ finding, index }) {
  const [expanded, setExpanded] = useState(false);
  const hasExtra = Boolean(
    finding.industry_best_practice
    || finding.suggested_negotiation
    || finding.suggested_clause
  );
  const severity = finding.severity || 'LOW';

  return (
    <div>
      <button
        type="button"
        onClick={() => hasExtra && setExpanded(!expanded)}
        className={`grid w-full grid-cols-[1.5rem_minmax(0,1fr)_auto_1rem] items-start gap-3 py-4 text-left transition-colors sm:grid-cols-[2rem_minmax(0,1fr)_4.5rem_1rem] ${
          hasExtra ? 'hover:bg-white/[0.02]' : 'cursor-default'
        }`}
        aria-expanded={hasExtra ? expanded : undefined}
      >
        <span className="mt-0.5 text-[10px] tabular-nums text-white/25">{String(index + 1).padStart(2, '0')}</span>
        <span className="min-w-0">
          <span className="block text-sm font-medium leading-6 text-white break-words">
            {finding.finding || finding.pattern || 'Untitled finding'}
          </span>
          {finding.area && (
            <span className="mt-0.5 block text-[9px] uppercase tracking-[0.14em] text-white/30">{finding.area}</span>
          )}
          {(finding.why_it_matters || finding.evidence) && (
            <span className="mt-1.5 line-clamp-2 block text-xs leading-5 text-white/40">
              {finding.why_it_matters || finding.evidence}
            </span>
          )}
        </span>
        <span className={`pt-0.5 text-right text-[10px] font-semibold uppercase tracking-[0.12em] ${SEVERITY[severity] || SEVERITY.LOW}`}>
          {severity}
        </span>
        {hasExtra ? (
          expanded ? <ChevronUp className="mt-1 h-4 w-4 justify-self-end text-white/25" /> : <ChevronDown className="mt-1 h-4 w-4 justify-self-end text-white/25" />
        ) : (
          <span aria-hidden="true" />
        )}
      </button>

      {expanded && hasExtra && (
        <div className="grid gap-5 border-t border-white/5 bg-white/[0.02] px-4 py-4 sm:grid-cols-2 sm:px-8">
          {finding.industry_best_practice && (
            <div>
              <p className="text-[9px] font-semibold uppercase tracking-[0.16em] text-accent-400">Industry standard</p>
              <p className="mt-1.5 text-sm leading-6 text-white/50">{finding.industry_best_practice}</p>
            </div>
          )}
          {finding.suggested_negotiation && (
            <div>
              <p className="text-[9px] font-semibold uppercase tracking-[0.16em] text-emerald-400">Suggested negotiation</p>
              <p className="mt-1.5 text-sm leading-6 text-white/50">{finding.suggested_negotiation}</p>
            </div>
          )}
          {finding.suggested_clause && (
            <div className="border-l-2 border-white/15 pl-4 sm:col-span-2">
              <p className="text-[9px] font-semibold uppercase tracking-[0.16em] text-white/30">Suggested clause</p>
              <p className="mt-1.5 whitespace-pre-wrap break-words text-xs leading-6 text-white/45">{finding.suggested_clause}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
