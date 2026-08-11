import { Sparkles, Zap, Cpu } from 'lucide-react';

const MODELS = [
  { id: 'auto', label: 'Auto', desc: 'Best available — recommended', icon: Sparkles },
  { id: 'gemini', label: 'Gemini 2.0 Flash', desc: 'Fast, great with long contracts', icon: Zap },
  { id: 'llama-3.3-70b-versatile', label: 'Llama 3.3 70B', desc: 'Deepest reasoning', icon: Cpu },
];

export default function ModelSelector({ selected, onChange }) {
  return (
    <div className="space-y-2.5">
      <p className="text-xs font-semibold text-white/40 uppercase tracking-wider text-center">AI Model</p>
      <div className="flex gap-2 justify-center">
        {MODELS.map(({ id, label, desc, icon: Icon }) => (
          <button
            key={id}
            onClick={() => onChange(id)}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-full border text-sm transition-all duration-200 ${
              selected === id
                ? 'border-accent-400 bg-accent-500/10 text-white'
                : 'border-white/10 text-white/50 hover:border-white/20 hover:text-white/70'
            }`}
          >
            <Icon className="w-3.5 h-3.5" />
            <span className="font-medium">{label}</span>
            <span className="text-[10px] text-white/30 hidden sm:inline">{desc}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
