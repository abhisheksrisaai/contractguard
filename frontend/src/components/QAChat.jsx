import { useState, useEffect } from 'react';
import { MessageCircle, Send, Loader, HelpCircle, AlertTriangle } from 'lucide-react';
import { askQuestion } from '../services/api';

const MAX_QUESTIONS = 10;
const EXAMPLE_QUESTIONS = [
  'What is the notice period for termination?',
  'Is there a late payment penalty?',
  'Who owns the intellectual property?',
  'What is the liability cap?',
  'Are there any non-compete restrictions?',
];

export default function QAChat({ contractText, onReset }) {
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [history, setHistory] = useState([]);
  const [questionCount, setQuestionCount] = useState(0);
  const [limitReached, setLimitReached] = useState(false);

  // Reset count when contract changes (parent calls onReset)
  useEffect(() => {
    setQuestionCount(0);
    setLimitReached(false);
    setHistory([]);
    setAnswer('');
    setError('');
  }, [contractText]);

  const handleAsk = async (q) => {
    const query = q || question.trim();
    if (!query || limitReached) return;

    if (questionCount >= MAX_QUESTIONS) {
      setLimitReached(true);
      return;
    }

    setLoading(true);
    setError('');
    setAnswer('');

    try {
      const result = await askQuestion(contractText, query);
      const response = result.answer || 'No answer returned.';
      setAnswer(response);
      setHistory((prev) => [
        { question: query, answer: response, id: Date.now() },
        ...prev,
      ]);
      setQuestion('');
      setQuestionCount((prev) => {
        const next = prev + 1;
        if (next >= MAX_QUESTIONS) setLimitReached(true);
        return next;
      });
    } catch (err) {
      setError(err.message || 'Failed to get answer.');
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleAsk();
    }
  };

  const countColor =
    questionCount >= MAX_QUESTIONS ? 'text-red-600' :
    questionCount >= 7 ? 'text-amber-600' :
    'text-green-600';

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden no-print">
      {/* Header */}
      <div className="px-5 py-4 border-b border-slate-100 bg-slate-50/50 flex items-center justify-between">
        <h3 className="font-semibold text-slate-800 flex items-center gap-2">
          <MessageCircle className="w-5 h-5 text-blue-500" />
          Ask About This Contract
        </h3>
        <span className={`text-xs font-semibold ${countColor} bg-white px-2.5 py-1 rounded-full border`}>
          {questionCount}/{MAX_QUESTIONS}
        </span>
      </div>

      <div className="p-5 space-y-4">
        {/* Limit Reached Banner */}
        {limitReached && (
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
            <p className="text-sm text-amber-800">
              Daily question limit reached ({MAX_QUESTIONS}/{MAX_QUESTIONS}). Download the full report for complete analysis.
            </p>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="bg-red-50 text-red-700 text-sm p-3 rounded-lg border border-red-200">
            {error}
          </div>
        )}

        {/* Answer Display */}
        {(answer || loading) && (
          <div className="bg-blue-50 rounded-lg p-4 border border-blue-100">
            {loading ? (
              <div className="flex items-center gap-2 text-blue-600 text-sm">
                <Loader className="w-4 h-4 animate-spin" />
                Thinking...
              </div>
            ) : (
              <div>
                <p className="text-xs font-semibold text-blue-500 uppercase tracking-wider mb-1">
                  Answer
                </p>
                <p className="text-sm text-slate-700 leading-relaxed">{answer}</p>
              </div>
            )}
          </div>
        )}

        {/* Input */}
        <div className="flex gap-2">
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              limitReached
                ? 'Question limit reached'
                : 'Ask a question about this contract...'
            }
            disabled={loading || limitReached}
            className="flex-1 px-4 py-2.5 border border-slate-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 focus:border-blue-400 disabled:bg-slate-100 disabled:text-slate-400"
          />
          <button
            onClick={() => handleAsk()}
            disabled={loading || !question.trim() || limitReached}
            className="px-4 py-2.5 bg-blue-600 text-white rounded-xl font-medium text-sm hover:bg-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1.5"
          >
            {loading ? (
              <Loader className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
            Ask
          </button>
        </div>

        {/* Question counter bar */}
        <div className="flex items-center gap-2">
          <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-300 ${
                questionCount >= MAX_QUESTIONS ? 'bg-red-500' :
                questionCount >= 7 ? 'bg-amber-500' :
                'bg-green-500'
              }`}
              style={{ width: `${(questionCount / MAX_QUESTIONS) * 100}%` }}
            />
          </div>
          <span className={`text-[10px] font-semibold ${countColor} w-10 text-right`}>
            {questionCount}/{MAX_QUESTIONS}
          </span>
        </div>

        {/* Example Questions */}
        {history.length === 0 && !answer && !limitReached && (
          <div>
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-1">
              <HelpCircle className="w-3.5 h-3.5" />
              Example Questions
            </p>
            <div className="flex flex-wrap gap-2">
              {EXAMPLE_QUESTIONS.map((eq, i) => (
                <button
                  key={i}
                  onClick={() => handleAsk(eq)}
                  disabled={loading || limitReached}
                  className="text-xs bg-slate-100 hover:bg-slate-200 text-slate-600 px-3 py-1.5 rounded-full transition disabled:opacity-50"
                >
                  {eq}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* History */}
        {history.length > 0 && (
          <div className="space-y-3 max-h-64 overflow-y-auto">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Previous Questions ({history.length})
            </p>
            {history.map((h) => (
              <details key={h.id} className="text-sm">
                <summary className="cursor-pointer text-slate-600 font-medium hover:text-blue-600 transition">
                  {h.question}
                </summary>
                <p className="mt-1 text-slate-500 bg-slate-50 p-2 rounded border border-slate-100">
                  {h.answer}
                </p>
              </details>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
