import { Shield, Scale, FileCheck } from 'lucide-react';

const OUTCOMES = [
  {
    icon: Shield,
    title: 'Detect',
    desc: 'Risky clauses & missing protections flagged across 5C enforceability, payment, liability, and compliance.',
  },
  {
    icon: Scale,
    title: 'Decode',
    desc: 'Plain-English explanations of what each clause means, why it matters, and fair alternatives.',
  },
  {
    icon: FileCheck,
    title: 'Decide',
    desc: 'Overall risk score, 5C enforceability grades, and a prioritized negotiation playbook.',
  },
];

export default function OutcomesStrip() {
  return (
    <section className="py-12 sm:py-16 px-4 sm:px-6 bg-[#0A0A0A] border-y border-white/5">
      <div className="max-w-4xl mx-auto">
        <div className="text-center mb-8">
          <h2 className="text-2xl sm:text-3xl font-bold text-white tracking-tight mb-2">
            Outcomes you can trust
          </h2>
          <p className="text-white/40 text-sm max-w-md mx-auto">
            Every analysis delivers three things you need before signing
          </p>
        </div>
        <div className="grid sm:grid-cols-3 gap-4">
          {OUTCOMES.map(({ icon: Icon, title, desc }, i) => (
            <div key={i} className="card p-5 text-center">
              <div className="w-10 h-10 rounded-lg bg-accent-500/10 border border-accent-500/20 flex items-center justify-center mx-auto mb-3">
                <Icon className="w-5 h-5 text-accent-400" />
              </div>
              <h3 className="font-semibold text-white mb-1.5">{title}</h3>
              <p className="text-xs text-white/40 leading-relaxed">{desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
