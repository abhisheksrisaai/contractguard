import { Briefcase, Building2, HardHat, Handshake, FileText, ShoppingCart, Shield, HelpCircle } from 'lucide-react';

const TYPE_CONFIG = {
  employment_contract: { icon: Briefcase, label: 'Employment Contract' },
  supplier_contract: { icon: Building2, label: 'Supplier Contract' },
  works_contract: { icon: HardHat, label: 'Works Contract' },
  partner_agreement: { icon: Handshake, label: 'Partner Agreement' },
  service_agreement: { icon: FileText, label: 'Service Agreement' },
  nda: { icon: Shield, label: 'NDA' },
  purchase_order: { icon: ShoppingCart, label: 'Purchase Order' },
};

export default function ContractTypeBadge({ contractType, confidence }) {
  const cfg = TYPE_CONFIG[contractType] || { icon: HelpCircle, label: (contractType || 'Unknown').replace(/_/g, ' ') };
  const Icon = cfg.icon;
  const pct = Math.round((confidence || 0) * 100);

  if (!contractType) return null;

  return (
    <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/5 border border-white/10">
      <Icon className="w-3.5 h-3.5 text-accent-400" />
      <span className="text-sm font-medium text-white">{cfg.label}</span>
      {pct > 0 && <span className="text-[10px] text-white/30 bg-white/5 px-1.5 py-0.5 rounded-full">{pct}%</span>}
    </div>
  );
}
