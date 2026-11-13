import { AlertTriangle } from 'lucide-react';

const SEVERITY_ORDER = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3 };
const SEVERITY_COLORS = {
  CRITICAL: 'text-red-400',
  HIGH: 'text-amber-400',
  MEDIUM: 'text-white/45',
  LOW: 'text-white/30',
};

function truncateAtWord(text, max) {
  if (!text || text.length <= max) return text;
  const cut = text.slice(0, max);
  const lastSpace = cut.lastIndexOf(' ');
  return (lastSpace > max * 0.6 ? cut.slice(0, lastSpace) : cut) + '…';
}

export default function RedFlagBanner({ redFlags }) {
  if (!redFlags || redFlags.length === 0) return null;

  const critical = redFlags.filter((flag) => flag.severity === 'CRITICAL');
  const high = redFlags.filter((flag) => flag.severity === 'HIGH');
  if (critical.length === 0 && high.length === 0) return null;

  const sorted = [...redFlags].sort(
    (a, b) => (SEVERITY_ORDER[a.severity] ?? 99) - (SEVERITY_ORDER[b.severity] ?? 99)
  );

  return (
    <section className="border-y border-white/10 py-4 animate-slide-up">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        <AlertTriangle className="h-4 w-4 text-amber-400" />
        <h2 className="text-sm font-semibold text-white">Automated risk flags</h2>
        <span className="text-[9px] uppercase tracking-[0.14em] text-white/25">Rule scan, not legal advice</span>
        <span className="ml-auto text-[10px] uppercase tracking-[0.12em] text-white/30">
          {critical.length > 0 && <span className="text-red-400">{critical.length} critical</span>}
          {critical.length > 0 && high.length > 0 && <span className="text-white/20"> / </span>}
          {high.length > 0 && <span className="text-amber-400">{high.length} high</span>}
        </span>
      </div>

      <div className="mt-3 divide-y divide-white/5 border-y border-white/5">
        {sorted.slice(0, 6).map((flag, index) => (
          <div key={index} className="grid gap-2 py-3 sm:grid-cols-[4.5rem_minmax(0,1fr)_minmax(0,0.9fr)] sm:gap-4">
            <span className={`text-[10px] font-semibold uppercase tracking-[0.12em] ${SEVERITY_COLORS[flag.severity] || SEVERITY_COLORS.MEDIUM}`}>
              {flag.severity || 'MEDIUM'}
            </span>
            <p className="text-sm leading-6 text-white/65">{flag.pattern || flag.finding || ''}</p>
            {flag.evidence ? (
              <p className="text-xs leading-5 text-white/30">{truncateAtWord(flag.evidence, 150)}</p>
            ) : (
              <span />
            )}
          </div>
        ))}
      </div>
      {sorted.length > 6 && (
        <p className="mt-2 text-[10px] uppercase tracking-[0.12em] text-white/25">+{sorted.length - 6} more flags in the report</p>
      )}
    </section>
  );
}
