import { AlertTriangle, AlertCircle, CheckCircle2, Hash } from 'lucide-react';

/**
 * StatsBar — Row of stat badges showing High/Medium/Low risk counts.
 *
 * @param {Object} props
 * @param {Object} props.breakdown — { High: number, Medium: number, Low: number }
 * @param {number} [props.total] — Total clauses
 */
const STATS = [
  { key: 'High',   icon: AlertTriangle, color: 'text-red-500',   bg: 'bg-red-50',   border: 'border-red-200', ring: 'bg-red-500' },
  { key: 'Medium', icon: AlertCircle,   color: 'text-amber-500', bg: 'bg-amber-50', border: 'border-amber-200', ring: 'bg-amber-500' },
  { key: 'Low',    icon: CheckCircle2,  color: 'text-emerald-500', bg: 'bg-emerald-50', border: 'border-emerald-200', ring: 'bg-emerald-500' },
];

export default function StatsBar({ breakdown = {}, total }) {
  const clauses = total || Object.values(breakdown).reduce((a, b) => a + b, 0);

  return (
    <div className="flex flex-wrap items-center gap-2 sm:gap-3 md:gap-4">
      {STATS.map(({ key, icon: Icon, color, bg, border, ring }) => {
        const count = breakdown[key] || 0;
        const pct = clauses > 0 ? Math.round((count / clauses) * 100) : 0;

        return (
          <div
            key={key}
            className={`
              flex items-center gap-3 px-4 py-3 rounded-xl border shadow-sm
              transition-all duration-200 hover:shadow-md
              ${bg} ${border}
            `}
          >
            <div className={`w-8 h-8 rounded-lg ${bg} flex items-center justify-center`}>
              <Icon className={`w-4 h-4 ${color}`} />
            </div>
            <div>
              <div className="flex items-baseline gap-1.5">
                <span className="text-xl font-extrabold text-slate-800">{count}</span>
                <span className="text-xs font-medium text-slate-400">{key}</span>
              </div>
              <div className="flex items-center gap-1.5 mt-0.5">
                <div className="w-12 h-1 bg-slate-200 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${ring}`}
                    style={{ width: `${pct}%` }}
                  />
                </div>
                <span className="text-[10px] text-slate-400">{pct}%</span>
              </div>
            </div>
          </div>
        );
      })}

      <div className="flex items-center gap-2 px-4 py-3 rounded-xl border border-slate-200 bg-white shadow-sm">
        <Hash className="w-4 h-4 text-slate-400" />
        <span className="text-sm font-semibold text-slate-500">
          {clauses} clause{clauses !== 1 ? 's' : ''}
        </span>
      </div>
    </div>
  );
}
