/**
 * Explicit state machine for the contract-analysis journey.
 *
 * The app used to infer its view from three independent booleans/objects
 * (`loading`, `analysis`, `error`). That allowed impossible combinations and
 * let a late response overwrite a reset. Every transition now lives here:
 *
 *   idle ──START──▶ analyzing ──SUCCEED──▶ results
 *     ▲                │                    │
 *     └──────FAIL──────┘                    │
 *     └──────────────── RESET ──────────────┘
 *
 * `runId` makes completions idempotent: a response from an abandoned run is
 * ignored, so "Analyze another contract" cannot be undone by an in-flight
 * request. The report download is a small sub-machine on `results`.
 */

export const ANALYSIS_PHASE = Object.freeze({
  IDLE: 'idle',
  ANALYZING: 'analyzing',
  RESULTS: 'results',
});

export const ANALYSIS_OUTCOME = Object.freeze({
  NONE: 'none',
  COMPLETE: 'complete',
  PARTIAL: 'partial',
  FAILED: 'failed',
});

export const REPORT_STATUS = Object.freeze({
  IDLE: 'idle',
  GENERATING: 'generating',
  READY: 'ready',
  ERROR: 'error',
});

export const ANALYSIS_EVENT = Object.freeze({
  START: 'analysis/start',
  PROGRESS: 'analysis/progress',
  SUCCEED: 'analysis/succeed',
  FAIL: 'analysis/fail',
  ERROR_SET: 'analysis/error-set',
  ERROR_DISMISSED: 'analysis/error-dismissed',
  RESET: 'analysis/reset',
  REPORT_START: 'report/start',
  REPORT_SUCCEED: 'report/succeed',
  REPORT_FAIL: 'report/fail',
});

const TRANSITIONS = Object.freeze({
  [ANALYSIS_PHASE.IDLE]: Object.freeze({
    [ANALYSIS_EVENT.START]: ANALYSIS_PHASE.ANALYZING,
    [ANALYSIS_EVENT.ERROR_SET]: ANALYSIS_PHASE.IDLE,
    [ANALYSIS_EVENT.ERROR_DISMISSED]: ANALYSIS_PHASE.IDLE,
    [ANALYSIS_EVENT.RESET]: ANALYSIS_PHASE.IDLE,
  }),
  [ANALYSIS_PHASE.ANALYZING]: Object.freeze({
    [ANALYSIS_EVENT.PROGRESS]: ANALYSIS_PHASE.ANALYZING,
    [ANALYSIS_EVENT.SUCCEED]: ANALYSIS_PHASE.RESULTS,
    [ANALYSIS_EVENT.FAIL]: ANALYSIS_PHASE.IDLE,
    [ANALYSIS_EVENT.RESET]: ANALYSIS_PHASE.IDLE,
  }),
  [ANALYSIS_PHASE.RESULTS]: Object.freeze({
    [ANALYSIS_EVENT.START]: ANALYSIS_PHASE.ANALYZING,
    [ANALYSIS_EVENT.RESET]: ANALYSIS_PHASE.IDLE,
    [ANALYSIS_EVENT.REPORT_START]: ANALYSIS_PHASE.RESULTS,
    [ANALYSIS_EVENT.REPORT_SUCCEED]: ANALYSIS_PHASE.RESULTS,
    [ANALYSIS_EVENT.REPORT_FAIL]: ANALYSIS_PHASE.RESULTS,
  }),
});

export const ANALYSIS_MACHINE = Object.freeze({
  initial: ANALYSIS_PHASE.IDLE,
  transitions: TRANSITIONS,
  states: Object.freeze({
    [ANALYSIS_PHASE.IDLE]: Object.freeze({
      description: 'Landing page. No analysis is running or displayed.',
      view: 'idle',
      events: Object.freeze(Object.keys(TRANSITIONS[ANALYSIS_PHASE.IDLE])),
    }),
    [ANALYSIS_PHASE.ANALYZING]: Object.freeze({
      description: 'A PDF is uploading or the backend pipeline is running.',
      view: 'analyzing',
      events: Object.freeze(Object.keys(TRANSITIONS[ANALYSIS_PHASE.ANALYZING])),
    }),
    [ANALYSIS_PHASE.RESULTS]: Object.freeze({
      description: 'Analysis finished. The outcome may be complete or partial.',
      view: 'results',
      events: Object.freeze(Object.keys(TRANSITIONS[ANALYSIS_PHASE.RESULTS])),
    }),
  }),
  outcomes: ANALYSIS_OUTCOME,
  reportStatuses: REPORT_STATUS,
});

