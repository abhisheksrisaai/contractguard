import { useState } from 'react';
import { ChevronDown, ChevronUp, AlertTriangle, Lightbulb, BookOpen } from 'lucide-react';

const RISK_STYLES = {
  High: {
    badge: 'bg-red-100 text-red-700 border-red-200',
    border: 'border-l-red-500',
    dot: 'bg-red-500',
  },
  Medium: {
    badge: 'bg-amber-100 text-amber-700 border-amber-200',
    border: 'border-l-amber-500',
    dot: 'bg-amber-500',
  },
  Low: {
    badge: 'bg-green-100 text-green-700 border-green-200',
    border: 'border-l-green-500',
    dot: 'bg-green-500',
  },
};

export default function ClauseCard({ clause }) {
  const [expanded, setExpanded] = useState(false);

  const risk = clause.risk_level || 'Low';
  const styles = RISK_STYLES[risk] || RISK_STYLES.Low;
  const hasAlternatives = clause.fair_alternatives?.length > 0;

  return (
    <div className={`bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden transition-all ${expanded ? 'shadow-md' : ''}`}>
      {/* ── Header (always visible) ───────── */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-3 px-5 py-4 text-left hover:bg-slate-50 transition"
      >
        {/* Risk dot */}
        <span className={`w-2.5 h-2.5 rounded-full shrink-0 ${styles.dot}`} />

        {/* Title + type */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h4 className="font-semibold text-slate-800 text-sm truncate">
              {clause.title || `Clause #${clause.id}`}
            </h4>
            <span className="text-[10px] uppercase tracking-wider text-slate-400 bg-slate-100 px-2 py-0.5 rounded-full shrink-0">
              {clause.type || 'general'}
            </span>
          </div>
        </div>

        {/* Risk badge */}
        <span className={`text-xs font-semibold px-2.5 py-1 rounded-full border ${styles.badge} shrink-0`}>
          {risk} • {clause.risk_score ?? '?'}/100
        </span>

        {/* Expand chevron */}
        {expanded ? (
          <ChevronUp className="w-5 h-5 text-slate-400 shrink-0" />
        ) : (
          <ChevronDown className="w-5 h-5 text-slate-400 shrink-0" />
        )}
      </button>

      {/* ── Expanded Content ────────────────── */}
      {expanded && (
        <div className="px-5 pb-5 space-y-4 border-t border-slate-100 pt-4">
          {/* Original Text */}
          <Section
            icon={<BookOpen className="w-4 h-4 text-slate-400" />}
            label="Original Clause Text"
          >
            <p className="text-sm text-slate-600 bg-slate-50 rounded-lg p-3 border border-slate-100 whitespace-pre-line leading-relaxed italic">
              {clause.content || 'No text available.'}
            </p>
          </Section>

          {/* Risk Explanation */}
          <Section
            icon={<AlertTriangle className="w-4 h-4 text-amber-500" />}
            label="Risk Explanation"
          >
            <p className="text-sm text-slate-700 leading-relaxed">
              {clause.explanation || 'No specific risk explanation.'}
            </p>
          </Section>

          {/* Risk Factors */}
          {clause.risk_factors?.length > 0 && (
            <div>
              <h5 className="text-xs font-semibold uppercase tracking-wider text-red-600 mb-2">
                ⚠ Risk Factors
              </h5>
              <ul className="space-y-1">
                {clause.risk_factors.map((f, i) => (
                  <li key={i} className="text-sm text-red-700 flex items-start gap-2">
                    <span className="text-red-400 mt-0.5 shrink-0">•</span>
                    {f}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Suggested Alternative */}
          {clause.suggested_alternative && (
            <Section
              icon={<Lightbulb className="w-4 h-4 text-green-500" />}
              label="💡 Suggested Alternative"
            >
              <p className="text-sm text-green-800 bg-green-50 rounded-lg p-3 border border-green-100 leading-relaxed">
                {clause.suggested_alternative}
              </p>
            </Section>
          )}

          {/* Missing Protections */}
          {clause.missing_protections?.length > 0 && (
            <div>
              <h5 className="text-xs font-semibold uppercase tracking-wider text-amber-600 mb-2">
                Missing Protections
              </h5>
              <ul className="space-y-1">
                {clause.missing_protections.map((mp, i) => (
                  <li key={i} className="text-sm text-amber-700 flex items-start gap-2">
                    <span className="text-amber-400 mt-0.5 shrink-0">◦</span>
                    {mp}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Fair Alternatives (RAG) */}
          {hasAlternatives && (
            <Section
              icon={<BookOpen className="w-4 h-4 text-blue-500" />}
              label="🔍 Similar Fair Clauses from Library"
            >
              <div className="space-y-2">
                {clause.fair_alternatives.map((alt, i) => (
                  <div
                    key={i}
                    className="bg-blue-50 rounded-lg p-3 border border-blue-100"
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-semibold text-slate-800">
                        {alt.title}
                      </span>
                      <span className="text-xs text-blue-600 font-medium bg-blue-100 px-2 py-0.5 rounded-full">
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
                <p className="text-xs text-slate-500 mt-2 italic">
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
      <h5 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2 flex items-center gap-1.5">
        {icon}
        {label}
      </h5>
      {children}
    </div>
  );
}
