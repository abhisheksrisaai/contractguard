import { useState } from 'react';
import { Shield, Github, BookOpen, ArrowRight, Menu, X } from 'lucide-react';

/**
 * Navbar — Professional LegalTech header, fully responsive with mobile hamburger menu.
 *
 * @param {Object} props
 * @param {boolean} [props.compact] — Smaller variant for results page
 * @param {Function} [props.onReset] — Called when "New Analysis" clicked
 * @param {boolean} [props.showReset] — Show "New Analysis" button
 */
export default function Navbar({ compact = false, onReset, showReset = false }) {
  const [menuOpen, setMenuOpen] = useState(false);

  const closeMenu = () => setMenuOpen(false);

  return (
    <header className={`
      sticky top-0 z-50 bg-navy-950/95 backdrop-blur-md border-b border-white/5
      ${compact ? 'py-2.5 sm:py-3' : 'py-3 sm:py-4'}
    `}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 flex items-center justify-between">
        {/* ── Logo ───────────────────────── */}
        <a href="/" className="flex items-center gap-2.5 sm:gap-3 group shrink-0">
          <div className="w-8 h-8 sm:w-9 sm:h-9 rounded-lg bg-gradient-to-br from-accent-500 to-accent-700 flex items-center justify-center shadow-lg shadow-accent-500/20">
            <Shield className="w-4 h-4 sm:w-5 sm:h-5 text-white" />
          </div>
          <div>
            <h1 className={`font-bold tracking-tight text-white ${compact ? 'text-sm sm:text-base' : 'text-base sm:text-lg'}`}>
              ContractGuard
            </h1>
            {!compact && (
              <p className="hidden xs:block text-[10px] text-slate-400 tracking-wide uppercase">
                AI Contract Risk Analysis
              </p>
            )}
          </div>
        </a>

        {/* ── Desktop Nav Links ──────────── */}
        <div className="hidden md:flex items-center gap-3 lg:gap-5">
          <a href="#how-it-works" className="flex items-center gap-1.5 text-sm text-slate-400 hover:text-white transition">
            <BookOpen className="w-3.5 h-3.5" /> How It Works
          </a>
          <a href="https://github.com/abhisheksrisaai/contractguard" target="_blank" rel="noopener noreferrer"
            className="flex items-center gap-1.5 text-sm text-slate-400 hover:text-white transition">
            <Github className="w-3.5 h-3.5" /> GitHub
          </a>

          {showReset && onReset && (
            <button onClick={onReset}
              className="text-xs text-slate-300 hover:text-white border border-slate-600 hover:border-slate-400 rounded-lg px-3 py-1.5 transition">
              + New
            </button>
          )}

          <a href="#upload" className="btn-primary !py-2 !px-4 !text-sm inline-flex items-center gap-1.5">
            Upload <ArrowRight className="w-3.5 h-3.5" />
          </a>
        </div>

        {/* ── Mobile Right Side ──────────── */}
        <div className="flex md:hidden items-center gap-2">
          {showReset && onReset && (
            <button onClick={onReset}
              className="text-xs text-slate-300 border border-slate-600 rounded-lg px-2.5 py-1.5">
              + New
            </button>
          )}
          <button onClick={() => setMenuOpen(!menuOpen)}
            className="p-2 text-slate-400 hover:text-white transition rounded-lg hover:bg-white/5"
            aria-label={menuOpen ? 'Close menu' : 'Open menu'}>
            {menuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* ── Mobile Menu ──────────────────── */}
      {menuOpen && (
        <div className="md:hidden border-t border-white/5 bg-navy-900/95 backdrop-blur-md animate-slide-up">
          <div className="px-4 py-4 space-y-3">
            <a href="#how-it-works" onClick={closeMenu}
              className="flex items-center gap-2 text-sm text-slate-300 hover:text-white py-2 transition">
              <BookOpen className="w-4 h-4" /> How It Works
            </a>
            <a href="https://github.com/abhisheksrisaai/contractguard" target="_blank" rel="noopener noreferrer" onClick={closeMenu}
              className="flex items-center gap-2 text-sm text-slate-300 hover:text-white py-2 transition">
              <Github className="w-4 h-4" /> GitHub
            </a>
            <a href="#upload" onClick={closeMenu}
              className="btn-primary !py-2.5 !text-sm flex items-center justify-center gap-2 w-full">
              Upload Contract <ArrowRight className="w-4 h-4" />
            </a>
          </div>
        </div>
      )}
    </header>
  );
}
