import { useMemo, useState } from 'react';
import {
  AlertTriangle, ArrowDown, Check, ChevronDown, Copy, FileText, Search,
} from 'lucide-react';

const LEVELS = {
  High: {
    label: 'High',
    text: 'text-red-400',
    bar: 'bg-red-500',
    dot: 'bg-red-500',
  },
  Medium: {
    label: 'Medium',
    text: 'text-amber-400',
    bar: 'bg-amber-500',
    dot: 'bg-amber-500',
  },
  Low: {
    label: 'Low',
    text: 'text-emerald-400',
    bar: 'bg-emerald-500',
    dot: 'bg-emerald-500',
  },
  Review: {
    label: 'Review',
    text: 'text-white/40',
    bar: 'bg-white/20',
    dot: 'bg-white/25',
  },
};

function clauseLevel(clause) {
  if (clause.analysis_status === 'failed' || clause.risk_level === 'Unknown' || clause.risk_score == null) {
    return 'Review';
  }
  return LEVELS[clause.risk_level] ? clause.risk_level : 'Review';
}

function safeScore(clause) {
  return typeof clause.risk_score === 'number' ? Math.max(0, Math.min(100, clause.risk_score)) : null;
}

export default function ClauseLedger({ clauses = [], onAskQuestions }) {
  const [filter, setFilter] = useState('all');
  const [sort, setSort] = useState('document');
  const [query, setQuery] = useState('');
  const [openId, setOpenId] = useState(null);

  const counts = useMemo(() => {
    const result = { all: clauses.length, High: 0, Medium: 0, Low: 0, Review: 0 };
    clauses.forEach((clause) => {
      result[clauseLevel(clause)] += 1;
    });
    return result;
  }, [clauses]);

  const rows = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    const mapped = clauses.map((clause, index) => ({
      clause,
      index,
      level: clauseLevel(clause),
      score: safeScore(clause),
    }));

    const filtered = mapped.filter((row) => {
      if (filter !== 'all' && row.level !== filter) return false;
      if (!normalizedQuery) return true;
      const haystack = `${row.clause.title || ''} ${row.clause.type || ''} ${row.clause.content || ''}`.toLowerCase();
      return haystack.includes(normalizedQuery);
    });

    if (sort === 'risk') {
      filtered.sort((a, b) => {
        if (a.score == null && b.score == null) return a.index - b.index;
        if (a.score == null) return 1;
        if (b.score == null) return -1;
        return b.score - a.score || a.index - b.index;
      });
    }
    return filtered;
  }, [clauses, filter, query, sort]);

  const setFilterAndReset = (nextFilter) => {
    setFilter(nextFilter);
    setOpenId(null);
  };

  return (
    <section id="clause-register" className="space-y-4 animate-slide-up">
      <div className="flex flex-col gap-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-accent-400">Clause register</p>
            <h2 className="mt-1 flex flex-wrap items-baseline gap-x-2 text-xl font-semibold tracking-tight text-white">
              Detailed clause analysis
              <span className="text-sm font-normal tabular-nums text-white/30">{clauses.length} clauses</span>
            </h2>
            <p className="mt-1 max-w-2xl text-sm leading-6 text-white/40">
              Every clause, scored and ranked. Open a row for the assessment, risk factors, and suggested language.
            </p>
          </div>
          <button
            type="button"
            onClick={onAskQuestions}
            className="inline-flex shrink-0 items-center gap-1.5 self-start rounded-full border border-white/10 px-3.5 py-2 text-xs font-medium text-white/55 transition hover:border-white/20 hover:text-white"
          >
            Ask about this contract <ArrowDown className="h-3.5 w-3.5" />
          </button>
        </div>

        <div className="h-1 w-full overflow-hidden bg-white/5" aria-hidden="true">
          <div className="flex h-full">
            <span className="bg-red-500" style={{ width: `${counts.all ? (counts.High / counts.all) * 100 : 0}%` }} />
            <span className="bg-amber-500" style={{ width: `${counts.all ? (counts.Medium / counts.all) * 100 : 0}%` }} />
            <span className="bg-emerald-500" style={{ width: `${counts.all ? (counts.Low / counts.all) * 100 : 0}%` }} />
            <span className="bg-white/20" style={{ width: `${counts.all ? (counts.Review / counts.all) * 100 : 0}%` }} />
          </div>
        </div>

        <div className="flex flex-col gap-3 border-b border-white/10 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex flex-wrap items-center gap-x-0.5" role="tablist" aria-label="Filter clauses by risk">
            {[
              ['all', 'All'],
              ['High', 'High'],
              ['Medium', 'Medium'],
              ['Low', 'Low'],
              ['Review', 'Review'],
            ].map(([value, label]) => (
              <button
                key={value}
                type="button"
                role="tab"
                aria-selected={filter === value}
                onClick={() => setFilterAndReset(value)}
                className={`-mb-px border-b-2 px-3 py-2.5 text-xs font-medium transition-colors ${
                  filter === value
                    ? 'border-accent-400 text-white'
                    : 'border-transparent text-white/40 hover:text-white/70'
                }`}
              >
                {label}
                <span className="ml-1.5 tabular-nums text-white/25">{counts[value]}</span>
              </button>
            ))}
          </div>

          <div className="flex items-center gap-2 pb-2 sm:pb-1">
            <label className="relative flex-1 sm:w-52">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-white/25" />
              <input
                type="search"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Find a clause"
                aria-label="Search clauses"
                className="w-full rounded-full border border-white/10 bg-white/[0.03] py-1.5 pl-8 pr-3 text-xs text-white placeholder-white/25 outline-none transition focus:border-accent-400"
              />
            </label>
            <select
              value={sort}
              onChange={(event) => setSort(event.target.value)}
              aria-label="Sort clauses"
              className="rounded-full border border-white/10 bg-white/[0.03] px-3 py-1.5 text-xs text-white/50 outline-none transition focus:border-accent-400"
            >
              <option value="document">Document order</option>
              <option value="risk">Highest risk</option>
            </select>
          </div>
        </div>
      </div>

      <div className="overflow-hidden rounded-2xl border border-white/10 bg-white/[0.015]">
        <div className="hidden grid-cols-[2rem_minmax(0,1fr)_7rem_4.5rem_1rem] gap-4 border-b border-white/5 px-5 py-2 text-[9px] font-semibold uppercase tracking-[0.16em] text-white/25 sm:grid">
          <span>#</span>
          <span>Clause</span>
          <span>Risk score</span>
          <span>Level</span>
          <span aria-hidden="true" />
        </div>

        {rows.length === 0 ? (
          <div className="px-5 py-12 text-center">
            <FileText className="mx-auto h-6 w-6 text-white/20" />
            <p className="mt-3 text-sm font-medium text-white/55">No clauses match this view</p>
            <p className="mt-1 text-xs text-white/30">Try a different filter or clear the search.</p>
          </div>
        ) : (
          rows.map((row) => (
            <ClauseRow
              key={row.clause.id || row.index}
              row={row}
              open={openId === (row.clause.id || row.index)}
              onToggle={() => setOpenId(openId === (row.clause.id || row.index) ? null : (row.clause.id || row.index))}
            />
          ))
        )}
      </div>
    </section>
  );
}

