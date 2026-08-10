import { useState, useEffect, useRef } from 'react';
import { CheckCircle, Loader, FileText, Search, Shield, GitCompare, BarChart3, Info } from 'lucide-react';

const STEPS = [
  { label: 'Extracting text from PDF', icon: FileText, desc: 'Reading document structure and extracting every clause' },
  { label: 'Detecting contract type', icon: Search, desc: 'Identifying agreement type for tailored analysis' },
  { label: 'Running 5C enforceability validation', icon: Shield, desc: 'Checking Capacity, Consent, Consideration, Clarity & Compliance' },
  { label: 'Analyzing clauses with AI', icon: Loader, desc: 'Scoring risk levels and identifying red flags per clause' },
  { label: 'Benchmarking against fair standards', icon: GitCompare, desc: 'Comparing against 50 fair-clause templates' },
  { label: 'Scoring risks & building report', icon: BarChart3, desc: 'Aggregating findings into your negotiation playbook' },
];

export default function AnalysisProgress() {
  const [step, setStep] = useState(0);
  const [elapsed, setElapsed] = useState(0);
  const intervalRef = useRef(null);
  const tickRef = useRef(null);

  useEffect(() => {
    // Advance steps on a timer (~8.5s each)
    intervalRef.current = setInterval(() => {
      setStep((s) => Math.min(s + 1, STEPS.length - 1));
    }, 8500);

    tickRef.current = setInterval(() => {
      setElapsed((e) => e + 1);
    }, 1000);

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
      if (tickRef.current) clearInterval(tickRef.current);
    };
  }, []);

  const progressPct = Math.min(95, (step / (STEPS.length - 1)) * 100 + (step > 0 ? 10 : 0));

  return (
    <div className="max-w-xl mx-auto px-4 py-12 animate-scale-in">
      <div className="text-center mb-8">
        <h2 className="text-xl font-bold text-white mb-1">Analyzing Your Contract</h2>
        <p className="text-sm text-white/40">This takes about 50 seconds — hang tight</p>
      </div>

      {/* Progress bar */}
      <div className="h-1.5 bg-white/10 rounded-full overflow-hidden mb-8">
        <div
          className="h-full bg-accent-500 rounded-full transition-all duration-700 ease-out"
          style={{ width: `${progressPct}%` }}
        />
      </div>

      {/* Steps */}
      <div className="space-y-1">
        {STEPS.map((s, i) => {
          const completed = i < step;
          const active = i === step;
          const pending = i > step;

          return (
            <div
              key={i}
              className={`flex items-center gap-3 py-3 px-4 rounded-xl transition-all duration-500 ${
                active ? 'bg-white/[0.03] border border-white/10' : ''
              }`}
            >
              <div
                className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 transition-all duration-300 ${
                  completed
                    ? 'bg-emerald-500/20 text-emerald-400'
                    : active
                      ? 'bg-accent-500/20 text-accent-400 animate-pulse'
                      : 'bg-white/5 text-white/20'
                }`}
              >
                {completed ? <CheckCircle className="w-4 h-4" /> : <s.icon className={`w-4 h-4 ${active ? '' : ''}`} />}
              </div>
              <div className="flex-1">
                <p
                  className={`text-sm font-medium transition-colors duration-300 ${
                    completed ? 'text-white/60' : pending ? 'text-white/20' : 'text-white'
                  }`}
                >
                  {s.label}
                </p>
                {active && (
                  <p className="text-[11px] text-white/30 mt-0.5 animate-fade-in">{s.desc}</p>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Cold start note */}
      {elapsed > 20 && (
        <div className="mt-6 bg-amber-500/5 border border-amber-500/10 rounded-xl p-3 flex items-start gap-2 animate-fade-in">
          <Info className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
          <p className="text-xs text-amber-300/80">
            Free cloud server may be waking up — first analysis can take a little longer. Subsequent analyses are faster.
          </p>
        </div>
      )}
    </div>
  );
}
