import { useState, useEffect, useRef } from 'react';
import { MessageCircle, Send, Loader, HelpCircle, Sparkles, ChevronDown, ChevronUp } from 'lucide-react';

const MAX_QUESTIONS = 10;
const EXAMPLE_QUESTIONS = [
  'What is my notice period?',
  'Are there any hidden penalties?',
  'Can they fire me without cause?',
  'Is the non-compete enforceable?',
  'What happens to my benefits if I leave?',
];

/**
 * QAChat — Floating/embedded chat panel for asking contract questions.
 *
 * @param {Object} props
 * @param {string} props.contractText — Full contract text for context
 * @param {Function} props.askQuestion — Async function (text, question) => { answer }
 */
export default function QAChat({ contractText, askQuestion }) {
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [history, setHistory] = useState([]);
  const [count, setCount] = useState(0);
  const [collapsed, setCollapsed] = useState(false);
  const [showExamples, setShowExamples] = useState(true);
  const inputRef = useRef(null);

  useEffect(() => {
    setCount(0);
    setHistory([]);
    setAnswer('');
    setError('');
    setShowExamples(true);
  }, [contractText]);

  const handleAsk = async (q) => {
    const query = q || question.trim();
    if (!query || count >= MAX_QUESTIONS) return;

    setLoading(true);
    setError('');
    setAnswer('');
    setShowExamples(false);

    try {
      const result = await askQuestion(contractText, query);
      const response = result.answer || 'No answer returned.';
      setAnswer(response);
      setHistory((prev) => [{ question: query, answer: response, id: Date.now() }, ...prev]);
      setQuestion('');
      setCount((c) => c + 1);
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

  const progressColor = count >= MAX_QUESTIONS ? 'bg-red-500' : count >= 7 ? 'bg-amber-500' : 'bg-emerald-500';

  return (
    <div className="card overflow-hidden no-print animate-slide-up">
      {/* ── Header ──────────────────────── */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="w-full flex items-center justify-between px-5 py-4 bg-gradient-to-r from-navy-950 to-navy-900 text-white"
      >
        <h3 className="font-semibold flex items-center gap-2">
          <MessageCircle className="w-5 h-5 text-accent-400" />
          Ask About This Contract
          <span className="text-[10px] font-normal text-slate-400 ml-1">
            ({count}/{MAX_QUESTIONS})
          </span>
        </h3>
        <div className="flex items-center gap-3">
          <div className="w-16 h-1.5 bg-white/10 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${progressColor}`}
              style={{ width: `${(count / MAX_QUESTIONS) * 100}%` }}
            />
          </div>
          {collapsed ? (
            <ChevronDown className="w-4 h-4 text-slate-400" />
          ) : (
            <ChevronUp className="w-4 h-4 text-slate-400" />
          )}
        </div>
      </button>

      {!collapsed && (
        <div className="p-5 space-y-4">
          {/* ── Limit Warning ────────────── */}
          {count >= MAX_QUESTIONS && (
            <div className="bg-amber-50 border border-amber-200 rounded-xl p-3 flex items-start gap-2">
              <Sparkles className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
              <p className="text-sm text-amber-800">
                Daily question limit reached. Download the full report for complete analysis.
              </p>
            </div>
          )}

          {/* ── Error ────────────────────── */}
          {error && (
            <div className="bg-red-50 text-red-700 text-sm p-3 rounded-xl border border-red-200 animate-slide-up">
              {error}
            </div>
          )}

          {/* ── Answer Display ───────────── */}
          {(answer || loading) && (
            <div className="bg-accent-50 rounded-xl p-4 border border-accent-100 animate-scale-in">
              {loading ? (
                <div className="flex items-center gap-2 text-accent-600 text-sm">
                  <Loader className="w-4 h-4 animate-spin" />
                  <span className="font-medium">Analyzing contract...</span>
                </div>
              ) : (
                <div>
                  <p className="text-xs font-bold text-accent-600 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5" />
                    Answer
                  </p>
                  <p className="text-sm text-slate-700 leading-relaxed">{answer}</p>
                </div>
              )}
            </div>
          )}

          {/* ── Input ────────────────────── */}
          <div className="flex gap-2">
            <input
              ref={inputRef}
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={
                count >= MAX_QUESTIONS
                  ? 'Question limit reached'
                  : 'Ask a question about your contract...'
              }
              disabled={loading || count >= MAX_QUESTIONS}
              className="flex-1 px-4 py-3 border border-slate-300 rounded-xl text-sm
                         focus:outline-none focus:ring-2 focus:ring-accent-400 focus:border-accent-400
                         disabled:bg-slate-100 disabled:text-slate-400
                         placeholder:text-slate-400"
              aria-label="Type your question"
            />
            <button
              onClick={() => handleAsk()}
              disabled={loading || !question.trim() || count >= MAX_QUESTIONS}
              className="px-5 py-3 bg-accent-500 text-white rounded-xl font-semibold text-sm
                         hover:bg-accent-600 transition shadow-lg shadow-accent-500/20
                         disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-accent-500
                         flex items-center gap-2 active:scale-95"
              aria-label="Send question"
            >
              {loading ? (
                <Loader className="w-4 h-4 animate-spin" />
              ) : (
                <Send className="w-4 h-4" />
              )}
              Ask
            </button>
          </div>

          {/* ── Example Questions ────────── */}
          {showExamples && history.length === 0 && !answer && count === 0 && (
            <div>
              <p className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-1.5">
                <HelpCircle className="w-3.5 h-3.5" />
                Try asking
              </p>
              <div className="flex flex-wrap gap-2">
                {EXAMPLE_QUESTIONS.map((eq, i) => (
                  <button
                    key={i}
                    onClick={() => handleAsk(eq)}
                    disabled={loading}
                    className="text-xs bg-slate-100 hover:bg-accent-50 hover:text-accent-700
                               text-slate-600 px-3.5 py-2 rounded-full transition font-medium
                               border border-slate-200 hover:border-accent-200"
                  >
                    {eq}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* ── History ──────────────────── */}
          {history.length > 0 && (
            <div className="space-y-3 max-h-64 overflow-y-auto">
              <p className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                Previous ({history.length})
              </p>
              {history.map((h) => (
                <details key={h.id} className="text-sm group">
                  <summary className="cursor-pointer text-slate-600 font-medium hover:text-accent-600 transition py-1">
                    {h.question}
                  </summary>
                  <p className="mt-2 text-slate-500 bg-slate-50 p-3 rounded-xl border border-slate-100 leading-relaxed">
                    {h.answer}
                  </p>
                </details>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
