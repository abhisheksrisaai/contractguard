import { useState } from 'react';
import { Copy, Check } from 'lucide-react';

const PRIORITY_COLORS = {
  High: 'border-red-500/20 bg-red-500/5',
  Medium: 'border-amber-500/20 bg-amber-500/5',
  Low: 'border-white/10 bg-white/[0.02]',
};

export default function NegotiationPanel({ opportunities = [], addToast }) {
  if (!opportunities || opportunities.length === 0) return null;

  const sorted = [...opportunities].sort((a, b) => {
    const order = { High: 0, Medium: 1, Low: 2 };
    return (order[a.priority || 'Low'] ?? 99) - (order[b.priority || 'Low'] ?? 99);
  });

  return (
    <section className="space-y-3 animate-slide-up">
      <h3 className="text-lg font-bold text-white flex items-center gap-2">
        <span className="w-2 h-2 rounded-full bg-accent-400 shrink-0" />
        Negotiation Playbook
        <span className="text-sm font-normal text-white/30">({opportunities.length} items)</span>
      </h3>

      <div className="grid gap-3">
        {sorted.map((op, i) => (
          <NegotiationCard key={i} op={op} addToast={addToast} />
        ))}
      </div>
    </section>
  );
}

function NegotiationCard({ op, addToast }) {
  const [copied, setCopied] = useState(false);
  const borderStyle = PRIORITY_COLORS[op.priority] || PRIORITY_COLORS.Low;

  const handleCopy = (text) => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      addToast?.('Clause copied to clipboard', 'success');
      setTimeout(() => setCopied(false), 2000);
    }).catch(() => {});
  };

  return (
    <div className={`card overflow-hidden border ${borderStyle}`}>
      <div className="p-4 space-y-3">
        <div className="flex items-center gap-2 flex-wrap">
          <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full border shrink-0 ${
            op.priority === 'High' ? 'bg-red-500/10 text-red-400 border-red-500/20' :
            op.priority === 'Medium' ? 'bg-amber-500/10 text-amber-400 border-amber-500/20' :
            'bg-white/5 text-white/40 border-white/10'
          }`}>
            {op.priority || 'Medium'} priority
          </span>
        </div>

        <p className="text-sm font-semibold text-white break-words">{op.risk}</p>

        <div className="space-y-2">
          {op.why_it_matters && (
            <div>
              <p className="text-[10px] uppercase tracking-wider text-white/30 font-bold mb-0.5">Why it matters</p>
              <p className="text-xs text-white/50 break-words">{op.why_it_matters}</p>
            </div>
          )}

          {op.industry_best_practice && (
            <div>
              <p className="text-[10px] uppercase tracking-wider text-accent-400 font-bold mb-0.5">Industry standard</p>
              <p className="text-xs text-white/50 break-words">{op.industry_best_practice}</p>
            </div>
          )}

          {op.suggested_negotiation && (
            <div>
              <p className="text-[10px] uppercase tracking-wider text-emerald-400 font-bold mb-0.5">Suggested negotiation</p>
              <p className="text-xs text-white/60 break-words">{op.suggested_negotiation}</p>
            </div>
          )}

          {op.suggested_clause && (
            <div className="bg-white/[0.03] rounded-lg border border-white/10 relative">
              <div className="flex items-center justify-between px-3 pt-2.5 pb-1">
                <p className="text-[10px] uppercase tracking-wider text-white/30 font-bold">Suggested clause</p>
                <button
                  onClick={() => handleCopy(op.suggested_clause)}
                  className="p-1.5 rounded-md bg-white/5 hover:bg-white/10 transition text-white/30 hover:text-white shrink-0"
                  title="Copy clause"
                >
                  {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                </button>
              </div>
              <div className="overflow-x-auto px-3 pb-3">
                <p className="text-xs text-white/40 font-mono leading-relaxed whitespace-pre-wrap break-words min-w-0">{op.suggested_clause}</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
