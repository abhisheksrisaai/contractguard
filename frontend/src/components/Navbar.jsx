import { Shield, Github, BookOpen, ArrowRight } from 'lucide-react';

/**
 * Navbar — Professional LegalTech header with logo, nav links, and GitHub CTA.
 *
 * @param {Object} props
 * @param {boolean} [props.compact] — Smaller variant for results page
 * @param {Function} [props.onReset] — Called when "New Analysis" clicked
 * @param {boolean} [props.showReset] — Show "New Analysis" button
 */
export default function Navbar({ compact = false, onReset, showReset = false }) {
  return (
    <header className={`
      sticky top-0 z-50 bg-navy-950/95 backdrop-blur-md border-b border-white/5
      ${compact ? 'py-3' : 'py-4'}
    `}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 flex items-center justify-between">
        {/* ── Logo ───────────────────────── */}
        <a href="/" className="flex items-center gap-3 group">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-accent-500 to-accent-700 flex items-center justify-center shadow-lg shadow-accent-500/20">
            <Shield className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className={`
              font-bold tracking-tight text-white
              ${compact ? 'text-base' : 'text-lg'}
            `}>
              ContractGuard
            </h1>
            {!compact && (
              <p className="text-[10px] text-slate-400 tracking-wide uppercase">
                AI Contract Risk Analysis
              </p>
            )}
          </div>
        </a>

        {/* ── Nav Links ──────────────────── */}
        <div className="flex items-center gap-3 sm:gap-5">
          <a
            href="#how-it-works"
            className="hidden sm:flex items-center gap-1.5 text-sm text-slate-400 hover:text-white transition"
          >
            <BookOpen className="w-3.5 h-3.5" />
            How It Works
          </a>
          <a
            href="https://github.com/abhisheksrisaai/contractguard"
            target="_blank"
            rel="noopener noreferrer"
            className="hidden sm:flex items-center gap-1.5 text-sm text-slate-400 hover:text-white transition"
          >
            <Github className="w-3.5 h-3.5" />
            GitHub
          </a>

          {showReset && onReset && (
            <button
              onClick={onReset}
              className="text-xs text-slate-300 hover:text-white border border-slate-600 hover:border-slate-400 rounded-lg px-3 py-1.5 transition"
            >
              + New Analysis
            </button>
          )}

          <a
            href="#upload"
            className="btn-primary !py-2 !px-4 !text-sm hidden sm:inline-flex items-center gap-1.5"
          >
            Upload Contract
            <ArrowRight className="w-3.5 h-3.5" />
          </a>
        </div>
      </div>
    </header>
  );
}
