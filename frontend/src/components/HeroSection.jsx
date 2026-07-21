import { Shield, Zap, Lock, Bot } from 'lucide-react';

/**
 * HeroSection — Landing page hero with headline, trust badges, and upload CTA.
 *
 * @param {Object} props
 * @param {Function} props.onUploadClick — Scrolls to / opens upload zone
 */
export default function HeroSection({ onUploadClick }) {
  return (
    <section className="relative overflow-hidden bg-gradient-to-b from-navy-950 via-navy-900 to-navy-950">
      {/* Background pattern */}
      <div className="absolute inset-0 opacity-[0.03] pointer-events-none"
        style={{
          backgroundImage: `radial-gradient(circle at 25px 25px, white 1px, transparent 0)`,
          backgroundSize: '50px 50px',
        }}
      />

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 pt-16 pb-24 md:pt-24 md:pb-32">
        <div className="grid md:grid-cols-2 gap-12 items-center">

          {/* ── Left: Text Content ──────── */}
          <div className="space-y-6 md:space-y-8 animate-slide-up" style={{ animationDelay: '0.1s' }}>
            <div className="inline-flex items-center gap-2 bg-accent-500/10 border border-accent-500/20 rounded-full px-4 py-1.5">
              <Bot className="w-3.5 h-3.5 text-accent-400" />
              <span className="text-xs font-medium text-accent-400 tracking-wide">
                AI-Powered Contract Analysis
              </span>
            </div>

            <h1 className="text-4xl md:text-5xl lg:text-6xl font-extrabold text-white leading-[1.1] tracking-tight">
              Protect Yourself{' '}
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-accent-400 to-accent-600">
                Before You Sign
              </span>
            </h1>

            <p className="text-lg md:text-xl text-slate-400 max-w-lg leading-relaxed">
              Upload any employment or service contract. Our AI analyzes every clause for risks,
              compares against fair standards, and gives you a detailed report — all in under 60 seconds.
            </p>

            <div className="flex flex-col sm:flex-row gap-3">
              <button
                onClick={onUploadClick}
                className="btn-primary !py-3.5 !px-8 !text-base !rounded-2xl inline-flex items-center justify-center gap-2"
              >
                <Shield className="w-5 h-5" />
                Upload Your Contract
              </button>
              <a
                href="#how-it-works"
                className="btn-secondary !py-3.5 !px-8 !rounded-2xl inline-flex items-center justify-center gap-2 !border-slate-600 !text-slate-300 hover:!text-white hover:!border-slate-500"
              >
                See How It Works
              </a>
            </div>

            {/* ── Trust Badges ──────────── */}
            <div className="flex flex-wrap gap-4 pt-4">
              {[
                { icon: Lock, label: 'Secure & Private' },
                { icon: Zap, label: 'Results in 60s' },
                { icon: Bot, label: 'AI-Powered' },
                { icon: Shield, label: '100% Free' },
              ].map(({ icon: Icon, label }) => (
                <div key={label} className="flex items-center gap-2 text-slate-400">
                  <Icon className="w-4 h-4 text-accent-500" />
                  <span className="text-xs font-medium">{label}</span>
                </div>
              ))}
            </div>
          </div>

          {/* ── Right: Illustration Area ── */}
          <div className="hidden md:flex justify-center animate-slide-up" style={{ animationDelay: '0.3s' }}>
            <div className="relative w-80 h-80 lg:w-96 lg:h-96">
              {/* Decorative circles */}
              <div className="absolute inset-0 rounded-full bg-gradient-to-br from-accent-500/10 to-accent-700/5 animate-pulse-soft" />
              <div className="absolute inset-8 rounded-full border-2 border-dashed border-accent-500/20 animate-spin" style={{ animationDuration: '20s' }} />
              <div className="absolute inset-16 rounded-full bg-gradient-to-br from-accent-500/20 to-transparent" />

              {/* Center shield icon */}
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="w-24 h-24 rounded-2xl bg-navy-800 border border-accent-500/30 shadow-2xl shadow-accent-500/10 flex items-center justify-center">
                  <Shield className="w-12 h-12 text-accent-400" />
                </div>
              </div>

              {/* Floating document cards */}
              <div className="absolute -top-2 left-4 bg-navy-800 border border-white/5 rounded-xl p-3 shadow-xl animate-slide-up" style={{ animationDelay: '0.5s' }}>
                <div className="w-24 h-3 bg-slate-600 rounded mb-2" />
                <div className="w-20 h-2 bg-slate-700 rounded mb-1" />
                <div className="w-16 h-2 bg-slate-700 rounded" />
              </div>
              <div className="absolute -bottom-2 right-4 bg-accent-500 text-white text-xs font-bold rounded-full px-3 py-1 shadow-lg shadow-accent-500/30 animate-slide-up" style={{ animationDelay: '0.7s' }}>
                Risk Score: 85
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom gradient fade */}
      <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-[var(--color-bg)] to-transparent" />
    </section>
  );
}
