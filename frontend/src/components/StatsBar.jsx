import { AlertTriangle, AlertCircle, CheckCircle2, Hash } from 'lucide-react';

const STATS = [
  { key: 'High',   icon: AlertTriangle, color: 'text-red-400',   bg: 'bg-red-500/10',   border: 'border-red-500/20', ring: 'bg-red-500' },
  { key: 'Medium', icon: AlertCircle,   color: 'text-amber-400', bg: 'bg-amber-500/10', border: 'border-amber-500/20', ring: 'bg-amber-500' },
  { key: 'Low',    icon: CheckCircle2,  color: 'text-emerald-400', bg: 'bg-emerald-500/10', border: 'border-emerald-500/20', ring: 'bg-emerald-500' },
];

export default function StatsBar({ breakdown = {}, total }) {
  const clauses = total || Object.values(breakdown).reduce((a, b) => a + b, 0);

  return (
    <div className="flex flex-wrap items-center gap-3">
      {STATS.map(({ key, icon: Icon, color, bg, border, ring }) => {
        const count = breakdown[key] || 0;
        const pct = clauses > 0 ? Math.round((count / clauses) * 100) : 0;
        return (
          <div key={key} className={`flex items-center gap-3 px-4 py-3 rounded-xl border transition-all duration-200 ${bg} ${border}`}>
            <div className={`w-8 h-8 rounded-lg ${bg} flex items-center justify-center`}><Icon className={`w-4 h-4 ${color}`} /></div>
            <div>
              <div className="flex items-baseline gap-1.5">
                <span className="text-xl font-extrabold text-white">{count}</span>
                <span className="text-xs font-medium text-white/40">{key}</span>
              </div>
              <div className="flex items-center gap-1.5 mt-0.5">
                <div className="w-12 h-1 bg-white/10 rounded-full overflow-hidden"><div className={`h-full rounded-full ${ring}`} style={{ width: `${pct}%` }} /></div>
                <span className="text-[10px] text-white/30">{pct}%</span>
              </div>
            </div>
          </div>
        );
      })}
      <div className="flex items-center gap-2 px-4 py-3 rounded-xl border border-white/10 bg-white/[0.02]">
        <Hash className="w-4 h-4 text-white/30" />
        <span className="text-sm font-semibold text-white/50">{clauses} clause{clauses !== 1 ? 's' : ''}</span>
      </div>
    </div>
  );
}
