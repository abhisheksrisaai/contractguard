import { useState } from 'react';
import { ChevronDown, ChevronUp, AlertTriangle, Lightbulb, BookOpen, Shield, Gavel } from 'lucide-react';

const RISK_CONFIG = {
  High:   { border: 'border-l-red-500',   dot: 'bg-red-500',   icon: AlertTriangle, iconColor: 'text-red-400' },
  Medium: { border: 'border-l-amber-500', dot: 'bg-amber-500', icon: AlertTriangle, iconColor: 'text-amber-400' },
  Low:    { border: 'border-l-emerald-500', dot: 'bg-emerald-500', icon: Shield, iconColor: 'text-emerald-400' },
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
    <div className={`card border-l-4 overflow-hidden animate-slide-up ${config.border}`}>
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-3 px-4 sm:px-5 py-3.5 text-left hover:bg-white/[0.03] transition-colors"
        aria-expanded={expanded}
      >
        <div className={`w-3 h-3 rounded-full shrink-0 ${config.dot} ${risk === 'High' ? 'animate-pulse' : ''}`} />

        {/* Title row: title + type pill on same line, risk badge + chevron on right */}
        <div className="flex-1 min-w-0 flex items-center gap-2 flex-wrap">
          <h4 className="font-semibold text-white text-sm truncate">{clause.title || `Clause #${clause.id}`}</h4>
          <span className="text-[10px] uppercase tracking-wider text-white/30 bg-white/5 px-2 py-0.5 rounded-full shrink-0 hidden sm:inline-flex">{clause.type || 'general'}</span>
        </div>

        {/* Risk badge + score + chevron — always in one compact group */}
        <div className="flex items-center gap-1.5 shrink-0">
          <span className={`badge-risk-${risk.toLowerCase()} inline-flex items-center gap-1`}>
            <Icon className={`w-3 h-3 ${config.iconColor}`} />
            <span className="hidden xs:inline">{risk}</span>
            <span className="text-white/30 font-normal ml-1">{clause.risk_score ?? '?'}/100</span>
          </span>
          {expanded ? <ChevronUp className="w-5 h-5 text-white/30 shrink-0" /> : <ChevronDown className="w-5 h-5 text-white/30 shrink-0" />}
        </div>
      </button>

      {/* Mobile: type pill below header */}
      <div className="sm:hidden px-4 -mt-1 pb-2">
        <span className="text-[10px] uppercase tracking-wider text-white/30 bg-white/5 px-2 py-0.5 rounded-full inline-flex">{clause.type || 'general'}</span>
      </div>

      {expanded && (
        <div className="px-4 sm:px-5 pb-5 space-y-4 border-t border-white/5 pt-4 animate-slide-up">
          <Section icon={<BookOpen className="w-4 h-4" />} label="Original Clause">
            <p className="text-sm text-white/50 bg-white/[0.03] rounded-xl p-4 border border-white/5 leading-relaxed italic whitespace-pre-line break-words">{clause.content || 'No text available.'}</p>
          </Section>

          {(clause.explanation || clause.risk_score) && (
            <Section icon={<AlertTriangle className="w-4 h-4 text-amber-400" />} label="Risk Analysis">
              <p className="text-sm text-white/60 leading-relaxed break-words">{clause.explanation || 'Risk score indicates the severity of potential concerns.'}</p>
            </Section>
          )}

          {hasRiskFactors && (
            <div className="bg-red-500/5 rounded-xl p-4 border border-red-500/10">
              <h5 className="text-xs font-bold uppercase tracking-wider text-red-400 mb-3 flex items-center gap-1.5"><AlertTriangle className="w-3.5 h-3.5" />Risk Factors</h5>
              <ul className="space-y-2">
                {clause.risk_factors.map((f, i) => (<li key={i} className="text-sm text-red-300/80 flex items-start gap-2 break-words"><span className="text-red-400 mt-1 shrink-0">&bull;</span>{f}</li>))}
              </ul>
            </div>
          )}

          {clause.suggested_alternative && (
            <Section icon={<Lightbulb className="w-4 h-4 text-emerald-400" />} label="Suggested Fair Alternative">
              <p className="text-sm text-emerald-300/80 bg-emerald-500/5 rounded-xl p-4 border border-emerald-500/10 leading-relaxed font-medium break-words">{clause.suggested_alternative}</p>
            </Section>
          )}

          {hasMissing && (
            <div className="bg-amber-500/5 rounded-xl p-4 border border-amber-500/10">
              <h5 className="text-xs font-bold uppercase tracking-wider text-amber-400 mb-3 flex items-center gap-1.5"><Gavel className="w-3.5 h-3.5" />Missing Protections</h5>
              <ul className="space-y-2">
                {clause.missing_protections.map((mp, i) => (<li key={i} className="text-sm text-amber-300/80 flex items-start gap-2 break-words"><span className="text-amber-400 mt-1 shrink-0">&bull;</span>{mp}</li>))}
              </ul>
            </div>
          )}

          {hasAlternatives && (
            <Section icon={<BookOpen className="w-4 h-4 text-accent-400" />} label="Similar Fair Clauses">
              <div className="space-y-3">
                {clause.fair_alternatives.map((alt, i) => (
                  <div key={i} className="bg-accent-500/5 rounded-xl p-4 border border-accent-500/10">
                    <div className="flex items-center justify-between mb-2 gap-2">
                      <span className="text-sm font-semibold text-white truncate">{alt.title}</span>
                      <span className="text-xs font-bold text-accent-400 bg-accent-500/10 px-3 py-1 rounded-full shrink-0">{(alt.score * 100).toFixed(0)}% match</span>
                    </div>
                    <p className="text-xs text-white/40 leading-relaxed break-words">{alt.content?.length > 300 ? alt.content.slice(0, 300) + '...' : alt.content}</p>
                  </div>
                ))}
              </div>
              {clause.comparison_notes && <p className="text-xs text-white/30 mt-2 italic leading-relaxed break-words">{clause.comparison_notes}</p>}
            </Section>
          )}
        </div>
      )}
    </div>
  );
}

function Section({ icon, label, children }) {
  return (
    <div>
      <h5 className="text-xs font-bold uppercase tracking-wider text-white/40 mb-3 flex items-center gap-2">{icon}{label}</h5>
      {children}
    </div>
  );
}
