import { useState, useEffect, useCallback } from 'react';
import ErrorBoundary from './components/ErrorBoundary';
import LoadingSpinner from './components/LoadingSpinner';
import Navbar from './components/Navbar';
import HeroSection from './components/HeroSection';
import UploadZone from './components/UploadZone';
import RiskMeter from './components/RiskMeter';
import StatsBar from './components/StatsBar';
import ClauseAccordion from './components/ClauseAccordion';
import QAChat from './components/QAChat';
import Footer from './components/Footer';
import { ToastContainer } from './components/Toast';
import { askQuestion } from './services/api';
import { Download, RefreshCw, Loader, ArrowDown, ChevronRight, FileText } from 'lucide-react';
import { downloadReport } from './services/api';

let toastId = 0;

export default function App() {
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [toasts, setToasts] = useState([]);
  const [downloading, setDownloading] = useState(false);

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
    addToast(
      highCount > 0
        ? `Found ${highCount} high-risk clause${highCount > 1 ? 's' : ''} — review carefully.`
        : 'Analysis complete. No high-risk clauses found.',
      highCount > 0 ? 'warning' : 'success'
    );
    // Scroll to results
    setTimeout(() => {
      document.getElementById('results')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 300);
  };

  const handleReset = () => {
    setAnalysis(null);
    setError('');
    window.scrollTo({ top: 0, behavior: 'smooth' });
    addToast('Ready for a new contract.', 'info');
  };

  const handleDownload = async () => {
    if (!analysis) return;
    setDownloading(true);
    try {
      await downloadReport(analysis);
      addToast('Report downloaded successfully!', 'success');
    } catch (err) {
      addToast(err.message || 'Download failed.', 'error');
    } finally {
      setDownloading(false);
    }
  };

  const scrollToUpload = () => {
    document.getElementById('upload')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  };

  // ── Keyboard Shortcuts ──────────────────────────────────
  useEffect(() => {
    const handler = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'u') {
        e.preventDefault();
        handleReset();
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  // ── Landing Page ─────────────────────────────────────────
  if (!analysis && !loading) {
    return (
      <ErrorBoundary onReset={handleReset}>
        <div className="min-h-screen flex flex-col bg-[var(--color-bg)]">
          <Navbar />
          <HeroSection onUploadClick={scrollToUpload} />

          {/* How It Works */}
          <section id="how-it-works" className="py-16 md:py-20 px-4 sm:px-6">
            <div className="max-w-5xl mx-auto text-center mb-12">
              <h2 className="text-3xl md:text-4xl font-extrabold text-slate-900 mb-4">
                How It Works
              </h2>
              <p className="text-slate-500 max-w-lg mx-auto">
                Three simple steps to understand your contract before you sign.
              </p>
            </div>

            <div className="max-w-4xl mx-auto grid md:grid-cols-3 gap-6">
              {[
                { step: '1', icon: '📄', title: 'Upload Contract', desc: 'Drag & drop your PDF employment or service contract. We accept files up to 10MB.' },
                { step: '2', icon: '🤖', title: 'AI Analysis', desc: 'Our AI extracts every clause, scores risk levels, and compares against 20 fair templates.' },
                { step: '3', icon: '📊', title: 'Review & Download', desc: 'Get a detailed risk report with suggested alternatives. Download as PDF to share.' },
              ].map(({ step, icon, title, desc }) => (
                <div key={step} className="card p-6 text-center hover:-translate-y-1 transition-transform duration-300">
                  <div className="text-4xl mb-4">{icon}</div>
                  <div className="w-8 h-8 rounded-full bg-accent-500 text-white text-sm font-bold flex items-center justify-center mx-auto mb-3">
                    {step}
                  </div>
                  <h3 className="font-bold text-slate-800 mb-2">{title}</h3>
                  <p className="text-sm text-slate-500 leading-relaxed">{desc}</p>
                </div>
              ))}
            </div>
          </section>

          {/* Upload Section */}
          <section className="py-12 px-4 sm:px-6 bg-white border-y border-slate-200">
            <div className="max-w-7xl mx-auto">
              <div className="text-center mb-8">
                <h2 className="text-2xl md:text-3xl font-extrabold text-slate-900 mb-2">
                  Ready to Analyze Your Contract?
                </h2>
                <p className="text-slate-500">
                  Upload a PDF and get results in under 60 seconds.
                </p>
              </div>
              <UploadZone
                onAnalysisComplete={handleAnalysisComplete}
                onLoading={setLoading}
                onError={(e) => { setError(e); setLoading(false); addToast(e, 'error'); }}
              />
            </div>
          </section>

          <Footer />
          <ToastContainer toasts={toasts} removeToast={removeToast} />
        </div>
      </ErrorBoundary>
    );
  }

  // ── Loading State ────────────────────────────────────────
  if (loading) {
    return (
      <ErrorBoundary onReset={handleReset}>
        <div className="min-h-screen flex flex-col bg-[var(--color-bg)]">
          <Navbar compact onReset={handleReset} showReset />
          <main className="flex-1 flex items-center justify-center">
            <LoadingSpinner message="Analyzing your contract..." size="lg" />
          </main>
          <Footer />
        </div>
      </ErrorBoundary>
    );
  }

  // ── Results Dashboard ────────────────────────────────────
  const score = analysis?.overall_score ?? 0;
  const breakdown = analysis?.risk_breakdown || { High: 0, Medium: 0, Low: 0 };
  const clauses = analysis?.clauses || [];
  const contractText = clauses.map((c) => c.content).join('\n\n');

  return (
    <ErrorBoundary onReset={handleReset}>
      <div className="min-h-screen flex flex-col bg-[var(--color-bg)]">
        <Navbar compact onReset={handleReset} showReset />

        <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 py-8 space-y-8" id="results">

          {/* ── Error Banner ────────────── */}
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-2xl p-4 flex items-start gap-3 animate-slide-up">
              <span className="text-red-500 text-xl shrink-0">⚠</span>
              <div className="flex-1">
                <h3 className="font-semibold text-red-800 text-sm">Error</h3>
                <p className="text-red-700 text-sm mt-0.5">{error}</p>
              </div>
              <button onClick={() => setError('')} className="text-red-400 hover:text-red-600">✕</button>
            </div>
          )}

          {/* ── Risk Dashboard Card ──────── */}
          <div className="card p-6 md:p-8 animate-slide-up">
            <div className="flex flex-col lg:flex-row items-center gap-6 lg:gap-10">
              {/* Risk Meter */}
              <div className="relative">
                <RiskMeter score={score} size="lg" />
              </div>

              {/* Info + Stats */}
              <div className="flex-1 text-center lg:text-left space-y-4">
                <div>
                  <h2 className="text-2xl md:text-3xl font-extrabold text-slate-900">
                    Contract Risk Analysis
                  </h2>
                  <p className="text-slate-500 text-sm mt-1 max-w-lg">
                    {analysis?.assessment || 'Your contract has been analyzed clause by clause.'}
                  </p>
                </div>

                <StatsBar breakdown={breakdown} total={analysis?.total_clauses} />

                {/* Action Buttons */}
                <div className="flex flex-col sm:flex-row gap-3 pt-2">
                  <button onClick={handleDownload} disabled={downloading} className="btn-primary inline-flex items-center justify-center gap-2">
                    {downloading ? <Loader className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
                    {downloading ? 'Generating...' : 'Download PDF Report'}
                  </button>
                  <button onClick={handleReset} className="btn-secondary inline-flex items-center justify-center gap-2">
                    <RefreshCw className="w-4 h-4" />
                    Analyze Another
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* ── Clause Cards ─────────────── */}
          <section className="space-y-4 animate-slide-up" style={{ animationDelay: '0.2s' }}>
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-bold text-slate-800 flex items-center gap-2">
                <FileText className="w-5 h-5 text-accent-500" />
                Detailed Clause Analysis
                <span className="text-sm font-normal text-slate-400">
                  ({clauses.length} clause{clauses.length !== 1 ? 's' : ''})
                </span>
              </h3>
              <button
                onClick={() => document.getElementById('qa-chat')?.scrollIntoView({ behavior: 'smooth' })}
                className="text-sm text-accent-500 hover:text-accent-600 font-medium flex items-center gap-1"
              >
                Ask Questions
                <ArrowDown className="w-3.5 h-3.5" />
              </button>
            </div>
            <div className="space-y-3">
              {clauses.map((clause) => (
                <ClauseAccordion key={clause.id} clause={clause} />
              ))}
            </div>
          </section>

          {/* ── Q&A Chat ─────────────────── */}
          <section id="qa-chat" className="animate-slide-up" style={{ animationDelay: '0.3s' }}>
            <QAChat contractText={contractText} askQuestion={askQuestion} />
          </section>

        </main>

        <Footer />
        <ToastContainer toasts={toasts} removeToast={removeToast} />
      </div>
    </ErrorBoundary>
  );
}
