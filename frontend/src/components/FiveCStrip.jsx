import { CheckCircle, AlertTriangle, XCircle } from 'lucide-react';

const C_CONFIG = ['capacity', 'consent', 'consideration', 'clarity', 'compliance'];

function StatusIcon({ status }) {
  if (status === 'Pass') return <CheckCircle className="w-4 h-4 text-emerald-400" />;
  if (status === 'Fail') return <XCircle className="w-4 h-4 text-red-400" />;
  return <AlertTriangle className="w-4 h-4 text-amber-400" />;
}

export default function FiveCStrip({ fiveC }) {
  if (!fiveC) return null;

  return (
    <div className="flex flex-wrap gap-2">
      {C_CONFIG.map((c) => {
        const data = fiveC[c];
        if (!data) return null;
        const score = data.score ?? 0;
        const status = data.status || 'Partial';
        return (
          <div key={c} className="flex items-center gap-2 px-3 py-2 rounded-xl bg-white/[0.03] border border-white/5 min-w-[80px] flex-1">
            <StatusIcon status={status} />
            <div className="flex-1 min-w-0">
              <p className="text-[10px] uppercase tracking-wider text-white/40">{c}</p>
              <p className="text-sm font-bold text-white">{score}<span className="text-white/20 text-[10px]">/100</span></p>
            </div>
          </div>
        );
      })}
    </div>
  );
}
