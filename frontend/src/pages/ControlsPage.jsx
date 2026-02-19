/**
 * ControlsPage.jsx — Full-page simulation controls with
 * detailed settings, mini 3D preview, and status panel.
 */

import { useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import {
  Play, Pause, Square, RotateCcw, Flame, Wind, Timer,
  Gauge, Settings, Activity, AlertTriangle,
} from 'lucide-react';
import Scene3D from '../components/Scene3D/Scene3D';
import AnimatedNumber from '../components/AnimatedNumber';

const SPEEDS = [1, 2, 5, 10, 25, 50];

const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.06, delayChildren: 0.1 } },
};

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0, transition: { type: 'spring', stiffness: 120, damping: 20 } },
};

export default function ControlsPage({ state, simStatus, sendCmd }) {
  const [inletTemp, setInletTemp] = useState(105);
  const [airflow, setAirflow] = useState(0.7);
  const [speed, setSpeed] = useState(10);

  const isRunning = simStatus === 'running';
  const isPaused = simStatus === 'paused';
  const isFinished = simStatus === 'finished';
  const isIdle = simStatus === 'idle';

  const handleTempChange = useCallback((e) => {
    const v = +e.target.value;
    setInletTemp(v);
    sendCmd('set_controls', { inlet_temp: v, airflow });
  }, [sendCmd, airflow]);

  const handleAirflowChange = useCallback((e) => {
    const v = +e.target.value;
    setAirflow(v);
    sendCmd('set_controls', { inlet_temp: inletTemp, airflow: v });
  }, [sendCmd, inletTemp]);

  const statusColor = {
    idle: '#94a3b8', running: '#4ade80', paused: '#fbbf24', finished: '#38bdf8',
  }[simStatus] || '#94a3b8';

  const moisture = state?.moisture != null ? state.moisture * 100 : 70;
  const bedTemp = state?.bed_temp ?? 28;
  const elapsed = state?.time ?? 0;

  return (
    <motion.div
      key="controls"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.4 }}
      className="h-full overflow-y-auto bg-scene px-6 py-5"
    >
      <motion.div variants={container} initial="hidden" animate="show" className="max-w-6xl mx-auto">
        {/* Header */}
        <motion.div variants={fadeUp} className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-white">Simulation Controls</h1>
            <p className="text-sm text-slate-500 mt-1">Configure and manage the drying simulation</p>
          </div>
          <motion.div
            animate={{ scale: [1, 1.04, 1] }}
            transition={{ duration: 2, repeat: Infinity }}
            className="px-4 py-2 rounded-2xl text-sm font-semibold"
            style={{ background: `${statusColor}12`, color: statusColor, border: `1px solid ${statusColor}25` }}
          >
            {simStatus.toUpperCase()}
          </motion.div>
        </motion.div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Left column: Main controls */}
          <div className="lg:col-span-2 flex flex-col gap-4">
            {/* Transport controls */}
            <motion.div variants={fadeUp} className="glass p-5">
              <h3 className="text-xs uppercase tracking-wider text-slate-500 font-semibold mb-4 flex items-center gap-1.5">
                <Activity size={12} /> Transport
              </h3>
              <div className="flex gap-3">
                {(isIdle || isPaused || isFinished) && (
                  <motion.button
                    whileHover={{ scale: 1.03, y: -1 }} whileTap={{ scale: 0.97 }}
                    onClick={() => sendCmd('start', { speed })}
                    className="flex-1 flex items-center justify-center gap-2 py-3.5 rounded-2xl
                               bg-emerald-500/15 hover:bg-emerald-500/25 text-emerald-400
                               border border-emerald-500/25 text-sm font-semibold transition-all glow-emerald"
                  >
                    <Play size={18} /> {isPaused ? 'Resume Simulation' : 'Start Simulation'}
                  </motion.button>
                )}
                {isRunning && (
                  <motion.button
                    whileHover={{ scale: 1.03, y: -1 }} whileTap={{ scale: 0.97 }}
                    onClick={() => sendCmd('pause')}
                    className="flex-1 flex items-center justify-center gap-2 py-3.5 rounded-2xl
                               bg-amber-500/15 hover:bg-amber-500/25 text-amber-400
                               border border-amber-500/25 text-sm font-semibold transition-all glow-amber"
                  >
                    <Pause size={18} /> Pause
                  </motion.button>
                )}
                {(isRunning || isPaused) && (
                  <motion.button
                    whileHover={{ scale: 1.03, y: -1 }} whileTap={{ scale: 0.97 }}
                    onClick={() => sendCmd('stop')}
                    className="flex-1 flex items-center justify-center gap-2 py-3.5 rounded-2xl
                               bg-red-500/15 hover:bg-red-500/25 text-red-400
                               border border-red-500/25 text-sm font-semibold transition-all glow-red"
                  >
                    <Square size={18} /> Stop
                  </motion.button>
                )}
                <motion.button
                  whileHover={{ scale: 1.03, y: -1 }} whileTap={{ scale: 0.97 }}
                  onClick={() => sendCmd('reset')}
                  className="w-14 flex items-center justify-center rounded-2xl
                             bg-slate-500/15 hover:bg-slate-500/25 text-slate-400
                             border border-slate-500/25 transition-all"
                  title="Reset to t=0"
                >
                  <RotateCcw size={18} />
                </motion.button>
              </div>
            </motion.div>

            {/* Speed control */}
            <motion.div variants={fadeUp} className="glass p-5">
              <h3 className="text-xs uppercase tracking-wider text-slate-500 font-semibold mb-4 flex items-center gap-1.5">
                <Timer size={12} /> Simulation Speed
              </h3>
              <div className="grid grid-cols-6 gap-2">
                {SPEEDS.map((s) => (
                  <motion.button
                    key={s}
                    whileHover={{ scale: 1.06 }} whileTap={{ scale: 0.95 }}
                    onClick={() => { setSpeed(s); sendCmd('set_speed', { speed: s }); }}
                    className={`py-3 rounded-2xl text-sm font-semibold transition-all
                      ${speed === s
                        ? 'bg-sky-500/20 text-sky-300 border border-sky-500/30 glow-sky'
                        : 'bg-white/3 text-slate-500 border border-white/5 hover:bg-white/6 hover:text-slate-300'
                      }`}
                  >
                    {s}×
                  </motion.button>
                ))}
              </div>
            </motion.div>

            {/* Manual overrides */}
            <motion.div variants={fadeUp} className="glass p-5">
              <h3 className="text-xs uppercase tracking-wider text-slate-500 font-semibold mb-5 flex items-center gap-1.5">
                <Settings size={12} /> Manual Overrides
              </h3>

              {/* Inlet Temperature */}
              <div className="mb-6">
                <div className="flex items-center justify-between mb-2">
                  <label className="text-sm text-slate-300 flex items-center gap-2">
                    <div className="w-8 h-8 rounded-xl bg-orange-500/10 flex items-center justify-center">
                      <Flame size={16} className="text-orange-400" />
                    </div>
                    Inlet Temperature
                  </label>
                  <div className="flex items-baseline gap-1">
                    <AnimatedNumber value={inletTemp} decimals={0} className="text-xl font-bold text-orange-400" />
                    <span className="text-sm text-slate-500">°C</span>
                  </div>
                </div>
                <div className="relative">
                  <input
                    type="range" min={80} max={130} step={1}
                    value={inletTemp} onChange={handleTempChange}
                    className="w-full h-2"
                    style={{ accentColor: '#f97316' }}
                  />
                  <div className="flex justify-between text-[9px] text-slate-600 mt-1">
                    <span>80°C</span><span>105°C</span><span>130°C</span>
                  </div>
                </div>
              </div>

              {/* Airflow */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-sm text-slate-300 flex items-center gap-2">
                    <div className="w-8 h-8 rounded-xl bg-sky-500/10 flex items-center justify-center">
                      <Wind size={16} className="text-sky-400" />
                    </div>
                    Airflow Damper
                  </label>
                  <div className="flex items-baseline gap-1">
                    <AnimatedNumber value={airflow * 100} decimals={0} className="text-xl font-bold text-sky-400" />
                    <span className="text-sm text-slate-500">%</span>
                  </div>
                </div>
                <div className="relative">
                  <input
                    type="range" min={0.2} max={1.0} step={0.05}
                    value={airflow} onChange={handleAirflowChange}
                    className="w-full h-2"
                    style={{ accentColor: '#38bdf8' }}
                  />
                  <div className="flex justify-between text-[9px] text-slate-600 mt-1">
                    <span>20%</span><span>60%</span><span>100%</span>
                  </div>
                </div>
              </div>
            </motion.div>

            {/* Warnings */}
            {state?.stewing && (
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="glass p-4 border-l-2 border-red-500/50 flex items-center gap-3"
              >
                <AlertTriangle size={20} className="text-red-400 shrink-0" />
                <div>
                  <div className="text-sm text-red-400 font-semibold">Stewing Warning</div>
                  <div className="text-xs text-slate-400">
                    Low temperature + high moisture detected. Increase inlet temperature to avoid enzyme stewing.
                  </div>
                </div>
              </motion.div>
            )}
          </div>

          {/* Right column: Mini 3D preview + live stats */}
          <div className="flex flex-col gap-4">
            {/* Mini 3D preview */}
            <motion.div variants={fadeUp} className="glass overflow-hidden h-[280px]">
              <Scene3D state={state} compact />
            </motion.div>

            {/* Live readout */}
            <motion.div variants={fadeUp} className="glass p-4">
              <h3 className="text-xs uppercase tracking-wider text-slate-500 font-semibold mb-3 flex items-center gap-1.5">
                <Gauge size={12} /> Live Readout
              </h3>
              <div className="space-y-3">
                {[
                  { label: 'Elapsed', value: elapsed, unit: 'min', color: '#94a3b8', decimals: 1 },
                  { label: 'Moisture', value: moisture, unit: '%', color: '#38bdf8', decimals: 1 },
                  { label: 'Bed Temp', value: bedTemp, unit: '°C', color: '#f97316', decimals: 0 },
                  { label: 'Drying Rate', value: Math.abs(state?.drying_rate ?? 0) * 100, unit: '%/min', color: '#4ade80', decimals: 3 },
                ].map((row) => (
                  <div key={row.label} className="flex items-center justify-between">
                    <span className="text-xs text-slate-500">{row.label}</span>
                    <div className="flex items-baseline gap-1">
                      <AnimatedNumber
                        value={row.value}
                        decimals={row.decimals}
                        className="text-sm font-mono font-semibold"
                        style={{ color: row.color }}
                      />
                      <span className="text-[10px] text-slate-600">{row.unit}</span>
                    </div>
                  </div>
                ))}
              </div>
            </motion.div>

            {/* Tea colour */}
            <motion.div variants={fadeUp} className="glass p-4 flex items-center gap-3">
              <motion.div
                animate={{ scale: [1, 1.05, 1] }}
                transition={{ duration: 3, repeat: Infinity }}
                className="w-12 h-12 rounded-2xl border border-white/10"
                style={{ background: state?.color_hex ?? '#7e7f51', transition: 'background 0.5s' }}
              />
              <div>
                <div className="text-xs text-slate-500">Tea Colour</div>
                <div className="text-sm font-mono text-slate-300">{state?.color_hex ?? '#7e7f51'}</div>
                <div className="text-[10px] text-slate-600">
                  L*{state?.l_star?.toFixed(0) ?? '52'} a*{state?.a_star?.toFixed(0) ?? '-8'} b*{state?.b_star?.toFixed(0) ?? '25'}
                </div>
              </div>
            </motion.div>
          </div>
        </div>

        <div className="h-6" />
      </motion.div>
    </motion.div>
  );
}
