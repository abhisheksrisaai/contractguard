import { useEffect, useRef } from 'react';

/**
 * RiskMeter — Animated circular gauge showing overall contract risk score.
 *
 * @param {Object} props
 * @param {number} props.score — 0-100 risk score
 * @param {string} [props.size] — 'sm' | 'md' | 'lg' (default: 'lg')
 */
function getColor(score) {
  if (score >= 70) return { ring: '#EF4444', bg: '#FEE2E2', text: '#991B1B' };
  if (score >= 40) return { ring: '#F59E0B', bg: '#FEF3C7', text: '#92400E' };
  return { ring: '#10B981', bg: '#D1FAE5', text: '#065F46' };
}

function getLabel(score) {
  if (score >= 70) return 'High Risk';
  if (score >= 40) return 'Medium Risk';
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

  useEffect(() => {
    // Animate on mount
    if (circleRef.current) {
      circleRef.current.style.transition = 'stroke-dashoffset 1s ease-out';
    }
  }, [score]);

  return (
    <div className="flex flex-col items-center gap-2 animate-scale-in">
      <svg width={s.dim} height={s.dim} className="transform -rotate-90">
        {/* Background circle */}
        <circle
          cx={s.dim / 2}
          cy={s.dim / 2}
          r={radius}
          fill="none"
          stroke={colors.bg}
          strokeWidth={s.stroke}
        />
        {/* Progress circle */}
        <circle
          ref={circleRef}
          cx={s.dim / 2}
          cy={s.dim / 2}
          r={radius}
          fill="none"
          stroke={colors.ring}
          strokeWidth={s.stroke}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={circumference}
          style={{ strokeDashoffset: offset }}
          className="transition-all duration-1000 ease-out"
        />
      </svg>

      {/* Center text */}
      <div className="absolute flex flex-col items-center justify-center" style={{
        width: s.dim, height: s.dim, marginTop: `-${s.dim}px`, position: 'relative',
      }}>
        <span
          className="font-extrabold tracking-tight"
          style={{ fontSize: s.font, color: colors.ring, lineHeight: 1 }}
        >
          {Math.round(score)}
        </span>
        <span
          className="text-slate-400 mt-0.5"
          style={{ fontSize: s.label, fontWeight: 500 }}
        >
          / 100
        </span>
      </div>

      <span
        className="font-semibold tracking-wide uppercase mt-1"
        style={{ fontSize: s.label, color: colors.ring }}
      >
        {getLabel(score)}
      </span>
    </div>
  );
}
