/**
 * Explicit state machine for the contract Q&A panel.
 *
 * The component used to track `loading`, `error`, `count`, `history`, and the
 * current answer independently. A request that resolved after a contract
 * change could append to the new contract's history. This machine gives each
 * ask a monotonically increasing request id and ignores anything that no
 * longer matches the active question.
 *
 *   idle ──ASK_START──▶ asking ──ASK_SUCCEED──▶ idle (or limit)
 *     ▲                   │
 *     └────ASK_FAIL───────┘
 */

export const QA_STATUS = Object.freeze({
  IDLE: 'idle',
  ASKING: 'asking',
  ERROR: 'error',
  LIMIT: 'limit',
});

export const QA_EVENT = Object.freeze({
  QUESTION_SET: 'qa/question-set',
  ASK_START: 'qa/ask-start',
  ASK_SUCCEED: 'qa/ask-succeed',
  ASK_FAIL: 'qa/ask-fail',
  TOGGLE_COLLAPSED: 'qa/toggle-collapsed',
  RESET: 'qa/reset',
});

export const MAX_QUESTIONS = 10;

const TRANSITIONS = Object.freeze({
  [QA_STATUS.IDLE]: Object.freeze({
    [QA_EVENT.QUESTION_SET]: QA_STATUS.IDLE,
    [QA_EVENT.ASK_START]: QA_STATUS.ASKING,
    [QA_EVENT.TOGGLE_COLLAPSED]: QA_STATUS.IDLE,
    [QA_EVENT.RESET]: QA_STATUS.IDLE,
  }),
  [QA_STATUS.ASKING]: Object.freeze({
    [QA_EVENT.ASK_SUCCEED]: QA_STATUS.IDLE,
    [QA_EVENT.ASK_FAIL]: QA_STATUS.ERROR,
    [QA_EVENT.TOGGLE_COLLAPSED]: QA_STATUS.ASKING,
    [QA_EVENT.RESET]: QA_STATUS.IDLE,
  }),
  [QA_STATUS.ERROR]: Object.freeze({
    [QA_EVENT.QUESTION_SET]: QA_STATUS.ERROR,
    [QA_EVENT.ASK_START]: QA_STATUS.ASKING,
    [QA_EVENT.TOGGLE_COLLAPSED]: QA_STATUS.ERROR,
    [QA_EVENT.RESET]: QA_STATUS.IDLE,
  }),
});

export const QA_MACHINE = Object.freeze({
  initial: QA_STATUS.IDLE,
  transitions: TRANSITIONS,
  states: Object.freeze({
    [QA_STATUS.IDLE]: Object.freeze({
      description: 'Waiting for a question, or showing the latest answer.',
      events: Object.freeze(Object.keys(TRANSITIONS[QA_STATUS.IDLE])),
    }),
    [QA_STATUS.ASKING]: Object.freeze({
      description: 'One question is in flight. Duplicate asks are ignored.',
      events: Object.freeze(Object.keys(TRANSITIONS[QA_STATUS.ASKING])),
    }),
    [QA_STATUS.ERROR]: Object.freeze({
      description: 'The last ask failed. The question can be retried.',
      events: Object.freeze(Object.keys(TRANSITIONS[QA_STATUS.ERROR])),
    }),
    [QA_STATUS.LIMIT]: Object.freeze({
      derived: true,
      description: 'The per-contract question budget is exhausted.',
      events: Object.freeze([]),
    }),
  }),
  maxQuestions: MAX_QUESTIONS,
});

export function createInitialQaState() {
  return {
    status: QA_STATUS.IDLE,
    question: '',
    answer: '',
    error: '',
    history: [],
    count: 0,
    collapsed: false,
    showExamples: true,
    requestId: 0,
  };
}

function allowedNextStatus(state, event) {
  return TRANSITIONS[state.status]?.[event.type] ?? null;
}

function isCurrentRequest(state, event) {
  return event.requestId == null || event.requestId === state.requestId;
}

export function qaReducer(state, event) {
  const nextStatus = allowedNextStatus(state, event);
  if (nextStatus == null) return state;

  switch (event.type) {
    case QA_EVENT.QUESTION_SET:
      return { ...state, question: event.question ?? '' };

    case QA_EVENT.TOGGLE_COLLAPSED:
      return { ...state, collapsed: !state.collapsed };

    case QA_EVENT.ASK_START: {
      const query = String(event.question ?? '').trim();
      if (!query || state.count >= MAX_QUESTIONS) return state;
      return {
        ...state,
        status: QA_STATUS.ASKING,
        question: query,
        answer: '',
        error: '',
        showExamples: false,
        requestId: event.requestId ?? state.requestId,
      };
    }

    case QA_EVENT.ASK_SUCCEED: {
      if (!isCurrentRequest(state, event)) return state;
      const answer = event.answer || 'No answer returned.';
      return {
        ...state,
        status: QA_STATUS.IDLE,
        answer,
        error: '',
        count: state.count + 1,
        question: '',
        history: [
          { id: state.requestId, question: event.question || state.question, answer },
          ...state.history,
        ],
      };
    }

    case QA_EVENT.ASK_FAIL:
      if (!isCurrentRequest(state, event)) return state;
      return {
        ...state,
        status: QA_STATUS.ERROR,
        answer: '',
        error: event.error || 'Failed to get answer.',
      };

    case QA_EVENT.RESET:
      return createInitialQaState();

    default:
      return state;
  }
}

export function selectQaStatus(state) {
  if (state.status !== QA_STATUS.ASKING && state.count >= MAX_QUESTIONS) {
    return QA_STATUS.LIMIT;
  }
  return state.status;
}

export function selectCanAsk(state) {
  return selectQaStatus(state) !== QA_STATUS.ASKING
    && state.count < MAX_QUESTIONS;
}
