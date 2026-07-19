import { useState, useEffect, useCallback } from 'react';
import ErrorBoundary from './components/ErrorBoundary';
import LoadingSpinner from './components/LoadingSpinner';
import Upload from './components/Upload';
import RiskDashboard from './components/RiskDashboard';
import ClauseCard from './components/ClauseCard';
import QAChat from './components/QAChat';
import { ToastContainer } from './components/Toast';
import { Shield, FileText } from 'lucide-react';

let toastId = 0;

export default function App() {
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [toasts, setToasts] = useState([]);

  // ── Toast Helpers ────────────────────────────────────────
  const addToast = useCallback((message, type = 'info') => {
    const id = ++toastId;
    setToasts((prev) => [...prev, { id, message, type }]);
  }, []);

  const removeToast = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  // ── Analysis Handlers ────────────────────────────────────
  const handleAnalysisComplete = (data) => {
    setAnalysis(data);
    setLoading(false);
    setError('');
    const highCount = data.risk_breakdown?.High || 0;
    if (highCount > 0) {
      addToast(
        `Analysis complete. ${highCount} high-risk clause${highCount > 1 ? 's' : ''} found.`,
        'warning'
      );
    } else {
      addToast('Analysis complete. No high-risk clauses found.', 'success');
    }
  };

  const handleReset = () => {
    setAnalysis(null);
    setError('');
    addToast('Ready for a new contract.', 'info');
  };

  // ── Keyboard Shortcuts ──────────────────────────────────
  useEffect(() => {
    const handler = (e) => {
      // Ctrl+U or Cmd+U → reset to upload
      if ((e.ctrlKey || e.metaKey) && e.key === 'u') {
        e.preventDefault();
        handleReset();
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  return (
    <ErrorBoundary onReset={handleReset}>
      <div className="min-h-screen flex flex-col">
        {/* ── Header ─────────────────────── */}
        <header className="bg-gradient-to-r from-slate-900 via-slate-800 to-slate-900 text-white px-6 py-4 shadow-lg no-print">
          <div className="max-w-7xl mx-auto flex items-center gap-3">
            <Shield className="w-8 h-8 text-blue-400" />
            <div className="flex-1">
              <h1 className="text-xl font-bold tracking-tight">ContractGuard</h1>
              <p className="text-xs text-slate-400">AI-Powered Contract Risk Analysis</p>
            </div>
            {analysis && (
              <button
                onClick={handleReset}
                className="text-xs text-slate-300 hover:text-white transition px-3 py-1.5 border border-slate-600 rounded-lg"
                title="Ctrl+U to reset"
              >
                New Analysis
              </button>
            )}
          </div>
        </header>

        {/* ── Main Content ────────────────── */}
        <main className="flex-1 max-w-7xl mx-auto w-full px-4 py-8">
          {/* Error Banner */}
          {error && (
            <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4 flex items-start gap-3 animate-slide-in">
              <span className="text-red-500 text-lg shrink-0">⚠</span>
              <div className="flex-1">
                <h3 className="font-semibold text-red-800 text-sm">Error</h3>
                <p className="text-red-700 text-sm mt-0.5">{error}</p>
              </div>
              <button
                onClick={() => setError('')}
                className="text-red-400 hover:text-red-600"
              >
                ✕
              </button>
            </div>
          )}

          {/* Loading State */}
          {loading && (
            <LoadingSpinner
              message="Analyzing your contract..."
              size="lg"
              fullPage
            />
          )}

          {/* Upload Page */}
          {!analysis && !loading && (
            <div className="space-y-6">
              <div className="text-center mb-8">
                <FileText className="w-16 h-16 text-blue-500 mx-auto mb-4" />
                <h2 className="text-3xl font-bold text-slate-800 mb-2">
                  Analyze Your Contract
                </h2>
                <p className="text-slate-500 max-w-md mx-auto">
                  Upload a PDF contract and our AI will identify risks, explain
                  concerns, and suggest fairer alternatives — in minutes.
                </p>
              </div>
              <Upload
                onAnalysisComplete={handleAnalysisComplete}
                onLoading={(v) => setLoading(v)}
                onError={(e) => {
                  setError(e);
                  setLoading(false);
                  addToast(e, 'error');
                }}
              />
            </div>
          )}

          {/* Results Dashboard */}
          {analysis && !loading && (
            <div className="space-y-8">
              <RiskDashboard analysis={analysis} onReset={handleReset} />

              {/* Clause Cards */}
              <div>
                <h3 className="text-lg font-bold text-slate-800 mb-4 flex items-center gap-2">
                  <FileText className="w-5 h-5 text-blue-500" />
                  Detailed Clause Analysis
                  <span className="text-sm font-normal text-slate-400">
                    ({analysis.clauses?.length || 0} clauses)
                  </span>
                </h3>
                <div className="space-y-3">
                  {analysis.clauses?.map((clause) => (
                    <ClauseCard key={clause.id} clause={clause} />
                  ))}
                </div>
              </div>

              {/* Q&A Section */}
              <QAChat
                contractText={
                  analysis.clauses?.map((c) => c.content).join('\n\n') || ''
                }
              />
            </div>
          )}
        </main>

        {/* ── Footer ──────────────────────── */}
        <footer className="bg-slate-900 text-slate-500 text-xs text-center py-4 px-4 no-print">
          <p>
            <strong className="text-slate-400">⚠ Disclaimer:</strong> This
            tool provides informational analysis only and does not constitute
            legal advice. Always consult a qualified attorney before making
            legal decisions.
          </p>
          <p className="mt-1">ContractGuard © {new Date().getFullYear()}</p>
        </footer>
      </div>

      {/* ── Toast Notifications ──────────── */}
      <ToastContainer toasts={toasts} removeToast={removeToast} />
    </ErrorBoundary>
  );
}
