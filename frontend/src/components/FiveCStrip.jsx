import { CheckCircle, AlertTriangle, XCircle } from 'lucide-react';

const C_CONFIG = ['capacity', 'consent', 'consideration', 'clarity', 'compliance'];

function StatusIcon({ status }) {
  if (status === 'Pass') return <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0" />;
  if (status === 'Fail') return <XCircle className="w-4 h-4 text-red-400 shrink-0" />;
  return <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />;
}

export default function FiveCStrip({ fiveC }) {
  if (!fiveC) return null;

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2">
      {C_CONFIG.map((c) => {
        const data = fiveC[c];
        if (!data) return null;
        const score = data.score ?? 0;
        const status = data.status || 'Partial';
        return (
          <div
            key={c}
            className="flex flex-col items-center gap-1.5 px-2.5 py-3 rounded-xl bg-white/[0.03] border border-white/5 min-h-[72px] justify-center"
          >
            <StatusIcon status={status} />
            <p className="text-[10px] uppercase tracking-wider text-white/40 truncate w-full text-center">{c}</p>
            <p className="text-sm font-bold text-white leading-none">{score}<span className="text-white/20 text-[10px]">/100</span></p>
          </div>
        );
      })}
    </div>
  );
}
