import { useState } from 'react';
import {
  Shield, Github, BookOpen, ArrowRight, Menu, X, MessageCircle, Sun, Moon,
} from 'lucide-react';
import { useTheme } from '../hooks/useTheme';

export default function Navbar({
  compact = false,
  onReset,
  showReset = false,
  onUpload,
  onHome,
}) {
  const [menuOpen, setMenuOpen] = useState(false);
  const { theme, toggleTheme } = useTheme();
  const closeMenu = () => setMenuOpen(false);

  const handleHome = (event) => {
    if (!onHome) return;
    event.preventDefault();
    closeMenu();
    onHome();
  };

  const handleUpload = () => {
    closeMenu();
    if (onUpload) {
      onUpload();
      return;
    }
    document.getElementById('upload')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  };

  const handleSection = (event, id) => {
    event.preventDefault();
    closeMenu();
    const target = document.getElementById(id);
    if (target) {
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      return;
    }
    if (onHome) {
      onHome();
      window.setTimeout(() => {
        document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 120);
    }
  };

  const themeLabel = theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme';

  return (
    <header className={`sticky top-0 z-50 border-b border-white/10 bg-black/80 backdrop-blur-md transition-colors ${compact ? 'py-2.5' : 'py-3 sm:py-4'}`}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 flex items-center justify-between">
        <a href="/" onClick={handleHome} className="flex items-center gap-2.5 group shrink-0">
          <div className="w-8 h-8 rounded-lg bg-accent-500 flex items-center justify-center shadow-lg shadow-accent-500/20">
            <Shield className="w-4 h-4 text-white" />
          </div>
          <div>
            <h1 className={`font-bold tracking-tight text-white ${compact ? 'text-sm' : 'text-base sm:text-lg'}`}>ContractGuard</h1>
            {!compact && <p className="hidden xs:block text-[10px] text-white/40 tracking-wide uppercase">AI Contract Risk Analysis</p>}
          </div>
        </a>

        <div className="hidden md:flex items-center gap-4">
          <a href="#how-it-works" onClick={(event) => handleSection(event, 'how-it-works')} className="text-sm text-white/50 hover:text-white transition">How It Works</a>
          <a href="#faq" onClick={(event) => handleSection(event, 'faq')} className="text-sm text-white/50 hover:text-white transition">FAQ</a>
          <a href="https://github.com/abhisheksrisaai/contractguard" target="_blank" rel="noopener noreferrer" className="text-sm text-white/50 hover:text-white transition flex items-center gap-1"><Github className="w-3.5 h-3.5" /> GitHub</a>
          <button
            type="button"
            onClick={toggleTheme}
            aria-label={themeLabel}
            title={themeLabel}
            className="flex h-9 w-9 items-center justify-center rounded-full border border-white/10 bg-white/5 text-white/50 transition hover:border-white/20 hover:text-white"
          >
            {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </button>
          {showReset && onReset && (
            <button onClick={onReset} className="text-xs text-white/60 hover:text-white border border-white/15 hover:border-white/30 rounded-lg px-3 py-1.5 transition">+ New</button>
          )}
          <button onClick={handleUpload} className="btn-primary !py-2 !px-4 !text-sm inline-flex items-center gap-1.5">
            Upload <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

        <div className="flex md:hidden items-center gap-2">
          <button
            type="button"
            onClick={toggleTheme}
            aria-label={themeLabel}
            className="flex h-9 w-9 items-center justify-center rounded-full border border-white/10 bg-white/5 text-white/50 transition hover:text-white"
          >
            {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </button>
          {showReset && onReset && <button onClick={onReset} className="text-xs text-white/60 border border-white/15 rounded-lg px-2.5 py-1.5">+ New</button>}
          <button onClick={() => setMenuOpen(!menuOpen)} className="p-2 text-white/50 hover:text-white transition" aria-label="Menu" aria-expanded={menuOpen}>
            {menuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {menuOpen && (
        <div className="md:hidden border-t border-white/10 bg-black/95 animate-slide-up">
          <div className="px-4 py-4 space-y-2">
            <a href="#how-it-works" onClick={(event) => handleSection(event, 'how-it-works')} className="flex items-center gap-2 text-sm text-white/60 hover:text-white py-2 px-3"><BookOpen className="w-4 h-4" /> How It Works</a>
            <a href="#faq" onClick={(event) => handleSection(event, 'faq')} className="flex items-center gap-2 text-sm text-white/60 hover:text-white py-2 px-3"><MessageCircle className="w-4 h-4" /> FAQ</a>
            <a href="https://github.com/abhisheksrisaai/contractguard" target="_blank" rel="noopener noreferrer" onClick={closeMenu} className="flex items-center gap-2 text-sm text-white/60 hover:text-white py-2 px-3"><Github className="w-4 h-4" /> GitHub</a>
            <button onClick={handleUpload} className="btn-primary !py-2.5 !text-sm flex items-center justify-center gap-2 w-full">Upload Contract <ArrowRight className="w-4 h-4" /></button>
          </div>
        </div>
      )}
    </header>
  );
}
