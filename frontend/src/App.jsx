import { useState, useEffect, useCallback } from 'react';
import ErrorBoundary from './components/ErrorBoundary';
import AnalysisProgress from './components/AnalysisProgress';
import Navbar from './components/Navbar';
import HeroSection from './components/HeroSection';
import ContractTypeSelector from './components/ContractTypeSelector';
import ModelSelector from './components/ModelSelector';
import OutcomesStrip from './components/OutcomesStrip';
import HowItWorks from './components/HowItWorks';
import FAQ from './components/FAQ';
import UploadZone from './components/UploadZone';
import ContractTypeBadge from './components/ContractTypeBadge';
import FiveCStrip from './components/FiveCStrip';
import RedFlagBanner from './components/RedFlagBanner';
import FindingsList from './components/FindingsList';
import NegotiationPanel from './components/NegotiationPanel';
import MissingClauses from './components/MissingClauses';
import ClauseAccordion from './components/ClauseAccordion';
import QAChat from './components/QAChat';
import Footer from './components/Footer';
import { ToastContainer } from './components/Toast';
import { askQuestion, downloadReport } from './services/api';
import { Download, RefreshCw, Loader, ArrowDown, FileText, Shield, Clock, FileWarning, CheckCircle2 } from 'lucide-react';

let toastId = 0;

function riskColor(score) {
  if (score >= 75) return { text: 'text-red-400', bg: 'bg-red-500', border: 'border-red-500/30', bgSoft: 'bg-red-500/10' };
  if (score >= 45) return { text: 'text-amber-400', bg: 'bg-amber-500', border: 'border-amber-500/30', bgSoft: 'bg-amber-500/10' };
  return { text: 'text-emerald-400', bg: 'bg-emerald-500', border: 'border-emerald-500/30', bgSoft: 'bg-emerald-500/10' };
}

function riskLabel(score) {
  if (score >= 75) return { word: 'HIGH RISK', action: 'RENEGOTIATE', sub: 'Major concerns — significant changes required before signing' };
  if (score >= 45) return { word: 'MEDIUM RISK', action: 'PROCEED WITH CAUTION', sub: 'Several areas of concern — negotiate key clauses' };
  return { word: 'LOW RISK', action: 'PROCEED', sub: 'Contract appears generally balanced and fair' };
}

