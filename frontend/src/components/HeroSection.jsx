import { Shield, ArrowRight, Sparkles } from 'lucide-react';

export default function HeroSection({ onUploadClick, onHowItWorksClick }) {
  return (
    <section className="relative overflow-hidden bg-black pt-8 pb-12 sm:pt-12 sm:pb-16 md:pt-16 md:pb-24">
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[800px] h-[500px] bg-accent-500/5 rounded-full blur-[120px]" />
      </div>

      <div className="relative max-w-4xl mx-auto px-4 sm:px-6 text-center">
        {/* Pill badge */}
        <div className="inline-flex items-center gap-2 bg-accent-500/10 border border-accent-500/20 rounded-full px-4 py-1.5 mb-6 sm:mb-8 animate-slide-up">
          <Sparkles className="w-3.5 h-3.5 text-accent-400" />
          <span className="text-xs sm:text-sm font-medium text-accent-400">AI-Powered Contract Review</span>
        </div>

        <h1 className="text-4xl sm:text-5xl md:text-7xl font-bold text-white leading-[1.05] tracking-tight mb-5 sm:mb-6 animate-slide-up" style={{ animationDelay: '0.1s' }}>
          Never sign a risky<br className="hidden sm:block" /> contract again.
        </h1>

        <p className="text-base sm:text-lg text-white/40 max-w-2xl mx-auto mb-8 sm:mb-10 leading-relaxed animate-slide-up" style={{ animationDelay: '0.15s' }}>
          Upload any employment, supplier, works or partner agreement. AI reviews every clause, checks enforceability, benchmarks against fair standards and tells you exactly what to negotiate — in under 60 seconds.
        </p>

        <div className="flex flex-col sm:flex-row gap-3 justify-center mb-6 animate-slide-up" style={{ animationDelay: '0.2s' }}>
          <button onClick={onUploadClick} className="btn-primary !py-3.5 !px-8 !text-base inline-flex items-center justify-center gap-2">
            <Shield className="w-5 h-5" />
            Analyze My Contract
          </button>
          <button onClick={onHowItWorksClick} className="btn-secondary !py-3.5 !px-8 inline-flex items-center justify-center gap-2">
            See how it works
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>

        <p className="text-xs text-white/30 animate-slide-up" style={{ animationDelay: '0.25s' }}>
          Free &bull; No signup &bull; Your document is never stored
        </p>
      </div>
    </section>
  );
}
