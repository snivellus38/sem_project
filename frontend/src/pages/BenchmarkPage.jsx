/**
 * BenchmarkPage.jsx — RL vs PID comparison screen.
 */

import { useEffect, useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { RefreshCcw } from 'lucide-react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceLine,
} from 'recharts';
import { api } from '../utils/api';

function fallbackSeries(currentMoisture) {
  const start = Math.max(40, currentMoisture + 12);
  return Array.from({ length: 21 }).map((_, i) => {
    const t = i * 1.5;
    const rl = Math.max(3.5, start * Math.exp(-0.14 * i));
    const pid = Math.max(3.5, start * Math.exp(-0.11 * i) + Math.sin(i * 0.7) * 1.8);
    return { t: Number(t.toFixed(1)), rl: Number(rl.toFixed(2)), pid: Number(pid.toFixed(2)) };
  });
}

export default function BenchmarkPage({ state }) {
  const moisture = state?.moisture != null ? state.moisture * 100 : 70;
  const [payload, setPayload] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedModel, setSelectedModel] = useState('auto');
  const [leaderboard, setLeaderboard] = useState([]);
  const [boardLoading, setBoardLoading] = useState(false);

  const modelOptions = [
    { label: 'Auto', value: 'auto' },
    { label: 'PPO Base', value: 'tea_dryer_PPO' },
    { label: 'PPO Energy', value: 'tea_dryer_PPO_energy' },
    { label: 'PPO Balanced', value: 'tea_dryer_PPO_balanced' },
  ];

  const loadBenchmark = async (model = selectedModel) => {
    setLoading(true);
    setError('');
    try {
      const data = await api.benchmark(model === 'auto' ? null : model);
      setPayload(data);
    } catch (err) {
      setError(err.message || 'Could not load benchmark data');
    } finally {
      setLoading(false);
    }
  };

  const loadLeaderboard = async () => {
    setBoardLoading(true);
    try {
      const requests = modelOptions.map(async (opt) => {
        try {
          const data = await api.benchmark(opt.value === 'auto' ? null : opt.value);
          const rl = data?.summary?.rl;
          if (!rl) return null;
          return {
            model: opt.label,
            source: data?.meta?.rl_source || '-',
            energy: rl.energy_kwh,
            tracking: rl.tracking_mae_pct,
            cycle: rl.cycle_time_min,
            finalMoisture: rl.final_moisture_pct,
            score: Number((rl.energy_kwh * 0.6 + rl.tracking_mae_pct * 0.4).toFixed(4)),
          };
        } catch {
          return null;
        }
      });
      const rows = (await Promise.all(requests)).filter(Boolean);
      rows.sort((a, b) => a.score - b.score);
      setLeaderboard(rows);
    } finally {
      setBoardLoading(false);
    }
  };

  useEffect(() => {
    loadBenchmark();
    loadLeaderboard();
  }, []);

  useEffect(() => {
    loadBenchmark(selectedModel);
  }, [selectedModel]);

  const data = useMemo(() => {
    if (payload?.trajectory?.length) return payload.trajectory;
    return fallbackSeries(moisture);
  }, [payload, moisture]);

  const summary = payload?.summary;
  const rlError = summary?.rl?.tracking_mae_pct ?? 3.14;
  const pidError = summary?.pid?.tracking_mae_pct ?? 6.82;
  const fuelDelta = summary?.delta?.energy_saved_pct ?? 11.7;
  const cycleDelta = summary?.delta?.cycle_time_saved_pct ?? 0;
  const trackDelta = summary?.delta?.tracking_error_improvement_pct ?? 0;
  const source = payload?.meta?.rl_source ?? 'fallback';
  const targetMoisture = payload?.meta?.target_moisture_pct ?? 4.0;
  const fuelDeltaText = `${fuelDelta >= 0 ? '-' : '+'}${Math.abs(fuelDelta).toFixed(1)}%`;
  const cycleDeltaText = `${cycleDelta >= 0 ? '+' : ''}${cycleDelta.toFixed(1)}%`;

  const derivedSeries = useMemo(() => {
    return data.map((row) => {
      const gap = row.pid - row.rl;
      return {
        ...row,
        gap: Number(gap.toFixed(3)),
        rlErr: Number(Math.abs(row.rl - targetMoisture).toFixed(3)),
        pidErr: Number(Math.abs(row.pid - targetMoisture).toFixed(3)),
      };
    });
  }, [data, targetMoisture]);

  const deltaBars = useMemo(() => {
    return [
      { metric: 'Energy Saved %', value: Number(fuelDelta.toFixed(2)) },
      { metric: 'Tracking Improvement %', value: Number(trackDelta.toFixed(2)) },
      { metric: 'Cycle Time Saved %', value: Number(cycleDelta.toFixed(2)) },
    ];
  }, [fuelDelta, trackDelta, cycleDelta]);

  const insight = useMemo(() => {
    if (!derivedSeries.length) {
      return { maxGap: 0, meanGap: 0, finalGap: 0 };
    }
    const gaps = derivedSeries.map((d) => d.gap);
    const meanGap = gaps.reduce((a, b) => a + b, 0) / gaps.length;
    return {
      maxGap: Number(Math.max(...gaps).toFixed(2)),
      meanGap: Number(meanGap.toFixed(2)),
      finalGap: Number(gaps[gaps.length - 1].toFixed(2)),
    };
  }, [derivedSeries]);

  return (
    <div className="h-full overflow-y-auto bg-scene px-4 sm:px-6 py-8">
      <motion.div
        initial={{ opacity: 0, y: 18 }}
        animate={{ opacity: 1, y: 0 }}
        className="max-w-6xl mx-auto"
      >
        <div className="glass p-6 sm:p-7 mb-4">
          <div className="flex items-start sm:items-center justify-between gap-3 flex-col sm:flex-row">
            <div>
              <h1 className="text-3xl sm:text-4xl font-semibold text-white mb-2">RL vs PID Benchmark</h1>
              <p className="text-sm text-slate-300">Tracking stability, energy use, and moisture trajectory comparison.</p>
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              <select
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
                className="px-3 py-2 rounded-full border border-white/20 bg-slate-900/60 text-slate-200 text-sm"
              >
                {modelOptions.map((opt) => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.97 }}
                onClick={() => loadBenchmark(selectedModel)}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-white/20 hover:border-emerald-300/35 text-slate-200 text-sm"
              >
                <RefreshCcw size={14} /> Refresh
              </motion.button>
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.97 }}
                onClick={loadLeaderboard}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-white/20 hover:border-sky-300/35 text-slate-200 text-sm"
              >
                <RefreshCcw size={14} /> Compare Models
              </motion.button>
            </div>
          </div>
          <div className="mt-3 text-xs text-slate-500">Data source: {source}{loading ? ' • updating...' : ''}</div>
          {error ? <div className="mt-2 text-xs text-rose-300">{error}</div> : null}
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 mb-4">
          <div className="glass p-4">
            <div className="text-[11px] uppercase tracking-[0.14em] text-slate-500 mb-1">RL Tracking MAE</div>
            <div className="text-2xl font-semibold text-emerald-300">{rlError.toFixed(2)}</div>
          </div>
          <div className="glass p-4">
            <div className="text-[11px] uppercase tracking-[0.14em] text-slate-500 mb-1">PID Tracking MAE</div>
            <div className="text-2xl font-semibold text-rose-300">{pidError.toFixed(2)}</div>
          </div>
          <div className="glass p-4">
            <div className="text-[11px] uppercase tracking-[0.14em] text-slate-500 mb-1">Fuel Saved (RL)</div>
            <div className="text-2xl font-semibold text-sky-300">{fuelDeltaText}</div>
          </div>
          <div className="glass p-4">
            <div className="text-[11px] uppercase tracking-[0.14em] text-slate-500 mb-1">Cycle Time Saved</div>
            <div className="text-2xl font-semibold text-amber-200">{cycleDeltaText}</div>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-4">
          <div className="glass p-4">
            <div className="text-[11px] uppercase tracking-[0.14em] text-slate-500 mb-1">Target Moisture</div>
            <div className="text-2xl font-semibold text-cyan-200">{targetMoisture.toFixed(2)}%</div>
          </div>
          <div className="glass p-4">
            <div className="text-[11px] uppercase tracking-[0.14em] text-slate-500 mb-1">Mean Gap (PID - RL)</div>
            <div className="text-2xl font-semibold text-violet-200">{insight.meanGap.toFixed(2)}%</div>
          </div>
          <div className="glass p-4">
            <div className="text-[11px] uppercase tracking-[0.14em] text-slate-500 mb-1">Max Gap (PID - RL)</div>
            <div className="text-2xl font-semibold text-fuchsia-200">{insight.maxGap.toFixed(2)}%</div>
          </div>
        </div>

        <div className="glass p-4 sm:p-6 h-[360px] mb-4">
          <div className="text-sm text-slate-300 mb-3">Moisture Trajectory</div>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 10, right: 20, left: 0, bottom: 5 }}>
              <CartesianGrid stroke="rgba(255,255,255,0.08)" strokeDasharray="4 4" />
              <XAxis dataKey="t" stroke="rgba(255,255,255,0.45)" tick={{ fontSize: 11 }} />
              <YAxis stroke="rgba(255,255,255,0.45)" tick={{ fontSize: 11 }} />
              <Tooltip
                contentStyle={{
                  background: 'rgba(10, 16, 30, 0.9)',
                  border: '1px solid rgba(255,255,255,0.15)',
                  borderRadius: '10px',
                }}
              />
              <ReferenceLine y={targetMoisture} stroke="rgba(56, 189, 248, 0.7)" strokeDasharray="3 3" />
              <Line type="monotone" dataKey="rl" stroke="#4ade80" strokeWidth={3} dot={false} name="RL" />
              <Line type="monotone" dataKey="pid" stroke="#fb7185" strokeWidth={2.4} dot={false} name="PID" />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
          <div className="glass p-4 sm:p-6 h-[320px]">
            <div className="text-sm text-slate-300 mb-3">Moisture Gap Over Time (PID - RL)</div>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={derivedSeries} margin={{ top: 10, right: 20, left: 0, bottom: 5 }}>
                <CartesianGrid stroke="rgba(255,255,255,0.08)" strokeDasharray="4 4" />
                <XAxis dataKey="t" stroke="rgba(255,255,255,0.45)" tick={{ fontSize: 11 }} />
                <YAxis stroke="rgba(255,255,255,0.45)" tick={{ fontSize: 11 }} />
                <Tooltip
                  contentStyle={{
                    background: 'rgba(10, 16, 30, 0.9)',
                    border: '1px solid rgba(255,255,255,0.15)',
                    borderRadius: '10px',
                  }}
                />
                <ReferenceLine y={0} stroke="rgba(255,255,255,0.4)" />
                <Area type="monotone" dataKey="gap" stroke="#a78bfa" fill="#a78bfa" fillOpacity={0.25} name="Gap" />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          <div className="glass p-4 sm:p-6 h-[320px]">
            <div className="text-sm text-slate-300 mb-3">Convergence To Target (Absolute Error)</div>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={derivedSeries} margin={{ top: 10, right: 20, left: 0, bottom: 5 }}>
                <CartesianGrid stroke="rgba(255,255,255,0.08)" strokeDasharray="4 4" />
                <XAxis dataKey="t" stroke="rgba(255,255,255,0.45)" tick={{ fontSize: 11 }} />
                <YAxis stroke="rgba(255,255,255,0.45)" tick={{ fontSize: 11 }} />
                <Tooltip
                  contentStyle={{
                    background: 'rgba(10, 16, 30, 0.9)',
                    border: '1px solid rgba(255,255,255,0.15)',
                    borderRadius: '10px',
                  }}
                />
                <Line type="monotone" dataKey="rlErr" stroke="#34d399" strokeWidth={2.8} dot={false} name="RL Error" />
                <Line type="monotone" dataKey="pidErr" stroke="#fda4af" strokeWidth={2.4} dot={false} name="PID Error" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="glass p-4 sm:p-6 h-[300px]">
          <div className="text-sm text-slate-300 mb-3">Performance Delta Summary</div>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={deltaBars} margin={{ top: 10, right: 20, left: 20, bottom: 10 }}>
              <CartesianGrid stroke="rgba(255,255,255,0.08)" strokeDasharray="4 4" />
              <XAxis dataKey="metric" stroke="rgba(255,255,255,0.45)" tick={{ fontSize: 11 }} />
              <YAxis stroke="rgba(255,255,255,0.45)" tick={{ fontSize: 11 }} />
              <Tooltip
                contentStyle={{
                  background: 'rgba(10, 16, 30, 0.9)',
                  border: '1px solid rgba(255,255,255,0.15)',
                  borderRadius: '10px',
                }}
              />
              <ReferenceLine y={0} stroke="rgba(255,255,255,0.4)" />
              <Bar dataKey="value" fill="#38bdf8" radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="glass p-4 sm:p-6 mt-4">
          <div className="flex items-center justify-between mb-3">
            <div className="text-sm text-slate-300">Model Leaderboard (lower score is better)</div>
            <div className="text-xs text-slate-500">{boardLoading ? 'computing...' : `${leaderboard.length} models`}</div>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="text-slate-400 border-b border-white/10">
                  <th className="text-left py-2 pr-3">Rank</th>
                  <th className="text-left py-2 pr-3">Model</th>
                  <th className="text-left py-2 pr-3">Energy</th>
                  <th className="text-left py-2 pr-3">Tracking MAE</th>
                  <th className="text-left py-2 pr-3">Final Moisture</th>
                  <th className="text-left py-2 pr-3">Score</th>
                </tr>
              </thead>
              <tbody>
                {leaderboard.map((row, idx) => (
                  <tr key={row.source} className="border-b border-white/5 text-slate-200">
                    <td className="py-2 pr-3">#{idx + 1}</td>
                    <td className="py-2 pr-3">{row.model}</td>
                    <td className="py-2 pr-3">{row.energy.toFixed(3)}</td>
                    <td className="py-2 pr-3">{row.tracking.toFixed(3)}</td>
                    <td className="py-2 pr-3">{row.finalMoisture.toFixed(3)}%</td>
                    <td className="py-2 pr-3">{row.score.toFixed(3)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
