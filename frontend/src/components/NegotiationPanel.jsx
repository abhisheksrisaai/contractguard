import { useState } from 'react';
import { Check, Copy } from 'lucide-react';

const PRIORITY = {
  High: 'text-red-400',
  Medium: 'text-amber-400',
  Low: 'text-white/35',
};

export default function NegotiationPanel({ opportunities = [], addToast }) {
  if (!opportunities || opportunities.length === 0) return null;

  const sorted = [...opportunities].sort((a, b) => {
    const order = { High: 0, Medium: 1, Low: 2 };
    return (order[a.priority || 'Low'] ?? 99) - (order[b.priority || 'Low'] ?? 99);
  });

  return (
    <section className="animate-slide-up">
      <div className="flex items-end justify-between gap-3 border-b border-white/10 pb-3">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-accent-400">Negotiation playbook</p>
          <h2 className="mt-1 text-xl font-semibold tracking-tight text-white">What to ask for</h2>
        </div>
        <span className="text-[10px] uppercase tracking-[0.12em] text-white/30">{opportunities.length} items</span>
      </div>

      <div className="divide-y divide-white/5 border-b border-white/5">
        {sorted.map((opportunity, index) => (
          <PlaybookRow key={index} opportunity={opportunity} index={index} addToast={addToast} />
        ))}
      </div>
    </section>
  );
}

function PlaybookRow({ opportunity, index, addToast }) {
  const [copied, setCopied] = useState(false);
  const priority = opportunity.priority || 'Medium';

  const copyClause = () => {
    if (!opportunity.suggested_clause) return;
    navigator.clipboard.writeText(opportunity.suggested_clause).then(() => {
      setCopied(true);
      addToast?.('Clause copied to clipboard', 'success');
      window.setTimeout(() => setCopied(false), 1800);
    }).catch(() => {});
  };

  return (
    <div className="grid gap-3 py-4 sm:grid-cols-[2rem_minmax(0,1fr)] sm:gap-4">
      <span className="text-[10px] tabular-nums text-white/25">{String(index + 1).padStart(2, '0')}</span>
      <div className="min-w-0">
        <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
          <p className="text-sm font-medium leading-6 text-white">{opportunity.risk}</p>
          <span className={`text-[9px] font-semibold uppercase tracking-[0.12em] ${PRIORITY[priority] || PRIORITY.Low}`}>{priority} priority</span>
        </div>

        <div className="mt-2 grid gap-3 sm:grid-cols-2">
          {opportunity.why_it_matters && (
            <div>
              <p className="text-[9px] font-semibold uppercase tracking-[0.16em] text-white/30">Why it matters</p>
              <p className="mt-1 text-xs leading-5 text-white/45">{opportunity.why_it_matters}</p>
            </div>
          )}
          {opportunity.industry_best_practice && (
            <div>
              <p className="text-[9px] font-semibold uppercase tracking-[0.16em] text-accent-400">Market standard</p>
              <p className="mt-1 text-xs leading-5 text-white/45">{opportunity.industry_best_practice}</p>
            </div>
          )}
        </div>

        {opportunity.suggested_negotiation && (
          <div className="mt-3 border-l-2 border-emerald-500/50 pl-3">
            <p className="text-[9px] font-semibold uppercase tracking-[0.16em] text-emerald-400">Ask for this</p>
            <p className="mt-1 text-sm leading-6 text-white/55">{opportunity.suggested_negotiation}</p>
          </div>
        )}

        {opportunity.suggested_clause && (
          <div className="mt-3 border-l-2 border-accent-500/50 pl-3">
            <div className="flex items-center justify-between gap-3">
              <p className="text-[9px] font-semibold uppercase tracking-[0.16em] text-accent-400">Suggested language</p>
              <button
                type="button"
                onClick={copyClause}
                className="inline-flex items-center gap-1 text-[10px] text-white/30 transition hover:text-white"
              >
                {copied ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
                {copied ? 'Copied' : 'Copy'}
              </button>
            </div>
            <p className="mt-1 whitespace-pre-wrap break-words text-xs leading-6 text-white/45">{opportunity.suggested_clause}</p>
          </div>
        )}
      </div>
    </div>
  );
}
