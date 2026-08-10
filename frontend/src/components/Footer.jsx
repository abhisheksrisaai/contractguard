import { Github, Shield } from 'lucide-react';

export default function Footer() {
  return (
    <footer className="border-t border-white/5 no-print py-8 px-4 sm:px-6">
      <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4 text-center sm:text-left">
        <div className="flex items-center gap-3">
          <Shield className="w-5 h-5 text-accent-400" />
          <p className="text-xs text-white/40 leading-relaxed max-w-md">
            <strong className="text-white/60">Disclaimer:</strong>{' '}
            ContractGuard provides informational analysis only. It does not constitute legal advice.
            Always consult a qualified attorney before making legal decisions.
          </p>
        </div>
        <div className="flex items-center gap-6">
          <a href="https://github.com/abhisheksrisaai/contractguard" target="_blank" rel="noopener noreferrer" className="text-xs text-white/40 hover:text-white/70 transition flex items-center gap-1.5">
            <Github className="w-3.5 h-3.5" /> GitHub
          </a>
          <span className="text-xs text-white/25">&copy; {new Date().getFullYear()} ContractGuard</span>
        </div>
      </div>
    </footer>
  );
}
