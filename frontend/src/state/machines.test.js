import test from 'node:test';
import assert from 'node:assert/strict';

import {
  ANALYSIS_EVENT,
  ANALYSIS_MACHINE,
  ANALYSIS_OUTCOME,
  ANALYSIS_PHASE,
  REPORT_STATUS,
  analysisReducer,
  createInitialAnalysisState,
  selectAnalysisStatus,
  selectAppState,
  selectIsAnalyzing,
  selectIsPartial,
} from './analysisMachine.js';

import {
  MAX_QUESTIONS,
  QA_EVENT,
  QA_MACHINE,
  QA_STATUS,
  createInitialQaState,
  qaReducer,
  selectCanAsk,
  selectQaStatus,
} from './qaMachine.js';

function start(state, runId) {
  return analysisReducer(state, { type: ANALYSIS_EVENT.START, runId });
}

function succeed(state, runId, analysisStatus = 'complete') {
  return analysisReducer(state, {
    type: ANALYSIS_EVENT.SUCCEED,
    runId,
    result: { analysis_status: analysisStatus, overall_score: 42 },
  });
}

test('analysis: idle -> analyzing -> complete results', () => {
  let state = createInitialAnalysisState();
  assert.equal(state.phase, ANALYSIS_PHASE.IDLE);

  state = start(state, 1);
  assert.equal(state.phase, ANALYSIS_PHASE.ANALYZING);
  assert.equal(selectIsAnalyzing(state), true);

  state = analysisReducer(state, {
    type: ANALYSIS_EVENT.PROGRESS,
    runId: 1,
    progress: 37.6,
  });
  assert.equal(state.progress, 38);

  state = succeed(state, 1);
  assert.equal(state.phase, ANALYSIS_PHASE.RESULTS);
  assert.equal(state.outcome, ANALYSIS_OUTCOME.COMPLETE);
  assert.equal(state.analysis.overall_score, 42);
  assert.equal(state.progress, 100);
  assert.equal(selectAppState(state), 'results-complete');
  assert.equal(selectAnalysisStatus(state), 'complete');
  assert.equal(selectIsPartial(state), false);
});

test('analysis: partial payload produces a partial outcome', () => {
  let state = start(createInitialAnalysisState(), 4);
  state = succeed(state, 4, 'partial');

  assert.equal(state.outcome, ANALYSIS_OUTCOME.PARTIAL);
  assert.equal(selectIsPartial(state), true);
  assert.equal(selectAppState(state), 'results-partial');
});

test('analysis: duplicate starts are ignored while a run is active', () => {
  let state = start(createInitialAnalysisState(), 1);
  const active = state;
  state = start(state, 2);

  assert.equal(state, active);
  assert.equal(state.runId, 1);
});

test('analysis: a stale completion cannot overwrite a reset', () => {
  let state = start(createInitialAnalysisState(), 1);
  state = analysisReducer(state, { type: ANALYSIS_EVENT.RESET });

  assert.equal(state.phase, ANALYSIS_PHASE.IDLE);

  const afterReset = state;
  state = succeed(state, 1);
  assert.equal(state, afterReset);

  state = analysisReducer(state, {
    type: ANALYSIS_EVENT.PROGRESS,
    runId: 1,
    progress: 90,
  });
  assert.equal(state.progress, 0);
});

test('analysis: failure returns to the landing page with the error', () => {
  let state = start(createInitialAnalysisState(), 1);
  state = analysisReducer(state, {
    type: ANALYSIS_EVENT.FAIL,
    runId: 1,
    error: 'AI analysis is temporarily unavailable.',
  });

  assert.equal(state.phase, ANALYSIS_PHASE.IDLE);
  assert.equal(state.outcome, ANALYSIS_OUTCOME.FAILED);
  assert.equal(state.error, 'AI analysis is temporarily unavailable.');
  assert.equal(selectAppState(state), 'idle-error');

  state = analysisReducer(state, { type: ANALYSIS_EVENT.ERROR_DISMISSED });
  assert.equal(state.error, '');
  assert.equal(selectAppState(state), 'idle');
});

test('analysis: progress is clamped and ignored for inactive runs', () => {
  let state = start(createInitialAnalysisState(), 2);
  state = analysisReducer(state, {
    type: ANALYSIS_EVENT.PROGRESS,
    runId: 2,
    progress: 140,
  });
  assert.equal(state.progress, 100);

  const unchanged = state;
  state = analysisReducer(state, {
    type: ANALYSIS_EVENT.PROGRESS,
    runId: 1,
    progress: 10,
  });
  assert.equal(state, unchanged);
});

