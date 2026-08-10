import { useState } from 'react';
import {
  Briefcase, Building2, HardHat, Handshake, Sparkles,
} from 'lucide-react';

const TYPES = [
  {
    id: 'employment_contract',
    icon: Briefcase,
    label: 'Employment',
    desc: 'Salary, notice, termination & gratuity risks',
    checks: ['Notice Period', 'Termination Grounds', 'Salary & Deductions', 'Gratuity / PF / ESI', 'Confidentiality', 'Non-Compete', 'Indemnity', 'Dispute Resolution'],
  },
  {
    id: 'supplier_contract',
    icon: Building2,
    label: 'Supplier',
    desc: 'Payment, delivery, warranty & liability exposure',
    checks: ['Payment Terms', 'Delivery & Incoterms', 'Quality & Inspection', 'Warranty & DLP', 'Liability & Indemnity', 'Force Majeure', 'Insurance', 'Termination'],
  },
  {
    id: 'works_contract',
    icon: HardHat,
    label: 'Works',
    desc: 'Milestones, EOT, variations & defect liability',
    checks: ['Scope & BOQ', 'Payment Milestones', 'Variations & EOT', 'Quality & ITP', 'Defect Liability', 'Performance Security', 'HSE Compliance', 'Dispute Resolution'],
  },
  {
    id: 'partner_agreement',
    icon: Handshake,
    label: 'Partner',
    desc: 'Revenue share, exclusivity & exit risks',
    checks: ['Revenue Share', 'Exclusivity', 'Targets & Performance', 'IP & Branding', 'Non-Solicit', 'Liability Caps', 'Termination & Exit', 'Dispute Resolution'],
  },
];

export default function ContractTypeSelector({ selected, onChange }) {
  const [autoDetect, setAutoDetect] = useState(selected === null);

  const handleAutoDetect = () => {
    setAutoDetect(true);
    onChange(null);
  };

  const handleSelect = (typeId) => {
    setAutoDetect(false);
    onChange(typeId);
  };

  const active = autoDetect ? null : selected;

  return (
    <div className="space-y-4">
      <div className="text-center">
        <h2 className="text-lg font-semibold text-white mb-1">What kind of contract is it?</h2>
        <p className="text-sm text-white/40">We tailor the analysis to your contract type for deeper insights</p>
      </div>

      {/* Type cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-2.5">
        {TYPES.map(({ id, icon: Icon, label, desc }) => (
          <button
            key={id}
            onClick={() => handleSelect(id)}
            className={`p-3.5 rounded-xl border text-left transition-all duration-200 ${
              active === id
                ? 'border-accent-400 bg-accent-500/10 ring-1 ring-accent-400/30'
                : 'border-white/10 bg-white/[0.03] hover:border-white/20 hover:bg-white/[0.06]'
            }`}
          >
            <div className="flex flex-col items-center text-center gap-2">
              <Icon className={`w-5 h-5 ${active === id ? 'text-accent-400' : 'text-white/40'}`} />
              <span className={`text-sm font-semibold ${active === id ? 'text-white' : 'text-white/80'}`}>{label}</span>
              <span className="text-[10px] leading-tight text-white/40">{desc}</span>
            </div>
          </button>
        ))}
        {/* Auto-Detect */}
        <button
          onClick={handleAutoDetect}
          className={`p-3.5 rounded-xl border text-left transition-all duration-200 ${
            autoDetect
              ? 'border-accent-400 bg-accent-500/10 ring-1 ring-accent-400/30'
              : 'border-white/10 bg-white/[0.03] hover:border-white/20 hover:bg-white/[0.06]'
          }`}
        >
          <div className="flex flex-col items-center text-center gap-2">
            <Sparkles className={`w-5 h-5 ${autoDetect ? 'text-accent-400' : 'text-white/40'}`} />
            <span className={`text-sm font-semibold ${autoDetect ? 'text-white' : 'text-white/80'}`}>Auto-Detect</span>
            <span className="text-[10px] leading-tight text-white/40">Recommended</span>
          </div>
        </button>
      </div>

      {/* Selected type detail */}
      {active && (
        <div className="card p-4 animate-scale-in">
          <div className="flex items-center gap-2 mb-3">
            {(() => {
              const t = TYPES.find(t => t.id === active);
              if (!t) return null;
              const Icon = t.icon;
              return <Icon className="w-4 h-4 text-accent-400" />;
            })()}
            <span className="text-sm font-semibold text-white">
              {TYPES.find(t => t.id === active)?.label} contract analysis covers:
            </span>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {(TYPES.find(t => t.id === active)?.checks || []).map((c) => (
              <div key={c} className="flex items-center gap-1.5 text-xs text-white/50">
                <div className="w-1 h-1 rounded-full bg-accent-400 shrink-0" />
                {c}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