export function createInitialAnalysisState() {
  return {
    phase: ANALYSIS_PHASE.IDLE,
    outcome: ANALYSIS_OUTCOME.NONE,
    analysis: null,
    error: '',
    progress: 0,
    runId: 0,
    report: {
      status: REPORT_STATUS.IDLE,
      error: '',
    },
  };
}

function allowedNextPhase(state, event) {
  return TRANSITIONS[state.phase]?.[event.type] ?? null;
}

function isCurrentRun(state, event) {
  // A caller that does not supply a run id keeps the legacy behaviour; all
  // in-app callers supply one so stale completions can be discarded.
  return event.runId == null || event.runId === state.runId;
}

function clampProgress(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return 0;
  return Math.max(0, Math.min(100, Math.round(numeric)));
}

function resetReport() {
  return { status: REPORT_STATUS.IDLE, error: '' };
}

export function analysisReducer(state, event) {
  const nextPhase = allowedNextPhase(state, event);
  if (nextPhase == null) return state;

  switch (event.type) {
    case ANALYSIS_EVENT.START:
      return {
        ...state,
        phase: ANALYSIS_PHASE.ANALYZING,
        outcome: ANALYSIS_OUTCOME.NONE,
        analysis: null,
        error: '',
        progress: 0,
        runId: event.runId ?? state.runId + 1,
        report: resetReport(),
      };

    case ANALYSIS_EVENT.PROGRESS:
      if (!isCurrentRun(state, event)) return state;
      return { ...state, progress: clampProgress(event.progress) };

    case ANALYSIS_EVENT.SUCCEED:
      if (!isCurrentRun(state, event)) return state;
      return {
        ...state,
        phase: ANALYSIS_PHASE.RESULTS,
        outcome: event.result?.analysis_status === ANALYSIS_OUTCOME.PARTIAL
          ? ANALYSIS_OUTCOME.PARTIAL
          : ANALYSIS_OUTCOME.COMPLETE,
        analysis: event.result,
        error: '',
        progress: 100,
        report: resetReport(),
      };

    case ANALYSIS_EVENT.FAIL:
      if (!isCurrentRun(state, event)) return state;
      return {
        ...state,
        phase: ANALYSIS_PHASE.IDLE,
        outcome: ANALYSIS_OUTCOME.FAILED,
        analysis: null,
        error: event.error || 'Analysis failed.',
        progress: 0,
        report: resetReport(),
      };

    case ANALYSIS_EVENT.ERROR_SET:
      return { ...state, error: event.error || '' };

    case ANALYSIS_EVENT.ERROR_DISMISSED:
      return { ...state, error: '' };

    case ANALYSIS_EVENT.RESET:
      return createInitialAnalysisState();

    case ANALYSIS_EVENT.REPORT_START:
      if (!state.analysis || state.report.status === REPORT_STATUS.GENERATING) {
        return state;
      }
      return {
        ...state,
        report: { status: REPORT_STATUS.GENERATING, error: '' },
      };

    case ANALYSIS_EVENT.REPORT_SUCCEED:
      if (state.report.status !== REPORT_STATUS.GENERATING) return state;
      return {
        ...state,
        report: { status: REPORT_STATUS.READY, error: '' },
      };

    case ANALYSIS_EVENT.REPORT_FAIL:
      if (state.report.status !== REPORT_STATUS.GENERATING) return state;
      return {
        ...state,
        report: {
          status: REPORT_STATUS.ERROR,
          error: event.error || 'Report download failed.',
        },
      };

    default:
      return state;
  }
}

export function selectAppState(state) {
  if (state.phase === ANALYSIS_PHASE.ANALYZING) return 'analyzing';
  if (state.phase === ANALYSIS_PHASE.RESULTS) {
    return state.outcome === ANALYSIS_OUTCOME.PARTIAL
      ? 'results-partial'
      : 'results-complete';
  }
  return state.error ? 'idle-error' : 'idle';
}

export function selectIsAnalyzing(state) {
  return state.phase === ANALYSIS_PHASE.ANALYZING;
}

export function selectIsPartial(state) {
  return state.outcome === ANALYSIS_OUTCOME.PARTIAL;
}

export function selectAnalysisStatus(state) {
  return state.phase === ANALYSIS_PHASE.RESULTS
    ? state.outcome
    : 'unavailable';
}
