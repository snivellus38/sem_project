/**
 * QualityCard.jsx — Composite tea quality score card.
 *
 * Displays a single quality score (0–100) computed from moisture,
 * enzyme denaturation, and pyrazine generation, plus a colour swatch
 * showing the current tea colour.
 */

import { qualityScore } from '../../utils/colorConvert';

function gradeLabel(score) {
  if (score >= 90) return { label: 'Excellent', color: '#4ade80' };
  if (score >= 70) return { label: 'Good', color: '#38bdf8' };
  if (score >= 50) return { label: 'Fair', color: '#fbbf24' };
  return { label: 'Poor', color: '#f87171' };
}

export default function QualityCard({ state }) {
  const score = qualityScore(state);
  const { label, color } = gradeLabel(score);
  const teaColor = state?.color_hex ?? '#7e7f51';

  return (
    <div className="glass-sm p-4 flex flex-col items-center gap-2">
      <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
        Tea Quality
      </h3>

      {/* Score ring */}
      <div className="relative w-20 h-20">
        <svg width="80" height="80" viewBox="0 0 80 80">
          <circle
            cx="40" cy="40" r="34"
            fill="none"
            stroke="rgba(255,255,255,0.08)"
            strokeWidth="6"
          />
          <circle
            cx="40" cy="40" r="34"
            fill="none"
            stroke={color}
            strokeWidth="6"
            strokeDasharray={`${2 * Math.PI * 34}`}
            strokeDashoffset={`${2 * Math.PI * 34 * (1 - score / 100)}`}
            strokeLinecap="round"
            transform="rotate(-90, 40, 40)"
            style={{ transition: 'stroke-dashoffset 0.5s ease' }}
          />
          <text x="40" y="38" textAnchor="middle" fill="#e2e8f0" fontSize="18" fontWeight="bold">
            {score}
          </text>
          <text x="40" y="52" textAnchor="middle" fill={color} fontSize="9">
            {label}
          </text>
        </svg>
      </div>

      {/* Colour swatch */}
      <div className="flex items-center gap-2">
        <div
          className="w-6 h-6 rounded-full border border-white/20"
          style={{ background: teaColor, transition: 'background 0.3s' }}
        />
        <span className="text-xs text-slate-400">
          {state?.l_star != null
            ? `L*${state.l_star.toFixed(0)} a*${state.a_star.toFixed(0)} b*${state.b_star.toFixed(0)}`
            : 'Waiting…'}
        </span>
      </div>

      {/* Status flags */}
      <div className="flex gap-2 text-[10px]">
        {state?.stewing && (
          <span className="bg-red-500/20 text-red-400 px-2 py-0.5 rounded-full animate-pulse">
            ⚠ Stewing
          </span>
        )}
        {state?.stewing_penalty && (
          <span className="bg-red-500/30 text-red-300 px-2 py-0.5 rounded-full">
            Stew Penalty
          </span>
        )}
      </div>
    </div>
  );
}
