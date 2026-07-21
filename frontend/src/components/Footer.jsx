import { Github, ExternalLink, Shield } from 'lucide-react';

/**
 * Footer — Professional footer with disclaimer and links.
 */
export default function Footer() {
  return (
    <footer className="bg-navy-950 border-t border-white/5 no-print">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
          {/* ── Logo + Disclaimer ────────── */}
          <div className="flex items-center gap-3">
            <Shield className="w-5 h-5 text-accent-500" />
            <p className="text-xs text-slate-400 leading-relaxed max-w-md">
              <strong className="text-slate-300">Disclaimer:</strong>{' '}
              ContractGuard provides informational analysis only. It does not constitute legal advice.
              Always consult a qualified attorney before making legal decisions.
            </p>
          </div>

          {/* ── Links ────────────────────── */}
          <div className="flex items-center gap-6">
            <a
              href="https://github.com/abhisheksrisaai/contractguard"
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-slate-500 hover:text-slate-300 transition flex items-center gap-1.5"
            >
              <Github className="w-3.5 h-3.5" />
              GitHub
            </a>
            <a
              href="https://contractguard-api.onrender.com/docs"
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-slate-500 hover:text-slate-300 transition flex items-center gap-1.5"
            >
              <ExternalLink className="w-3.5 h-3.5" />
              API Docs
            </a>
            <span className="text-xs text-slate-600">
              © {new Date().getFullYear()} ContractGuard
            </span>
          </div>
        </div>
      </div>
    </footer>
  );
}
