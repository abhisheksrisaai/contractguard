import { useState } from 'react';
import { Shield, Github, BookOpen, ArrowRight, Menu, X, MessageCircle } from 'lucide-react';

export default function Navbar({ compact = false, onReset, showReset = false }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const closeMenu = () => setMenuOpen(false);

  return (
    <header className={`sticky top-0 z-50 bg-black/80 backdrop-blur-md border-b border-white/10 ${compact ? 'py-2.5' : 'py-3 sm:py-4'}`}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 flex items-center justify-between">
        <a href="/" className="flex items-center gap-2.5 group shrink-0">
          <div className="w-8 h-8 rounded-lg bg-accent-500 flex items-center justify-center">
            <Shield className="w-4 h-4 text-white" />
          </div>
          <div>
            <h1 className={`font-bold tracking-tight text-white ${compact ? 'text-sm' : 'text-base sm:text-lg'}`}>ContractGuard</h1>
            {!compact && <p className="hidden xs:block text-[10px] text-white/40 tracking-wide uppercase">AI Contract Risk Analysis</p>}
          </div>
        </a>

        <div className="hidden md:flex items-center gap-4">
          <a href="#how-it-works" className="text-sm text-white/50 hover:text-white transition">How It Works</a>
          <a href="#faq" className="text-sm text-white/50 hover:text-white transition">FAQ</a>
          <a href="https://github.com/abhisheksrisaai/contractguard" target="_blank" rel="noopener noreferrer" className="text-sm text-white/50 hover:text-white transition flex items-center gap-1"><Github className="w-3.5 h-3.5" /> GitHub</a>
          {showReset && onReset && (
            <button onClick={onReset} className="text-xs text-white/60 hover:text-white border border-white/15 hover:border-white/30 rounded-lg px-3 py-1.5 transition">+ New</button>
          )}
          <a href="#upload" className="btn-primary !py-2 !px-4 !text-sm inline-flex items-center gap-1.5">
            Upload <ArrowRight className="w-3.5 h-3.5" />
          </a>
        </div>

        <div className="flex md:hidden items-center gap-2">
          {showReset && onReset && <button onClick={onReset} className="text-xs text-white/60 border border-white/15 rounded-lg px-2.5 py-1.5">+ New</button>}
          <button onClick={() => setMenuOpen(!menuOpen)} className="p-2 text-white/50 hover:text-white transition" aria-label="Menu">
            {menuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {menuOpen && (
        <div className="md:hidden border-t border-white/10 bg-black/95 animate-slide-up">
          <div className="px-4 py-4 space-y-3">
            <a href="#how-it-works" onClick={closeMenu} className="flex items-center gap-2 text-sm text-white/60 hover:text-white py-2"><BookOpen className="w-4 h-4" /> How It Works</a>
            <a href="#faq" onClick={closeMenu} className="flex items-center gap-2 text-sm text-white/60 hover:text-white py-2"><MessageCircle className="w-4 h-4" /> FAQ</a>
            <a href="https://github.com/abhisheksrisaai/contractguard" target="_blank" rel="noopener noreferrer" onClick={closeMenu} className="flex items-center gap-2 text-sm text-white/60 hover:text-white py-2"><Github className="w-4 h-4" /> GitHub</a>
            <a href="#upload" onClick={closeMenu} className="btn-primary !py-2.5 !text-sm flex items-center justify-center gap-2 w-full">Upload Contract <ArrowRight className="w-4 h-4" /></a>
          </div>
        </div>
      )}
    </header>
  );
}