test('report: only results can generate, and transitions are guarded', () => {
  let state = createInitialAnalysisState();
  state = analysisReducer(state, { type: ANALYSIS_EVENT.REPORT_START });
  assert.equal(state.report.status, REPORT_STATUS.IDLE);

  state = succeed(start(state, 1), 1);
  state = analysisReducer(state, { type: ANALYSIS_EVENT.REPORT_START });
  assert.equal(state.report.status, REPORT_STATUS.GENERATING);

  const generating = state;
  state = analysisReducer(state, { type: ANALYSIS_EVENT.REPORT_START });
  assert.equal(state, generating);

  state = analysisReducer(state, { type: ANALYSIS_EVENT.REPORT_SUCCEED });
  assert.equal(state.report.status, REPORT_STATUS.READY);
});

test('report: a failure keeps the error and can be retried', () => {
  let state = succeed(start(createInitialAnalysisState(), 1), 1);
  state = analysisReducer(state, { type: ANALYSIS_EVENT.REPORT_START });
  state = analysisReducer(state, {
    type: ANALYSIS_EVENT.REPORT_FAIL,
    error: 'Report generation failed.',
  });

  assert.equal(state.report.status, REPORT_STATUS.ERROR);
  assert.equal(state.report.error, 'Report generation failed.');

  state = analysisReducer(state, { type: ANALYSIS_EVENT.REPORT_START });
  assert.equal(state.report.status, REPORT_STATUS.GENERATING);
  assert.equal(state.report.error, '');
});

test('analysis machine: every declared event has a valid target state', () => {
  const states = new Set(Object.values(ANALYSIS_PHASE));
  for (const transitions of Object.values(ANALYSIS_MACHINE.transitions)) {
    for (const target of Object.values(transitions)) {
      assert.ok(states.has(target), `unknown target: ${target}`);
    }
  }
  assert.equal(ANALYSIS_MACHINE.states[ANALYSIS_PHASE.IDLE].view, 'idle');
});

function ask(state, requestId, question = 'Is the notice period fair?') {
  return qaReducer(state, {
    type: QA_EVENT.ASK_START,
    requestId,
    question,
  });
}

test('qa: ask -> asking -> answered, then the question is cleared', () => {
  let state = createInitialQaState();
  state = ask(state, 1);

  assert.equal(state.status, QA_STATUS.ASKING);
  assert.equal(selectCanAsk(state), false);
  assert.equal(state.showExamples, false);

  state = qaReducer(state, {
    type: QA_EVENT.ASK_SUCCEED,
    requestId: 1,
    answer: 'Thirty days for both parties.',
  });

  assert.equal(state.status, QA_STATUS.IDLE);
  assert.equal(state.answer, 'Thirty days for both parties.');
  assert.equal(state.question, '');
  assert.equal(state.count, 1);
  assert.equal(state.history.length, 1);
  assert.equal(state.history[0].question, 'Is the notice period fair?');
  assert.equal(selectCanAsk(state), true);
});

test('qa: duplicate asks while asking are ignored', () => {
  let state = ask(createInitialQaState(), 1);
  const active = state;
  state = ask(state, 2);

  assert.equal(state, active);
});

test('qa: a stale response after a contract change is ignored', () => {
  let state = ask(createInitialQaState(), 1);
  state = qaReducer(state, { type: QA_EVENT.RESET });

  const afterReset = state;
  state = qaReducer(state, {
    type: QA_EVENT.ASK_SUCCEED,
    requestId: 1,
    answer: 'Old contract answer.',
  });
  assert.equal(state, afterReset);

  state = qaReducer(state, {
    type: QA_EVENT.ASK_FAIL,
    requestId: 1,
    error: 'Old failure.',
  });
  assert.equal(state, afterReset);
});

test('qa: failure can be retried and clears the old answer', () => {
  let state = ask(createInitialQaState(), 1);
  state = qaReducer(state, {
    type: QA_EVENT.ASK_FAIL,
    requestId: 1,
    error: 'Q&A service is temporarily unavailable.',
  });

  assert.equal(state.status, QA_STATUS.ERROR);
  assert.equal(state.error, 'Q&A service is temporarily unavailable.');
  assert.equal(state.answer, '');

  state = ask(state, 2);
  assert.equal(state.status, QA_STATUS.ASKING);
  assert.equal(state.error, '');
});

test('qa: the question limit is derived, not a separate flag', () => {
  let state = createInitialQaState();
  for (let index = 0; index < MAX_QUESTIONS; index += 1) {
    state = ask(state, index + 1);
    state = qaReducer(state, {
      type: QA_EVENT.ASK_SUCCEED,
      requestId: index + 1,
      answer: `Answer ${index + 1}`,
    });
  }

  assert.equal(state.count, MAX_QUESTIONS);
  assert.equal(selectQaStatus(state), QA_STATUS.LIMIT);
  assert.equal(selectCanAsk(state), false);

  const exhausted = state;
  state = ask(state, MAX_QUESTIONS + 1);
  assert.equal(state, exhausted);
});

test('qa machine: every declared event has a valid target state', () => {
  const states = new Set(Object.values(QA_STATUS));
  for (const transitions of Object.values(QA_MACHINE.transitions)) {
    for (const target of Object.values(transitions)) {
      assert.ok(states.has(target), `unknown target: ${target}`);
    }
  }
});
