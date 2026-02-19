/**
 * Charts.jsx - Live time-series charts. Renders bare ResponsiveContainer
 * so parent can wrap in any layout (glass card, page section, etc.)
 */

import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend, Area, AreaChart,
} from "recharts";

const tick = { fontSize: 10, fill: "#64748b" };
const tooltipStyle = {
  contentStyle: { background: "#0f172a", border: "1px solid #1e3a5f", borderRadius: 12, fontSize: 11 },
  labelStyle: { color: "#94a3b8" },
};

function downsample(data, max = 150) {
  if (data.length <= max) return data;
  const step = Math.ceil(data.length / max);
  return data.filter((_, i) => i % step === 0 || i === data.length - 1);
}

export function MoistureChart({ history }) {
  const data = downsample(
    history.map((s) => ({ t: s.time?.toFixed(1), M: +(s.moisture * 100).toFixed(2) }))
  );
  return (
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={data}>
        <defs>
          <linearGradient id="moistGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#38bdf8" stopOpacity={0.35} />
            <stop offset="100%" stopColor="#38bdf8" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
        <XAxis dataKey="t" tick={tick} stroke="#1e3a5f" />
        <YAxis domain={[0, 75]} tick={tick} stroke="#1e3a5f" />
        <Tooltip {...tooltipStyle} />
        <Area type="monotone" dataKey="M" stroke="#38bdf8" fill="url(#moistGrad)" strokeWidth={2} dot={false} name="Moisture %" />
      </AreaChart>
    </ResponsiveContainer>
  );
}

export function TemperatureChart({ history }) {
  const data = downsample(
    history.map((s) => ({
      t: s.time?.toFixed(1),
      Inlet: +s.inlet_temp?.toFixed(1),
      Bed: +s.bed_temp?.toFixed(1),
    }))
  );
  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
        <XAxis dataKey="t" tick={tick} stroke="#1e3a5f" />
        <YAxis domain={[20, 140]} tick={tick} stroke="#1e3a5f" />
        <Tooltip {...tooltipStyle} />
        <Legend wrapperStyle={{ fontSize: 10 }} />
        <Line type="monotone" dataKey="Inlet" stroke="#f97316" strokeWidth={2} dot={false} />
        <Line type="monotone" dataKey="Bed" stroke="#ef4444" strokeWidth={2} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}

export function QualityChart({ history }) {
  const data = downsample(
    history.map((s) => ({
      t: s.time?.toFixed(1),
      Enzyme: +(s.enzyme_activity * 100).toFixed(1),
      Pyrazine: +s.pyrazine?.toFixed(2),
      "L*": +s.l_star?.toFixed(1),
    }))
  );
  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
        <XAxis dataKey="t" tick={tick} stroke="#1e3a5f" />
        <YAxis tick={tick} stroke="#1e3a5f" />
        <Tooltip {...tooltipStyle} />
        <Legend wrapperStyle={{ fontSize: 10 }} />
        <Line type="monotone" dataKey="Enzyme" stroke="#a78bfa" strokeWidth={2} dot={false} />
        <Line type="monotone" dataKey="Pyrazine" stroke="#4ade80" strokeWidth={2} dot={false} />
        <Line type="monotone" dataKey="L*" stroke="#fbbf24" strokeWidth={2} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}