function ClauseRow({ row, open, onToggle }) {
  const { clause, index, level, score } = row;
  const config = LEVELS[level];
  const title = clause.title || `Clause ${index + 1}`;
  const type = clause.type || 'general';

  return (
    <div
      className="border-b border-white/5 last:border-0"
      data-clause-id={clause.id || `clause-${index + 1}`}
      data-clause-status={level.toLowerCase()}
    >
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={open}
        className={`grid w-full grid-cols-[1.5rem_minmax(0,1fr)_3.25rem_1rem] items-center gap-3 px-4 py-3.5 text-left transition-colors sm:grid-cols-[2rem_minmax(0,1fr)_7rem_4.5rem_1rem] sm:gap-4 sm:px-5 ${
          open ? 'bg-white/[0.03]' : 'hover:bg-white/[0.02]'
        }`}
      >
        <span className="text-[10px] tabular-nums text-white/25">{String(index + 1).padStart(2, '0')}</span>

        <span className="min-w-0">
          <span className="block truncate text-sm font-medium text-white">{title}</span>
          <span className="mt-0.5 block truncate text-[9px] uppercase tracking-[0.14em] text-white/30">{type}</span>
        </span>

        {/* Mobile: compact score + level */}
        <span className="flex flex-col items-end gap-0.5 sm:hidden">
          <span className={`text-xs tabular-nums ${score == null ? 'text-white/25' : 'text-white/65'}`}>{score ?? '—'}</span>
          <span className={`text-[8px] font-semibold uppercase tracking-[0.08em] ${config.text}`}>{config.label}</span>
        </span>

        {/* Desktop: fixed-width score meter */}
        <span className="hidden items-center gap-2 sm:flex">
          <span className="h-1 flex-1 bg-white/10">
            <span className={`block h-full ${config.bar}`} style={{ width: `${score ?? 0}%` }} />
          </span>
          <span className={`w-7 text-right text-xs tabular-nums ${score == null ? 'text-white/25' : 'text-white/60'}`}>{score ?? '—'}</span>
        </span>

        <span className={`hidden text-right text-[10px] font-semibold uppercase tracking-[0.12em] sm:block ${config.text}`}>
          {config.label}
        </span>

        <ChevronDown className={`h-4 w-4 justify-self-end text-white/25 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      {open && <ClauseDetail clause={clause} level={level} />}
    </div>
  );
}

function ClauseDetail({ clause, level }) {
  const [copied, setCopied] = useState(false);
  const failed = level === 'Review';
  const config = LEVELS[level];
  const suggested = clause.suggested_alternative || '';
  const riskFactors = Array.isArray(clause.risk_factors) ? clause.risk_factors.filter(Boolean) : [];
  const missing = Array.isArray(clause.missing_protections) ? clause.missing_protections.filter(Boolean) : [];
  const alternatives = Array.isArray(clause.fair_alternatives) ? clause.fair_alternatives : [];

  const copySuggested = () => {
    if (!suggested) return;
    navigator.clipboard.writeText(suggested).then(() => {
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    }).catch(() => {});
  };

  return (
    <div className="border-t border-white/5 bg-white/[0.02] px-4 py-5 sm:px-6 sm:py-6">
      <div className="mb-5 flex flex-wrap items-center gap-x-3 gap-y-1 text-[9px] uppercase tracking-[0.14em] text-white/25">
        <span className={config.text}>{failed ? 'Not analyzed' : `${config.label} risk`}</span>
        {!failed && clause.confidence != null && <span>Confidence {clause.confidence}%</span>}
        {!failed && clause.parse_quality && <span>{clause.parse_quality} parse</span>}
        {clause.needs_human_review && <span className="text-amber-400/70">Manual review</span>}
        {alternatives.length > 0 && <span>{alternatives.length} reference match{alternatives.length === 1 ? '' : 'es'}</span>}
      </div>

      {failed ? (
        <div className="grid gap-5 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
          <div>
            <SectionLabel icon={FileText}>Original clause</SectionLabel>
            <p className="mt-2 max-h-72 overflow-y-auto whitespace-pre-line break-words pr-2 text-sm leading-7 text-white/50">
              {clause.content || 'No text available.'}
            </p>
          </div>
          <div className="border-l-2 border-white/15 pl-4">
            <p className="flex items-center gap-2 text-sm font-medium text-white/65">
              <AlertTriangle className="h-4 w-4 text-amber-400" /> This clause was not scored
            </p>
            <p className="mt-1.5 text-sm leading-6 text-white/40">
              Automated analysis could not complete after retries, so the clause is excluded from the overall score. Re-run the analysis, or review the language manually.
            </p>
          </div>
        </div>
      ) : (
        <div className="grid gap-6 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
          <div>
            <SectionLabel icon={FileText}>Original clause</SectionLabel>
            <p className="mt-2 max-h-80 overflow-y-auto whitespace-pre-line break-words pr-2 text-sm leading-7 text-white/50">
              {clause.content || 'No text available.'}
            </p>
          </div>

          <div className="space-y-5">
            <div>
              <SectionLabel icon={AlertTriangle}>Assessment</SectionLabel>
              <p className="mt-2 text-sm leading-7 text-white/60">
                {clause.explanation || 'No explanation returned for this clause.'}
              </p>
            </div>

            {riskFactors.length > 0 && (
              <div>
                <SectionLabel>Risk factors</SectionLabel>
                <div className="mt-2 divide-y divide-white/5 border-y border-white/5">
                  {riskFactors.map((factor, index) => (
                    <div key={index} className="flex gap-3 py-2.5">
                      <span className="mt-0.5 text-[9px] tabular-nums text-white/25">{String(index + 1).padStart(2, '0')}</span>
                      <p className="text-sm leading-6 text-white/55">{factor}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {missing.length > 0 && (
              <div>
                <SectionLabel>Missing protections</SectionLabel>
                <ul className="mt-2 space-y-1.5">
                  {missing.map((item, index) => (
                    <li key={index} className="flex gap-2 text-sm leading-6 text-white/45">
                      <span className="mt-2 h-1 w-1 shrink-0 bg-amber-500" />
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {suggested && (
              <div className="border-l-2 border-accent-500/60 pl-4">
                <div className="flex items-center justify-between gap-3">
                  <SectionLabel>Suggested language</SectionLabel>
                  <button
                    type="button"
                    onClick={copySuggested}
                    className="inline-flex items-center gap-1 text-[10px] text-white/30 transition hover:text-white"
                  >
                    {copied ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
                    {copied ? 'Copied' : 'Copy'}
                  </button>
                </div>
                <p className="mt-2 max-h-64 overflow-y-auto whitespace-pre-line break-words pr-2 text-sm leading-7 text-white/65">
                  {suggested}
                </p>
              </div>
            )}

            {alternatives.length > 0 && (
              <details className="group border-t border-white/5 pt-4">
                <summary className="flex cursor-pointer list-none items-center justify-between gap-3 text-[10px] font-semibold uppercase tracking-[0.14em] text-white/30 transition hover:text-white/60">
                  <span>Reference language ({alternatives.length})</span>
                  <ChevronDown className="h-3.5 w-3.5 transition-transform group-open:rotate-180" />
                </summary>
                <div className="mt-3 space-y-3">
                  {alternatives.slice(0, 3).map((alternative, index) => (
                    <div key={index} className="border-l border-white/10 pl-3">
                      <div className="flex flex-wrap items-baseline justify-between gap-2">
                        <p className="text-xs font-medium text-white/60">{alternative.title || 'Fair clause'}</p>
                        <span className="text-[10px] tabular-nums text-accent-400">{Math.round((alternative.score || 0) * 100)}% match</span>
                      </div>
                      <p className="mt-1 line-clamp-3 text-xs leading-5 text-white/35">{alternative.content || ''}</p>
                    </div>
                  ))}
                </div>
                {clause.comparison_notes && (
                  <p className="mt-3 text-xs leading-5 text-white/30">{clause.comparison_notes}</p>
                )}
              </details>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function SectionLabel({ icon: Icon, children }) {
  return (
    <p className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-[0.16em] text-white/30">
      {Icon && <Icon className="h-3 w-3" />}
      {children}
    </p>
  );
}
