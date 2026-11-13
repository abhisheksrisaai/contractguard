import { useState } from 'react';
import {
  AlertTriangle, CheckCircle2, Clock, MessageCircle, Shield,
} from 'lucide-react';
import ContractTypeBadge from '../ContractTypeBadge';

const FIVE_C = ['capacity', 'consent', 'consideration', 'clarity', 'compliance'];
const FIVE_C_LABELS = {
  capacity: 'Capacity',
  consent: 'Consent',
  consideration: 'Consideration',
  clarity: 'Clarity',
  compliance: 'Compliance',
};

const PROVIDER_LABELS = {
  groq: 'Qwen 3.8 27B',
};

export function scoreBand(score) {
  if (score >= 75) {
    return {
      key: 'high',
      word: 'High risk',
      action: 'Renegotiate',
      summary: 'Major concerns. Significant changes are required before signing.',
      text: 'text-red-400',
      bar: 'bg-red-500',
      soft: 'bg-red-500/10',
      border: 'border-red-500/20',
    };
  }
  if (score >= 45) {
    return {
      key: 'medium',
      word: 'Medium risk',
      action: 'Proceed with caution',
      summary: 'Several areas of concern. Negotiate the key clauses first.',
      text: 'text-amber-400',
      bar: 'bg-amber-500',
      soft: 'bg-amber-500/10',
      border: 'border-amber-500/20',
    };
  }
  return {
    key: 'low',
    word: 'Low risk',
    action: 'Proceed',
    summary: 'The agreement appears generally balanced and fair.',
    text: 'text-emerald-400',
    bar: 'bg-emerald-500',
    soft: 'bg-emerald-500/10',
    border: 'border-emerald-500/20',
  };
}

function providerLine(analysis) {
  const providers = analysis?.ai_providers?.length
    ? analysis.ai_providers
    : analysis?.ai_provider && analysis.ai_provider !== 'fallback'
      ? [analysis.ai_provider]
      : [];
  const labels = providers.map((provider) => PROVIDER_LABELS[provider] || provider);
  if (labels.length === 0) return null;
  if (labels.length === 1) return labels[0];
  return `${labels[0]} + ${labels.length - 1} fallback${labels.length > 2 ? 's' : ''}`;
}

