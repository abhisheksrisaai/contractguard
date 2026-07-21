import { useState } from 'react';
import {
  ChevronDown, ChevronUp, AlertTriangle, Lightbulb, BookOpen, Shield, Gavel,
} from 'lucide-react';

/**
 * ClauseAccordion — Expandable clause card with risk badge, explanation,
 * suggested alternative, and RAG fair-clause matches.
 *
 * @param {Object} props
 * @param {Object} props.clause — { id, title, content, type, risk_level, risk_score, explanation, risk_factors, suggested_alternative, missing_protections, fair_alternatives, comparison_notes }
 */
const RISK_CONFIG = {
  High: {
    border: 'border-l-red-500',
    badge: 'badge-risk-high',
    dot: 'bg-red-500',
    shadow: 'shadow-red-100',
    icon: AlertTriangle,
    iconColor: 'text-red-500',
  },
  Medium: {
    border: 'border-l-amber-500',
    badge: 'badge-risk-medium',
    dot: 'bg-amber-500',
    shadow: 'shadow-amber-100',
    icon: AlertTriangle,
    iconColor: 'text-amber-500',
  },
  Low: {
    border: 'border-l-emerald-500',
    badge: 'badge-risk-low',
    dot: 'bg-emerald-500',
    shadow: 'shadow-emerald-100',
    icon: Shield,
    iconColor: 'text-emerald-500',
  },
};

export default function ClauseAccordion({ clause }) {
  const [expanded, setExpanded] = useState(false);

  const risk = clause.risk_level || 'Low';
  const config = RISK_CONFIG[risk] || RISK_CONFIG.Low;
  const Icon = config.icon;
  const hasAlternatives = clause.fair_alternatives?.length > 0;
  const hasRiskFactors = clause.risk_factors?.length > 0;
  const hasMissing = clause.missing_protections?.length > 0;

  return (
    <div className={`
      card border-l-4 overflow-hidden animate-slide-up
      ${config.border}
      ${expanded ? `shadow-md ${config.shadow}` : ''}
    `}>
      {/* ── Header ──────────────────────── */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-4 px-5 py-4 text-left hover:bg-slate-50/80 transition-colors"
        aria-expanded={expanded}
      >
        <div className={`w-3 h-3 rounded-full shrink-0 ${config.dot} ${risk === 'High' ? 'animate-pulse-soft' : ''}`} />

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h4 className="font-semibold text-slate-800 text-sm truncate">
              {clause.title || `Clause #${clause.id}`}
            </h4>
            <span className="text-[10px] uppercase tracking-wider text-slate-400 bg-slate-100 px-2 py-0.5 rounded-full shrink-0 font-medium">
              {clause.type || 'general'}
            </span>
          </div>
        </div>

        <span className={`${config.badge} shrink-0`}>
          <Icon className={`w-3 h-3 ${config.iconColor}`} />
          <span className="ml-1">{risk}</span>
          <span className="ml-1.5 text-slate-400 font-normal">
            {clause.risk_score ?? '?'}/100
          </span>
        </span>

        {expanded ? (
          <ChevronUp className="w-5 h-5 text-slate-400 shrink-0" />
        ) : (
          <ChevronDown className="w-5 h-5 text-slate-400 shrink-0" />
        )}
      </button>

      {/* ── Expanded Content ────────────── */}
      {expanded && (
        <div className="px-5 pb-5 space-y-5 border-t border-slate-100 pt-5 animate-slide-up">
          {/* Original Text */}
          <Section icon={<BookOpen className="w-4 h-4" />} label="Original Clause">
            <p className="text-sm text-slate-600 bg-slate-50 rounded-xl p-4 border border-slate-100 leading-relaxed italic whitespace-pre-line">
              {clause.content || 'No text available.'}
            </p>
          </Section>

          {/* Risk Explanation */}
          {(clause.explanation || clause.risk_score) && (
            <Section icon={<AlertTriangle className="w-4 h-4 text-amber-500" />} label="Risk Analysis">
              <p className="text-sm text-slate-700 leading-relaxed">
                {clause.explanation || 'Risk score indicates the severity of potential concerns in this clause.'}
              </p>
            </Section>
          )}

          {/* Risk Factors */}
          {hasRiskFactors && (
            <div className="bg-red-50/50 rounded-xl p-4 border border-red-100">
              <h5 className="text-xs font-bold uppercase tracking-wider text-red-700 mb-3 flex items-center gap-1.5">
                <AlertTriangle className="w-3.5 h-3.5" />
                Risk Factors
              </h5>
              <ul className="space-y-2">
                {clause.risk_factors.map((f, i) => (
                  <li key={i} className="text-sm text-red-800 flex items-start gap-2">
                    <span className="text-red-400 mt-1 shrink-0">•</span>
                    {f}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Suggested Alternative */}
          {clause.suggested_alternative && (
            <Section icon={<Lightbulb className="w-4 h-4 text-emerald-500" />} label="Suggested Fair Alternative">
              <p className="text-sm text-emerald-800 bg-emerald-50 rounded-xl p-4 border border-emerald-100 leading-relaxed font-medium">
                {clause.suggested_alternative}
              </p>
            </Section>
          )}

          {/* Missing Protections */}
          {hasMissing && (
            <div className="bg-amber-50/50 rounded-xl p-4 border border-amber-100">
              <h5 className="text-xs font-bold uppercase tracking-wider text-amber-700 mb-3 flex items-center gap-1.5">
                <Gavel className="w-3.5 h-3.5" />
                Missing Protections
              </h5>
              <ul className="space-y-2">
                {clause.missing_protections.map((mp, i) => (
                  <li key={i} className="text-sm text-amber-800 flex items-start gap-2">
                    <span className="text-amber-400 mt-1 shrink-0">◦</span>
                    {mp}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Fair Alternatives (RAG) */}
          {hasAlternatives && (
            <Section icon={<BookOpen className="w-4 h-4 text-accent-500" />} label="Similar Fair Clauses (RAG Match)">
              <div className="space-y-3">
                {clause.fair_alternatives.map((alt, i) => (
                  <div key={i} className="bg-accent-50/50 rounded-xl p-4 border border-accent-100">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-semibold text-slate-800">{alt.title}</span>
                      <span className="text-xs font-bold text-accent-600 bg-accent-100 px-3 py-1 rounded-full">
                        {(alt.score * 100).toFixed(0)}% match
                      </span>
                    </div>
                    <p className="text-xs text-slate-600 leading-relaxed">
                      {alt.content?.length > 300
                        ? alt.content.slice(0, 300) + '...'
                        : alt.content}
                    </p>
                  </div>
                ))}
              </div>
              {clause.comparison_notes && (
                <p className="text-xs text-slate-500 mt-2 italic leading-relaxed">
                  {clause.comparison_notes}
                </p>
              )}
            </Section>
          )}
        </div>
      )}
    </div>
  );
}

/** Reusable section wrapper */
function Section({ icon, label, children }) {
  return (
    <div>
      <h5 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3 flex items-center gap-2">
        {icon}
        {label}
      </h5>
      {children}
    </div>
  );
}
