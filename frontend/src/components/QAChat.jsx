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
    setCount(0); setHistory([]); setAnswer(''); setError(''); setShowExamples(true);
  }, [contractText]);

  const handleAsk = async (q) => {
    const query = q || question.trim();
    if (!query || count >= MAX_QUESTIONS) return;
    setLoading(true); setError(''); setAnswer(''); setShowExamples(false);
    try {
      const result = await askQuestion(contractText, query);
      const response = result.answer || 'No answer returned.';
      setAnswer(response);
      setHistory((prev) => [{ question: query, answer: response, id: Date.now() }, ...prev]);
      setQuestion(''); setCount((c) => c + 1);
    } catch (err) {
      setError(err.message || 'Failed to get answer.');
    } finally { setLoading(false); }
  };

  const handleKeyDown = (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleAsk(); } };
  const progressColor = count >= MAX_QUESTIONS ? 'bg-red-500' : count >= 7 ? 'bg-amber-500' : 'bg-emerald-500';

  return (
    <div className="card overflow-hidden no-print animate-slide-up">
      <button onClick={() => setCollapsed(!collapsed)} className="w-full flex items-center justify-between px-5 py-4">
        <h3 className="font-semibold flex items-center gap-2 text-white">
          <MessageCircle className="w-5 h-5 text-accent-400" />
          Ask About This Contract
          <span className="text-[10px] font-normal text-white/30 ml-1">({count}/{MAX_QUESTIONS})</span>
        </h3>
        <div className="flex items-center gap-3">
          <div className="w-16 h-1.5 bg-white/10 rounded-full overflow-hidden">
            <div className={`h-full rounded-full transition-all duration-500 ${progressColor}`} style={{ width: `${(count / MAX_QUESTIONS) * 100}%` }} />
          </div>
          {collapsed ? <ChevronDown className="w-4 h-4 text-white/30" /> : <ChevronUp className="w-4 h-4 text-white/30" />}
        </div>
      </button>

      {!collapsed && (
        <div className="px-5 pb-5 space-y-4">
          {count >= MAX_QUESTIONS && (
            <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-3 flex items-start gap-2">
              <Sparkles className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
              <p className="text-sm text-amber-300/80">Daily question limit reached. Download the full report.</p>
            </div>
          )}
          {error && <div className="bg-red-500/10 text-red-400 text-sm p-3 rounded-xl border border-red-500/20 animate-slide-up">{error}</div>}

          {(answer || loading) && (
            <div className="bg-accent-500/5 rounded-xl p-4 border border-accent-500/10 animate-scale-in">
              {loading ? (
                <div className="flex items-center gap-2 text-accent-400 text-sm"><Loader className="w-4 h-4 animate-spin" /><span className="font-medium">Analyzing contract...</span></div>
              ) : (
                <div>
                  <p className="text-xs font-bold text-accent-400 uppercase tracking-wider mb-2 flex items-center gap-1.5"><Sparkles className="w-3.5 h-3.5" />Answer</p>
                  <p className="text-sm text-white/70 leading-relaxed break-words">{answer}</p>
                </div>
              )}
            </div>
          )}

          {/* Input + button — stacks on mobile */}
          <div className="flex flex-col sm:flex-row gap-2">
            <input ref={inputRef} type="text" value={question} onChange={(e) => setQuestion(e.target.value)} onKeyDown={handleKeyDown}
              placeholder={count >= MAX_QUESTIONS ? 'Question limit reached' : 'Ask a question about your contract...'}
              disabled={loading || count >= MAX_QUESTIONS}
              className="flex-1 px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-sm text-white placeholder-white/30
                         focus:outline-none focus:ring-2 focus:ring-accent-400 focus:border-accent-400
                         disabled:opacity-50 disabled:cursor-not-allowed"
              aria-label="Type your question"
            />
            <button onClick={() => handleAsk()} disabled={loading || !question.trim() || count >= MAX_QUESTIONS}
              className="sm:w-auto w-full px-5 py-3 bg-accent-500 text-white rounded-xl font-semibold text-sm hover:bg-accent-600 transition
                         disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 active:scale-95 shrink-0"
              aria-label="Send question">
              {loading ? <Loader className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />} Ask
            </button>
          </div>

          {showExamples && history.length === 0 && !answer && count === 0 && (
            <div>
              <p className="text-xs font-bold text-white/30 uppercase tracking-wider mb-3 flex items-center gap-1.5"><HelpCircle className="w-3.5 h-3.5" />Try asking</p>
              <div className="flex flex-wrap gap-2">
                {EXAMPLE_QUESTIONS.map((eq, i) => (
                  <button key={i} onClick={() => handleAsk(eq)} disabled={loading}
                    className="text-xs bg-white/5 hover:bg-accent-500/10 text-white/50 hover:text-accent-400 px-3.5 py-2 rounded-full transition border border-white/10 hover:border-accent-500/20">{eq}</button>
                ))}
              </div>
            </div>
          )}

          {history.length > 0 && (
            <div className="space-y-3 max-h-64 overflow-y-auto">
              <p className="text-xs font-bold text-white/30 uppercase tracking-wider">Previous ({history.length})</p>
              {history.map((h) => (
                <details key={h.id} className="text-sm group">
                  <summary className="cursor-pointer text-white/50 hover:text-white transition py-1">{h.question}</summary>
                  <p className="mt-2 text-white/40 bg-white/[0.03] p-3 rounded-xl border border-white/5 leading-relaxed break-words">{h.answer}</p>
                </details>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