export default function RiskBrief({ analysis, isPartial }) {
  const [openC, setOpenC] = useState(null);
  const score = Math.round(analysis?.overall_score ?? 0);
  const breakdown = analysis?.risk_breakdown || { High: 0, Medium: 0, Low: 0 };
  const band = scoreBand(score);
  const total = analysis?.total_clauses || 0;
  const analyzed = analysis?.analyzed_clause_count ?? total;
  const failed = analysis?.failed_clause_count || 0;
  const fiveC = analysis?.five_c;
  const fiveCUnavailable = analysis?.five_c_status === 'unavailable'
    || (fiveC && FIVE_C.every((key) => fiveC?.[key]?.score == null));
  const fiveCPartial = !fiveCUnavailable && analysis?.five_c_status === 'partial';
  const fiveCPass = fiveC
    ? FIVE_C.filter((key) => fiveC?.[key]?.status === 'Pass').length
    : 0;
  const provider = providerLine(analysis);
  const completedAt = analysis?.analysis_time_seconds;

  return (
    <section
      className="overflow-hidden rounded-2xl border border-white/10 bg-white/[0.02] animate-slide-up"
      data-analysis-status={analysis?.analysis_status || 'unknown'}
      data-five-c-status={analysis?.five_c_status || 'unknown'}
    >
      {/* Case-file strip */}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 border-b border-white/10 px-5 py-4 sm:px-6">
        <span className="text-[10px] font-semibold uppercase tracking-[0.18em] text-accent-400">Risk brief</span>
        <span className="min-w-0 max-w-full truncate text-sm font-medium text-white/75">{analysis?.filename || 'Contract'}</span>
        <ContractTypeBadge contractType={analysis?.contract_type} confidence={analysis?.type_confidence} />
        <div className="ml-auto flex flex-wrap items-center gap-x-4 gap-y-1 text-[10px] uppercase tracking-[0.12em] text-white/30">
          <span className="inline-flex items-center gap-1.5">
            {isPartial ? <AlertTriangle className="h-3 w-3 text-amber-400" /> : <CheckCircle2 className="h-3 w-3 text-emerald-400" />}
            {isPartial ? 'Partial' : 'Complete'}
          </span>
          {completedAt != null && <span className="inline-flex items-center gap-1.5"><Clock className="h-3 w-3" />{completedAt}s</span>}
          {provider && <span className="normal-case tracking-normal text-white/35">{provider}</span>}
        </div>
      </div>

      {isPartial && (
        <div className="flex items-start gap-3 border-b border-amber-500/15 bg-amber-500/[0.06] px-5 py-3 sm:px-6">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-400" />
          <div>
            <p className="text-xs font-semibold text-amber-300">Partial analysis</p>
            <p className="mt-0.5 text-xs leading-5 text-amber-200/60">
              {failed} of {total} clauses could not be scored after retries. They are marked Review and excluded from the overall score. The score covers the {analyzed} analyzed clauses.
            </p>
          </div>
        </div>
      )}

      <div className="grid lg:grid-cols-[minmax(0,0.92fr)_minmax(0,1.08fr)]">
        {/* Score + distribution */}
        <div className="p-5 sm:p-7 lg:border-r lg:border-white/10">
          <div className="flex items-end gap-3">
            <span className={`text-6xl font-semibold leading-none tracking-[-0.06em] tabular-nums sm:text-7xl ${band.text}`}>{score}</span>
            <div className="pb-1">
              <span className="text-xl font-medium text-white/20">/100</span>
              <p className="text-[9px] uppercase tracking-[0.16em] text-white/30">Overall risk</p>
            </div>
          </div>

          <div className="mt-3 flex flex-wrap items-baseline gap-x-2 gap-y-1">
            <span className={`text-sm font-semibold ${band.text}`}>{band.word}</span>
            <span className="text-white/20">/</span>
            <span className={`text-sm font-medium ${band.text}`}>{band.action}</span>
            {analysis?.confidence != null && (
              <span className="ml-auto text-[10px] uppercase tracking-[0.12em] text-white/25">Confidence {analysis.confidence}%</span>
            )}
          </div>

          <p className="mt-2 max-w-lg text-sm leading-6 text-white/50">
            {analysis?.executive_summary || analysis?.assessment || band.summary}
          </p>

          <RiskScale score={score} band={band} />

          <div className="mt-6 grid grid-cols-3 divide-x divide-white/10 border-y border-white/10">
            <RiskCount label="High" value={breakdown.High || 0} tone="text-red-400" rule="bg-red-500" />
            <RiskCount label="Medium" value={breakdown.Medium || 0} tone="text-amber-400" rule="bg-amber-500" />
            <RiskCount label="Low" value={breakdown.Low || 0} tone="text-emerald-400" rule="bg-emerald-500" />
          </div>
        </div>

        {/* 5C validation */}
        <div className="p-5 sm:p-7">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-white/30">Enforceability</p>
              <h3 className="mt-1 flex items-center gap-2 text-sm font-semibold text-white">
                <Shield className="h-4 w-4 text-accent-400" /> 5C validation
              </h3>
            </div>
            <span className={`text-[10px] uppercase tracking-[0.12em] ${fiveCUnavailable ? 'text-amber-400/70' : 'text-white/30'}`}>
              {fiveCUnavailable ? 'Not scored' : fiveCPartial ? 'Partial check' : `${fiveCPass}/5 pass`}
            </span>
          </div>

          {fiveCPartial && (
            <p className="mt-4 text-[11px] leading-5 text-amber-400/60">
              Some checks were not returned this run and are marked unavailable. Scored rows are unaffected.
            </p>
          )}

          {fiveCUnavailable ? (
            <div className="mt-5 rounded-xl border border-white/10 bg-white/[0.02] p-4">
              <p className="text-sm font-medium text-white/65">5C check unavailable this run</p>
              <p className="mt-1 text-xs leading-5 text-white/35">
                The model could not complete this check, so no score is shown. Clause-level scoring is unaffected.
              </p>
            </div>
          ) : (
            <div className="mt-4">
              {FIVE_C.map((key, index) => {
                const data = fiveC?.[key] || {};
                const scoreValue = data.score;
                const status = data.status || 'Unavailable';
                const issues = data.issues || [];
                const tone = status === 'Pass'
                  ? 'text-emerald-400'
                  : status === 'Fail'
                    ? 'text-red-400'
                    : status === 'Partial'
                      ? 'text-amber-400'
                      : 'text-white/30';
                const dot = status === 'Pass'
                  ? 'bg-emerald-500'
                  : status === 'Fail'
                    ? 'bg-red-500'
                    : status === 'Partial'
                      ? 'bg-amber-500'
                      : 'bg-white/20';
                const open = openC === key;
                return (
                  <div key={key} className="border-b border-white/5 last:border-0">
                    <button
                      type="button"
                      onClick={() => setOpenC(open ? null : key)}
                      className="grid w-full grid-cols-[1.5rem_minmax(0,1fr)_minmax(4rem,0.8fr)_2.5rem] items-center gap-3 py-3 text-left transition-colors hover:bg-white/[0.02]"
                      aria-expanded={open}
                    >
                      <span className="text-[10px] tabular-nums text-white/25">{String(index + 1).padStart(2, '0')}</span>
                      <span className="flex min-w-0 items-center gap-2">
                        <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${dot}`} />
                        <span className="truncate text-xs font-medium text-white/70">{FIVE_C_LABELS[key]}</span>
                        <span className={`hidden text-[9px] uppercase tracking-[0.12em] sm:inline ${tone}`}>{status}</span>
                      </span>
                      <span className="flex items-center gap-2">
                        <span className="h-1 flex-1 bg-white/10">
                          <span
                            className={`block h-full ${status === 'Pass' ? 'bg-emerald-500' : status === 'Fail' ? 'bg-red-500' : status === 'Partial' ? 'bg-amber-500' : 'bg-white/20'}`}
                            style={{ width: `${scoreValue ?? 0}%` }}
                          />
                        </span>
                        <span className={`w-8 text-right text-xs tabular-nums ${scoreValue == null ? 'text-white/25' : 'text-white/60'}`}>
                          {scoreValue ?? '—'}
                        </span>
                      </span>
                      <span className={`text-[9px] uppercase tracking-[0.1em] sm:hidden ${tone}`}>{status}</span>
                    </button>
                    {open && (
                      <div className="pb-3 pl-6 pr-1">
                        {issues.length > 0 ? (
                          <ul className="space-y-1.5 border-l border-white/10 pl-3">
                            {issues.map((issue, issueIndex) => (
                              <li key={issueIndex} className="text-xs leading-5 text-white/40">{issue}</li>
                            ))}
                          </ul>
                        ) : (
                          <p className="text-xs text-white/30">No specific issues recorded.</p>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          <div className="mt-4 flex items-center justify-between gap-3 border-t border-white/5 pt-4">
            <p className="text-[10px] leading-4 text-white/25">
              Tap a test to read the model's notes.
            </p>
            <a
              href="#clause-register"
              className="inline-flex shrink-0 items-center gap-1 text-[10px] font-medium text-accent-400 transition hover:text-accent-300"
            >
              <MessageCircle className="h-3 w-3" /> Clause register
            </a>
          </div>
        </div>
      </div>
    </section>
  );
}

function RiskScale({ score, band }) {
  return (
    <div className="mt-6">
      <div className="relative h-1.5 w-full bg-white/10">
        <div className="absolute inset-y-0 left-0 bg-emerald-500/35" style={{ width: '45%' }} />
        <div className="absolute inset-y-0 left-[45%] bg-amber-500/45" style={{ width: '30%' }} />
        <div className="absolute inset-y-0 left-[75%] right-0 bg-red-500/55" />
        <div
          className="absolute -top-1.5 h-4 w-0.5 bg-white shadow-[0_0_0_3px_rgba(255,255,255,0.08)]"
          style={{ left: `calc(${Math.max(0, Math.min(100, score))}% - 1px)` }}
        />
      </div>
      <div className="mt-2 flex items-center justify-between text-[9px] uppercase tracking-[0.14em] text-white/25">
        <span>Low</span>
        <span>Medium</span>
        <span>High</span>
      </div>
      <p className={`mt-1 text-[10px] font-medium ${band.text}`}>{score}/100 contract risk score</p>
    </div>
  );
}

function RiskCount({ label, value, tone, rule }) {
  return (
    <div className="px-3 py-3 first:pl-0 last:pr-0">
      <div className={`mb-2 h-0.5 w-6 ${rule}`} />
      <div className="flex items-baseline gap-1.5">
        <span className={`text-xl font-semibold tabular-nums ${tone}`}>{value}</span>
        <span className="text-[10px] uppercase tracking-[0.12em] text-white/30">{label}</span>
      </div>
    </div>
  );
}
