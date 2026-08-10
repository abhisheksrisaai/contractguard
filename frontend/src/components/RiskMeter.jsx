import { useEffect, useRef } from 'react';

function getColor(score) {
  if (score >= 75) return { ring: '#EF4444', bg: 'rgba(239,68,68,0.15)', text: '#FCA5A5' };
  if (score >= 45) return { ring: '#F59E0B', bg: 'rgba(245,158,11,0.15)', text: '#FCD34D' };
  return { ring: '#10B981', bg: 'rgba(16,185,129,0.15)', text: '#6EE7B7' };
}

function getLabel(score) {
  if (score >= 75) return 'High Risk';
  if (score >= 45) return 'Medium Risk';
  return 'Low Risk';
}

const SIZES = {
  sm:  { dim: 80, stroke: 6,  font: 20, label: 10 },
  md:  { dim: 120, stroke: 8, font: 32, label: 12 },
  lg:  { dim: 160, stroke: 10, font: 42, label: 14 },
};

export default function RiskMeter({ score = 0, size = 'lg' }) {
  const circleRef = useRef(null);
  const s = SIZES[size] || SIZES.lg;
  const radius = (s.dim - s.stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (Math.min(score, 100) / 100) * circumference;
  const colors = getColor(score);

  useEffect(() => { if (circleRef.current) circleRef.current.style.transition = 'stroke-dashoffset 1s ease-out'; }, [score]);

  return (
    <div className="flex flex-col items-center gap-2 animate-scale-in">
      <svg width={s.dim} height={s.dim} className="transform -rotate-90">
        <circle cx={s.dim / 2} cy={s.dim / 2} r={radius} fill="none" stroke={colors.bg} strokeWidth={s.stroke} />
        <circle ref={circleRef} cx={s.dim / 2} cy={s.dim / 2} r={radius} fill="none" stroke={colors.ring} strokeWidth={s.stroke} strokeLinecap="round"
          strokeDasharray={circumference} strokeDashoffset={circumference}
          style={{ strokeDashoffset: offset }} className="transition-all duration-1000 ease-out" />
      </svg>
      <div className="absolute flex flex-col items-center justify-center" style={{ width: s.dim, height: s.dim, marginTop: `-${s.dim}px`, position: 'relative' }}>
        <span className="font-extrabold tracking-tight" style={{ fontSize: s.font, color: colors.ring, lineHeight: 1 }}>{Math.round(score)}</span>
        <span className="text-white/30 mt-0.5" style={{ fontSize: s.label, fontWeight: 500 }}>/ 100</span>
      </div>
      <span className="font-semibold tracking-wide uppercase mt-1" style={{ fontSize: s.label, color: colors.ring }}>{getLabel(score)}</span>
    </div>
  );
}
