import { AlertTriangle } from 'lucide-react';

const SEVERITY_ORDER = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3 };
const SEVERITY_COLORS = {
  CRITICAL: 'border-red-500/30 bg-red-500/5 text-red-400',
  HIGH: 'border-amber-500/30 bg-amber-500/5 text-amber-400',
};

export default function RedFlagBanner({ redFlags }) {
  if (!redFlags || redFlags.length === 0) return null;

  const critical = redFlags.filter((f) => f.severity === 'CRITICAL');
  const high = redFlags.filter((f) => f.severity === 'HIGH');
  const sorted = [...redFlags].sort((a, b) => (SEVERITY_ORDER[a.severity] ?? 99) - (SEVERITY_ORDER[b.severity] ?? 99));

  return (
    <div className="card p-5 border-red-500/20 bg-red-500/[0.03] animate-slide-up">
      <div className="flex items-center gap-2 mb-3">
        <AlertTriangle className="w-5 h-5 text-red-400" />
        <h3 className="font-bold text-red-400">
          {critical.length} Critical Red Flag{critical.length !== 1 ? 's' : ''} Detected
          {high.length > 0 && ` • ${high.length} High`}
        </h3>
      </div>
      <div className="space-y-2">
        {sorted.slice(0, 6).map((f, i) => {
          const sevStyle = SEVERITY_COLORS[f.severity] || 'border-white/10 bg-white/[0.02] text-white/50';
          return (
            <div key={i} className={`flex items-start gap-2.5 p-3 rounded-xl border ${sevStyle}`}>
              <span className="text-[10px] font-bold uppercase tracking-wider shrink-0 mt-0.5">{f.severity}</span>
              <div className="flex-1 min-w-0">
                <p className="text-sm">{f.pattern || f.finding || ''}</p>
                {f.evidence && <p className="text-[11px] text-white/30 mt-0.5 italic truncate">{f.evidence}</p>}
              </div>
            </div>
          );
        })}
        {sorted.length > 6 && (
          <p className="text-xs text-white/30 text-center">+{sorted.length - 6} more</p>
        )}
      </div>
    </div>
  );
}