export default function App() {
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [toasts, setToasts] = useState([]);
  const [downloading, setDownloading] = useState(false);
  const [selectedType, setSelectedType] = useState(null);
  const [selectedModel, setSelectedModel] = useState('auto');

  const addToast = useCallback((message, type = 'info') => {
    const id = ++toastId;
    setToasts((prev) => [...prev, { id, message, type }]);
  }, []);

  const removeToast = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const handleAnalysisComplete = (data) => {
    setAnalysis(data);
    setLoading(false);
    setError('');
    const highCount = data.risk_breakdown?.High || 0;
    addToast(highCount > 0 ? `Found ${highCount} high-risk clause${highCount > 1 ? 's' : ''} — review carefully.` : 'Analysis complete — see report below.', highCount > 0 ? 'warning' : 'success');
    setTimeout(() => { document.getElementById('results')?.scrollIntoView({ behavior: 'smooth', block: 'start' }); }, 300);
  };

  const handleReset = () => {
    setAnalysis(null); setError('');
    window.scrollTo({ top: 0, behavior: 'smooth' });
    addToast('Ready for a new contract.', 'info');
  };

  const handleDownload = async () => {
    if (!analysis) return;
    setDownloading(true);
    try { await downloadReport(analysis); addToast('Report downloaded!', 'success'); }
    catch (err) { addToast(err.message || 'Download failed.', 'error'); }
    finally { setDownloading(false); }
  };

  const scrollToUpload = () => document.getElementById('upload')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  const scrollToHow = () => document.getElementById('how-it-works')?.scrollIntoView({ behavior: 'smooth', block: 'start' });

  useEffect(() => {
    const handler = (e) => { if ((e.ctrlKey || e.metaKey) && e.key === 'u') { e.preventDefault(); handleReset(); } };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  // ── Landing ────────────────────────────────────────────────
  if (!analysis && !loading) {
    return (
      <ErrorBoundary onReset={handleReset}>
        <div className="min-h-screen flex flex-col bg-black overflow-x-hidden">
          <Navbar />
          <HeroSection onUploadClick={scrollToUpload} onHowItWorksClick={scrollToHow} />
          <section className="py-10 sm:py-12 px-4 sm:px-6 lg:px-8 bg-[#0A0A0A] border-y border-white/5">
            <div className="max-w-4xl mx-auto space-y-6">
              <ContractTypeSelector selected={selectedType} onChange={setSelectedType} />
              <ModelSelector selected={selectedModel} onChange={setSelectedModel} />
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
                {['5C Enforceability Validation','Payment Terms & Pricing','Delivery Schedule & Incoterms','Warranty & Defect Liability','Liability Caps & Indemnities','Termination Rights & Exit','Insurance & Performance Security','Dispute Resolution & Governing Law','Regulatory & Tax Compliance','Missing Clauses & Protections'].map((item) => (
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
                <p className="text-white/40 text-sm">Upload a PDF and get results in under 60 seconds</p>
              </div>
              <UploadZone
                onAnalysisComplete={handleAnalysisComplete}
                onLoading={setLoading}
                onError={(e) => { setError(e); setLoading(false); if (e) addToast(e, 'error'); }}
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

  // ── Loading ────────────────────────────────────────────────
  if (loading) {
    return (
      <ErrorBoundary onReset={handleReset}>
        <div className="min-h-screen flex flex-col bg-black">
          <Navbar compact onReset={handleReset} showReset />
          <main className="flex-1 flex items-center justify-center"><AnalysisProgress /></main>
          <Footer />
        </div>
      </ErrorBoundary>
    );
  }

  // ── Results ────────────────────────────────────────────────
  const score = analysis?.overall_score ?? 0;
  const breakdown = analysis?.risk_breakdown || { High: 0, Medium: 0, Low: 0 };
  const clauses = analysis?.clauses || [];
  const contractText = clauses.map((c) => c.content).join('\n\n');
  const rc = riskColor(score);
  const rl = riskLabel(score);

  return (
    <ErrorBoundary onReset={handleReset}>
      <div className="min-h-screen flex flex-col bg-black overflow-x-hidden">
        <Navbar compact onReset={handleReset} showReset />
        <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-6 sm:py-8 space-y-6" id="results">

          {/* Error */}
          {error && (
            <div className="bg-red-500/10 border border-red-500/20 rounded-2xl p-4 flex items-start gap-3 animate-slide-up">
              <span className="text-red-400 text-xl shrink-0">⚠</span>
              <div className="flex-1"><h3 className="font-semibold text-red-400 text-sm">Error</h3><p className="text-red-300/80 text-sm mt-0.5">{error}</p></div>
              <button onClick={() => setError('')} className="text-red-400 hover:text-red-300">✕</button>
            </div>
          )}

          {/* ── Header Row ─────────────────── */}
          <div className="flex flex-wrap items-center gap-3 animate-slide-up">
            <span className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px] font-bold uppercase tracking-wider px-3 py-1 rounded-full flex items-center gap-1.5 shrink-0">
              <CheckCircle2 className="w-3 h-3" /> Analysis Complete
            </span>
            <span className="text-sm text-white/50 truncate">{analysis?.filename || 'Contract'}</span>
            <ContractTypeBadge contractType={analysis?.contract_type} confidence={analysis?.type_confidence} />
            {analysis?.analysis_time_seconds && (
              <span className="text-[10px] text-white/30 ml-auto flex items-center gap-1 shrink-0">
                <Clock className="w-3 h-3" /> {analysis.analysis_time_seconds}s
              </span>
            )}
          </div>
          {/* ── AI Provider line ──────────── */}
          {(analysis?.ai_provider && analysis.ai_provider !== 'fallback') && (
            <p className="text-[10px] text-white/30 -mt-2 animate-fade-in">
              Powered by {analysis.ai_provider === 'gemini' ? 'Gemini 2.0 Flash' : analysis.ai_provider === 'groq' ? 'Llama 3.3 70B' : analysis.ai_provider === 'groq_8b' ? 'Llama 3.1 8B' : analysis.ai_provider}
            </p>
          )}
          {analysis?.ai_provider === 'fallback' && (
            <p className="text-[10px] text-amber-400/60 -mt-2 animate-fade-in">Heuristic mode — AI quota reached, manual review recommended</p>
          )}

          {/* ── RISK SUMMARY CARD ──────────── */}
          <div className={`card p-5 sm:p-6 md:p-8 animate-slide-up border-l-4 ${rc.border}`}>
            <div className="flex flex-col lg:grid lg:grid-cols-2 gap-6 lg:gap-10">
              {/* Left: Score + Recommendation */}
              <div className="space-y-4">
                <div className={`text-2xl sm:text-3xl md:text-4xl font-bold tracking-tight ${rc.text}`}>{rl.word}</div>

                <div>
                  <span className="text-sm text-white/40">Confidence: <strong className="text-white">{analysis?.confidence ?? '—'}%</strong></span>
                  <div className="flex items-baseline gap-2 mt-1">
                    <span className={`text-4xl sm:text-5xl md:text-6xl font-black tracking-tight ${rc.text}`}>{Math.round(score)}</span>
                    <span className="text-xl sm:text-2xl text-white/20 font-bold">/100</span>
                  </div>
                  {/* Progress bar */}
                  <div className="h-2 bg-white/10 rounded-full mt-3 overflow-hidden">
                    <div className={`h-full rounded-full transition-all duration-1000 ${rc.bg}`} style={{ width: `${Math.min(score, 100)}%` }} />
                  </div>
                </div>

                {/* Recommendation banner */}
                <div className={`border rounded-xl p-3 sm:p-4 ${rc.border} ${rc.bgSoft}`}>
                  <p className={`text-sm font-bold ${rc.text} mb-1`}>{rl.action} — {rl.word}</p>
                  <p className="text-xs text-white/50 break-words">{analysis?.executive_summary || rl.sub}</p>
                </div>
              </div>

              {/* Right: 5C Strip */}
              <div className="space-y-4">
                <div className="flex items-center gap-2">
                  <Shield className="w-4 h-4 text-accent-400 shrink-0" />
                  <h3 className="text-sm font-bold text-white uppercase tracking-wider">5C Enforceability</h3>
                </div>
                {analysis?.five_c ? (
                  <FiveCStrip fiveC={analysis.five_c} />
                ) : (
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                    {['Capacity','Consent','Consideration','Clarity','Compliance'].map(c => (
                      <div key={c} className="flex items-center gap-2 px-3 py-2 rounded-xl bg-white/[0.03] border border-white/5">
                        <div className="w-2 h-2 rounded-full bg-white/20 shrink-0" />
                        <span className="text-xs text-white/40 truncate">{c}</span>
                      </div>
                    ))}
                  </div>
                )}

                {/* Quick counts */}
                <div className="grid grid-cols-3 gap-2 mt-3">
                  <div className="bg-red-500/5 border border-red-500/10 rounded-xl p-3 text-center">
                    <p className="text-lg font-bold text-red-400">{breakdown.High}</p>
                    <p className="text-[10px] text-red-400/60 uppercase">High</p>
                  </div>
                  <div className="bg-amber-500/5 border border-amber-500/10 rounded-xl p-3 text-center">
                    <p className="text-lg font-bold text-amber-400">{breakdown.Medium}</p>
                    <p className="text-[10px] text-amber-400/60 uppercase">Medium</p>
                  </div>
                  <div className="bg-emerald-500/5 border border-emerald-500/10 rounded-xl p-3 text-center">
                    <p className="text-lg font-bold text-emerald-400">{breakdown.Low}</p>
                    <p className="text-[10px] text-emerald-400/60 uppercase">Low</p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* ── RED FLAG BANNER ────────────── */}
          <RedFlagBanner redFlags={analysis?.red_flags} />

          {/* ── EXECUTIVE SUMMARY ──────────── */}
          {analysis?.executive_summary && (
            <div className="card p-5 animate-slide-up">
              <h3 className="text-sm font-bold text-white mb-2 flex items-center gap-2">
                <FileWarning className="w-4 h-4 text-accent-400" /> Executive Summary
              </h3>
              <p className="text-sm text-white/50 leading-relaxed">{analysis.executive_summary}</p>
            </div>
          )}

          {/* ── TOP RISK FINDINGS ──────────── */}
          <FindingsList findings={analysis?.findings} />

          {/* ── NEGOTIATION PLAYBOOK ───────── */}
          <NegotiationPanel opportunities={analysis?.negotiation_opportunities} addToast={addToast} />

          {/* ── MISSING CLAUSES ────────────── */}
          <MissingClauses missingClauses={analysis?.missing_clauses} />

          {/* ── DETAILED CLAUSE ANALYSIS ───── */}
          <section className="space-y-4 animate-slide-up">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <FileText className="w-5 h-5 text-accent-400" />
                Detailed Clause Analysis
                <span className="text-sm font-normal text-white/30">({clauses.length})</span>
              </h3>
              <button onClick={() => document.getElementById('qa-chat')?.scrollIntoView({ behavior: 'smooth' })} className="text-sm text-accent-400 hover:text-accent-300 font-medium flex items-center gap-1">
                Ask Questions <ArrowDown className="w-3.5 h-3.5" />
              </button>
            </div>
            <div className="space-y-3">{clauses.map((clause) => (<ClauseAccordion key={clause.id} clause={clause} />))}</div>
          </section>

          {/* ── Q&A ────────────────────────── */}
          <section id="qa-chat" className="animate-slide-up">
            <QAChat contractText={contractText} askQuestion={askQuestion} />
          </section>

          {/* ── Actions ────────────────────── */}
          <div className="flex flex-col sm:flex-row gap-3 pt-4 pb-2 justify-center animate-slide-up">
            <button onClick={handleDownload} disabled={downloading} className="btn-primary !py-3.5 !px-8 inline-flex items-center justify-center gap-2">
              {downloading ? <Loader className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
              {downloading ? 'Generating PDF...' : 'Download PDF Report'}
            </button>
            <button onClick={handleReset} className="btn-secondary !py-3.5 !px-8 inline-flex items-center justify-center gap-2">
              <RefreshCw className="w-4 h-4" /> Analyze Another Contract
            </button>
          </div>

        </main>
        <Footer />
        <ToastContainer toasts={toasts} removeToast={removeToast} />
      </div>
    </ErrorBoundary>
  );
}
