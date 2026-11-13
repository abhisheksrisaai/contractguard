import { useState, useReducer, useEffect, useCallback, useRef } from 'react';
import ErrorBoundary from './components/ErrorBoundary';
import AnalysisProgress from './components/AnalysisProgress';
import Navbar from './components/Navbar';
import HeroSection from './components/HeroSection';
import ContractTypeSelector from './components/ContractTypeSelector';
import OutcomesStrip from './components/OutcomesStrip';
import HowItWorks from './components/HowItWorks';
import FAQ from './components/FAQ';
import UploadZone from './components/UploadZone';
import RedFlagBanner from './components/RedFlagBanner';
import FindingsList from './components/FindingsList';
import NegotiationPanel from './components/NegotiationPanel';
import MissingClauses from './components/MissingClauses';
import RiskBrief from './components/results/RiskBrief';
import ClauseLedger from './components/results/ClauseLedger';
import QAChat from './components/QAChat';
import Footer from './components/Footer';
import { ToastContainer } from './components/Toast';
import { askQuestion, downloadReport } from './services/api';
import {
  ANALYSIS_EVENT,
  ANALYSIS_OUTCOME,
  ANALYSIS_PHASE,
  REPORT_STATUS,
  analysisReducer,
  createInitialAnalysisState,
  selectAppState,
} from './state/analysisMachine';
import {
  Download, RefreshCw, Loader, AlertTriangle, X,
} from 'lucide-react';

let toastId = 0;

