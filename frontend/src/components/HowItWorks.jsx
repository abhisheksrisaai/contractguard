import { Upload, Bot, Download } from 'lucide-react';

const STEPS = [
  {
    num: '01',
    icon: Upload,
    title: 'Upload your PDF',
    desc: 'Drag and drop any employment, supplier, works, or partner agreement. We accept PDFs up to 10MB.',
  },
  {
    num: '02',
    icon: Bot,
    title: 'AI reviews every clause',
    desc: 'Extraction, contract-type classification, 5C enforceability validation, clause-level risk scoring, and fair-clause benchmarking against 50 legal templates.',
  },
  {
    num: '03',
    icon: Download,
    title: 'Get your negotiation playbook',
    desc: 'Risk score, detailed findings, missing protections, suggested alternatives, and a downloadable PDF report ready to share with your lawyer.',
  },
];

export default function HowItWorks() {
  return (
    <section id="how-it-works" className="py-16 sm:py-20 px-4 sm:px-6">
      <div className="max-w-5xl mx-auto">
        <div className="text-center mb-10 sm:mb-14">
          <h2 className="text-3xl sm:text-4xl font-bold text-white tracking-tight mb-3">
            How it works
          </h2>
          <p className="text-white/50 text-sm sm:text-base max-w-lg mx-auto">
            Three steps from risky contract to informed decision
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-5 sm:gap-6">
          {STEPS.map(({ num, icon: Icon, title, desc }, i) => (
            <div key={i} className="card p-6 text-center group hover:-translate-y-1 transition-transform duration-300">
              <div className="w-12 h-12 rounded-xl bg-accent-500/10 border border-accent-500/20 flex items-center justify-center mx-auto mb-4">
                <Icon className="w-6 h-6 text-accent-400" />
              </div>
              <div className="text-[10px] font-bold text-accent-400 tracking-widest mb-2">
                STEP {num}
              </div>
              <h3 className="font-semibold text-white mb-2">{title}</h3>
              <p className="text-sm text-white/40 leading-relaxed">{desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
