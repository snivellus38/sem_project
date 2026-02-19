/**
 * Gauge.jsx — Circular / arc gauge for a single metric.
 *
 * Uses SVG for the arc so it works everywhere and is lightweight.
 */

export default function Gauge({ label, value, unit, min = 0, max = 100, color = 'var(--accent)', icon }) {
  const pct = Math.max(0, Math.min(1, (value - min) / (max - min)));
  const radius = 40;
  const circumference = 2 * Math.PI * radius * 0.75; // 270° arc
  const dashOffset = circumference * (1 - pct);

  return (
    <div className="glass-sm p-3 flex flex-col items-center gap-1 min-w-[120px]">
      <svg width="100" height="80" viewBox="0 0 100 80">
        {/* Background arc */}
        <circle
          cx="50" cy="55" r={radius}
          fill="none"
          stroke="rgba(255,255,255,0.08)"
          strokeWidth="7"
          strokeDasharray={`${circumference} ${2 * Math.PI * radius}`}
          strokeDashoffset="0"
          strokeLinecap="round"
          transform="rotate(135, 50, 55)"
        />
        {/* Value arc */}
        <circle
          cx="50" cy="55" r={radius}
          fill="none"
          stroke={color}
          strokeWidth="7"
          strokeDasharray={`${circumference} ${2 * Math.PI * radius}`}
          strokeDashoffset={dashOffset}
          strokeLinecap="round"
          transform="rotate(135, 50, 55)"
          style={{ transition: 'stroke-dashoffset 0.3s ease' }}
        />
        {/* Value text */}
        <text x="50" y="52" textAnchor="middle" fill="#e2e8f0" fontSize="16" fontWeight="bold">
          {typeof value === 'number' ? value.toFixed(1) : value}
        </text>
        <text x="50" y="68" textAnchor="middle" fill="#94a3b8" fontSize="10">
          {unit}
        </text>
      </svg>
      <span className="text-xs text-slate-400 flex items-center gap-1">
        {icon && <span className="text-sm">{icon}</span>}
        {label}
      </span>
    </div>
  );
}