export default function App() {
  const [analysisState, dispatch] = useReducer(
    analysisReducer,
    undefined,
    createInitialAnalysisState,
  );
  const [toasts, setToasts] = useState([]);
  const [selectedType, setSelectedType] = useState(null);
  const runSeqRef = useRef(0);
  const activeRunRef = useRef(null);
  const selectedModel = 'qwen/qwen3.8-27b';

  const {
    analysis, error, outcome, phase, progress, report,
  } = analysisState;
  const loading = phase === ANALYSIS_PHASE.ANALYZING;
  const isPartial = outcome === ANALYSIS_OUTCOME.PARTIAL;
  const isDownloading = report.status === REPORT_STATUS.GENERATING;
  const appState = selectAppState(analysisState);

  const addToast = useCallback((message, type = 'info') => {
    const id = ++toastId;
    setToasts((prev) => [...prev, { id, message, type }]);
  }, []);

  const removeToast = useCallback((id) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  }, []);

  const scrollToUpload = () => document.getElementById('upload')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  const scrollToHow = () => document.getElementById('how-it-works')?.scrollIntoView({ behavior: 'smooth', block: 'start' });

  const handleStartAnalysis = useCallback(() => {
    const runId = ++runSeqRef.current;
    activeRunRef.current = runId;
    dispatch({ type: ANALYSIS_EVENT.START, runId });
    return runId;
  }, []);

  const handleAnalysisComplete = (data, runId) => {
    if (runId != null && runId !== activeRunRef.current) return;
    activeRunRef.current = null;
    dispatch({ type: ANALYSIS_EVENT.SUCCEED, runId, result: data });
    const highCount = data.risk_breakdown?.High || 0;
    addToast(
      highCount > 0
        ? `Found ${highCount} high-risk clause${highCount > 1 ? 's' : ''} — review carefully.`
        : 'Analysis complete — see report below.',
      highCount > 0 ? 'warning' : 'success',
    );
    setTimeout(() => { document.getElementById('results')?.scrollIntoView({ behavior: 'smooth', block: 'start' }); }, 300);
  };

  const handleAnalysisFailure = (message, runId) => {
    if (runId != null && runId !== activeRunRef.current) return;
    if (!message) {
      dispatch({ type: ANALYSIS_EVENT.ERROR_DISMISSED });
      return;
    }
    activeRunRef.current = null;
    if (runId == null) {
      dispatch({ type: ANALYSIS_EVENT.ERROR_SET, error: message });
    } else {
      dispatch({ type: ANALYSIS_EVENT.FAIL, runId, error: message });
    }
    addToast(message, 'error');
  };

  const resetAnalysis = () => {
    activeRunRef.current = null;
    dispatch({ type: ANALYSIS_EVENT.RESET });
  };

  const handleReset = () => {
    resetAnalysis();
    window.scrollTo({ top: 0, behavior: 'smooth' });
    addToast('Ready for a new contract.', 'info');
  };

  const handleNewAnalysis = () => {
    resetAnalysis();
    window.scrollTo({ top: 0, behavior: 'smooth' });
    window.setTimeout(scrollToUpload, 120);
  };

  const handleHome = () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleUploadCta = () => {
    resetAnalysis();
    window.setTimeout(scrollToUpload, 120);
  };

  const handleDismissError = () => {
    dispatch({ type: ANALYSIS_EVENT.ERROR_DISMISSED });
  };

  const handleDownload = async () => {
    if (!analysis || report.status === REPORT_STATUS.GENERATING) return;
    dispatch({ type: ANALYSIS_EVENT.REPORT_START });
    try {
      await downloadReport(analysis);
      dispatch({ type: ANALYSIS_EVENT.REPORT_SUCCEED });
      addToast('Report downloaded!', 'success');
    } catch (err) {
      const message = err.message || 'Download failed.';
      dispatch({ type: ANALYSIS_EVENT.REPORT_FAIL, error: message });
      addToast(message, 'error');
    }
  };

  useEffect(() => {
    const handler = (event) => {
      if ((event.ctrlKey || event.metaKey) && event.key === 'u') {
        event.preventDefault();
        handleNewAnalysis();
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  // ── Loading ────────────────────────────────────────────────
  if (loading) {
    return (
      <ErrorBoundary onReset={handleReset}>
        <div
          className="min-h-screen flex flex-col bg-black"
          data-app-state={appState}
          aria-busy="true"
        >
          <Navbar
            compact
            onReset={handleReset}
            showReset
            onUpload={handleUploadCta}
            onHome={handleHome}
          />
          <main className="flex-1 flex items-center justify-center">
            <AnalysisProgress uploadProgress={progress} />
          </main>
          <Footer />
          <ToastContainer toasts={toasts} removeToast={removeToast} />
        </div>
      </ErrorBoundary>
    );
  }

  // ── Landing ────────────────────────────────────────────────
  if (!analysis) {
    return (
      <ErrorBoundary onReset={handleReset}>
        <div
          className="min-h-screen flex flex-col bg-black overflow-x-hidden"
          data-app-state={appState}
        >
          <Navbar
            onUpload={handleUploadCta}
            onHome={handleHome}
          />
          {error && (
            <div className="px-4 pt-4 sm:px-6" data-state="error">
              <div
                role="alert"
                className="mx-auto flex max-w-4xl items-start gap-3 rounded-2xl border border-red-500/20 bg-red-500/10 p-4"
              >
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-red-400" />
                <div className="flex-1">
                  <h3 className="text-sm font-semibold text-red-400">Analysis error</h3>
                  <p className="mt-0.5 text-sm text-red-300/80">{error}</p>
                </div>
                <button
                  type="button"
                  onClick={handleDismissError}
                  className="text-red-400 transition hover:text-red-300"
                  aria-label="Dismiss error"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            </div>
          )}
          <HeroSection onUploadClick={scrollToUpload} onHowItWorksClick={scrollToHow} />
          <section className="py-10 sm:py-12 px-4 sm:px-6 lg:px-8 bg-[#0A0A0A] border-y border-white/5">
            <div className="max-w-4xl mx-auto space-y-6">
              <ContractTypeSelector selected={selectedType} onChange={setSelectedType} />
            </div>
          </section>
          <OutcomesStrip />
          <HowItWorks />
          <section className="py-12 sm:py-16 px-4 sm:px-6 bg-[#0A0A0A] border-y border-white/5">
            <div className="max-w-4xl mx-auto">
              <div className="text-center mb-8">
                <h2 className="text-2xl sm:text-3xl font-bold text-white tracking-tight mb-2">What we check</h2>
                <p className="text-white/40 text-sm">Every contract is reviewed across these dimensions</p>
              </div>
              <div className="grid sm:grid-cols-2 gap-3 max-w-2xl mx-auto">
                {['5C Enforceability Validation', 'Payment Terms & Pricing', 'Delivery Schedule & Incoterms', 'Warranty & Defect Liability', 'Liability Caps & Indemnities', 'Termination Rights & Exit', 'Insurance & Performance Security', 'Dispute Resolution & Governing Law', 'Regulatory & Tax Compliance', 'Missing Clauses & Protections'].map((item) => (
                  <div key={item} className="flex items-center gap-2.5 text-sm text-white/50">
                    <div className="w-4 h-4 rounded bg-accent-500/10 border border-accent-500/20 flex items-center justify-center shrink-0">
                      <svg className="w-2.5 h-2.5 text-accent-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" /></svg>
                    </div>
                    {item}
                  </div>
                ))}
              </div>
            </div>
          </section>
          <section id="upload-section" className="py-12 sm:py-16 px-4 sm:px-6">
            <div className="max-w-7xl mx-auto">
              <div className="text-center mb-8">
                <h2 className="text-2xl sm:text-3xl font-bold text-white mb-2">Ready to analyze your contract?</h2>
                <p className="text-white/40 text-sm">Upload a PDF and get results, usually in 1–4 minutes</p>
              </div>
              <UploadZone
                onAnalysisComplete={handleAnalysisComplete}
                onStartAnalysis={handleStartAnalysis}
                onProgress={(pct, runId) => dispatch({
                  type: ANALYSIS_EVENT.PROGRESS,
                  runId,
                  progress: pct,
                })}
                onError={handleAnalysisFailure}
                selectedType={selectedType}
                selectedModel={selectedModel}
              />
            </div>
          </section>
          <FAQ />
          <Footer />
          <ToastContainer toasts={toasts} removeToast={removeToast} />
        </div>
      </ErrorBoundary>
    );
  }

  // ── Results ────────────────────────────────────────────────
  const clauses = analysis?.clauses || [];
  const contractText = clauses.map((clause) => clause.content).join('\n\n');

  return (
    <ErrorBoundary onReset={handleReset}>
      <div
        className="min-h-screen flex flex-col bg-black overflow-x-hidden"
        data-app-state={appState}
        data-analysis-status={outcome}
        data-report-state={report.status}
      >
        <Navbar
          compact
          onReset={handleReset}
          showReset
          onUpload={handleUploadCta}
          onHome={handleHome}
        />
        <main className="mx-auto w-full max-w-7xl flex-1 space-y-7 px-4 py-6 sm:px-6 sm:py-8 lg:px-8" id="results">

          {error && (
            <div
              className="flex items-start gap-3 rounded-2xl border border-red-500/20 bg-red-500/10 p-4 animate-slide-up"
              role="alert"
            >
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-red-400" />
              <div className="flex-1">
                <h3 className="text-sm font-semibold text-red-400">Analysis error</h3>
                <p className="mt-0.5 text-sm text-red-300/80">{error}</p>
              </div>
              <button type="button" onClick={handleDismissError} className="text-red-400 transition hover:text-red-300" aria-label="Dismiss error">
                <X className="h-4 w-4" />
              </button>
            </div>
          )}

          <RiskBrief analysis={analysis} isPartial={isPartial} />

          <RedFlagBanner redFlags={analysis?.red_flags} />

          <FindingsList findings={analysis?.findings} />

          <ClauseLedger
            clauses={clauses}
            onAskQuestions={() => document.getElementById('qa-chat')?.scrollIntoView({ behavior: 'smooth', block: 'start' })}
          />

          <NegotiationPanel opportunities={analysis?.negotiation_opportunities} addToast={addToast} />

          <MissingClauses missingClauses={analysis?.missing_clauses} />

          <section id="qa-chat" className="animate-slide-up">
            <QAChat contractText={contractText} askQuestion={askQuestion} model={selectedModel} />
          </section>

          <div className="flex flex-col justify-center gap-3 pb-2 pt-4 sm:flex-row animate-slide-up">
            <button onClick={handleDownload} disabled={isDownloading} className="btn-primary inline-flex items-center justify-center gap-2 !px-8 !py-3.5">
              {isDownloading ? <Loader className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
              {isDownloading ? 'Generating report...' : 'Download report'}
            </button>
            <button onClick={handleReset} className="btn-secondary inline-flex items-center justify-center gap-2 !px-8 !py-3.5">
              <RefreshCw className="h-4 w-4" /> Analyze another contract
            </button>
          </div>
          {report.error && (
            <p role="alert" className="text-center text-xs text-red-400/80">{report.error}</p>
          )}

        </main>
        <Footer />
        <ToastContainer toasts={toasts} removeToast={removeToast} />
      </div>
    </ErrorBoundary>
  );
}
