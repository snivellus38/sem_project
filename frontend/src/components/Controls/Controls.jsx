/**
 * Controls.jsx — Simulation control panel.
 *
 * Features:
 *   - Start / Pause / Stop / Reset buttons
 *   - Manual override sliders (inlet temperature, airflow)
 *   - Simulation speed selector (1×, 2×, 5×, 10×, 25×, 50×)
 *   - Status indicator
 */

import { useState, useCallback } from 'react';
import { Play, Pause, Square, RotateCcw, Gauge, Wind, Timer, Flame } from 'lucide-react';

const SPEEDS = [1, 2, 5, 10, 25, 50];

export default function Controls({ simStatus, sendCmd, state }) {
  const [inletTemp, setInletTemp] = useState(105);
  const [airflow, setAirflow] = useState(0.7);
  const [speed, setSpeed] = useState(10);

  const isRunning = simStatus === 'running';
  const isPaused = simStatus === 'paused';
  const isFinished = simStatus === 'finished';
  const isIdle = simStatus === 'idle';

  const handleStart = useCallback(() => {
    sendCmd('start', { speed });
  }, [sendCmd, speed]);

  const handlePause = useCallback(() => sendCmd('pause'), [sendCmd]);
  const handleStop = useCallback(() => sendCmd('stop'), [sendCmd]);
  const handleReset = useCallback(() => sendCmd('reset'), [sendCmd]);

  const handleTempChange = useCallback(
    (e) => {
      const v = +e.target.value;
      setInletTemp(v);
      sendCmd('set_controls', { inlet_temp: v, airflow });
    },
    [sendCmd, airflow],
  );

  const handleAirflowChange = useCallback(
    (e) => {
      const v = +e.target.value;
      setAirflow(v);
      sendCmd('set_controls', { inlet_temp: inletTemp, airflow: v });
    },
    [sendCmd, inletTemp],
  );

  const handleSpeedChange = useCallback(
    (s) => {
      setSpeed(s);
      sendCmd('set_speed', { speed: s });
    },
    [sendCmd],
  );

  // Status badge colour
  const statusColor = {
    idle: '#94a3b8',
    running: '#4ade80',
    paused: '#fbbf24',
    finished: '#38bdf8',
  }[simStatus] || '#94a3b8';

  return (
    <div className="glass p-4 flex flex-col gap-4 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-bold tracking-wide text-slate-200">Controls</h2>
        <span
          className="text-[10px] uppercase font-semibold px-2 py-0.5 rounded-full"
          style={{ background: `${statusColor}22`, color: statusColor, border: `1px solid ${statusColor}44` }}
        >
          {simStatus}
        </span>
      </div>

      {/* Transport buttons */}
      <div className="flex gap-2">
        {(isIdle || isPaused || isFinished) && (
          <button
            onClick={handleStart}
            className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-xl
                       bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-400
                       border border-emerald-500/30 transition-all text-sm font-medium"
          >
            <Play size={14} /> {isPaused ? 'Resume' : 'Start'}
          </button>
        )}
        {isRunning && (
          <button
            onClick={handlePause}
            className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-xl
                       bg-amber-500/20 hover:bg-amber-500/30 text-amber-400
                       border border-amber-500/30 transition-all text-sm font-medium"
          >
            <Pause size={14} /> Pause
          </button>
        )}
        {(isRunning || isPaused) && (
          <button
            onClick={handleStop}
            className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-xl
                       bg-red-500/20 hover:bg-red-500/30 text-red-400
                       border border-red-500/30 transition-all text-sm font-medium"
          >
            <Square size={14} /> Stop
          </button>
        )}
        <button
          onClick={handleReset}
          className="flex items-center justify-center gap-1.5 py-2 px-3 rounded-xl
                     bg-slate-500/20 hover:bg-slate-500/30 text-slate-300
                     border border-slate-500/30 transition-all text-sm"
          title="Reset to t=0"
        >
          <RotateCcw size={14} />
        </button>
      </div>

      {/* Speed selector */}
      <div>
        <label className="text-xs text-slate-400 flex items-center gap-1 mb-1.5">
          <Timer size={12} /> Sim Speed
        </label>
        <div className="flex gap-1">
          {SPEEDS.map((s) => (
            <button
              key={s}
              onClick={() => handleSpeedChange(s)}
              className={`flex-1 py-1 rounded-lg text-xs font-medium transition-all
                ${speed === s
                  ? 'bg-sky-500/30 text-sky-300 border border-sky-500/40'
                  : 'bg-white/5 text-slate-400 border border-transparent hover:bg-white/10'
                }`}
            >
              {s}×
            </button>
          ))}
        </div>
      </div>

      {/* Inlet Temperature slider */}
      <div>
        <label className="text-xs text-slate-400 flex items-center justify-between mb-1">
          <span className="flex items-center gap-1"><Flame size={12} /> Inlet Temp</span>
          <span className="text-slate-300 font-mono">{inletTemp}°C</span>
        </label>
        <input
          type="range"
          min={80} max={130} step={1}
          value={inletTemp}
          onChange={handleTempChange}
          className="w-full h-1.5 rounded-full appearance-none cursor-pointer
                     bg-gradient-to-r from-orange-400/40 to-red-500/40
                     [&::-webkit-slider-thumb]:appearance-none
                     [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4
                     [&::-webkit-slider-thumb]:rounded-full
                     [&::-webkit-slider-thumb]:bg-orange-400
                     [&::-webkit-slider-thumb]:border-2 [&::-webkit-slider-thumb]:border-white/30
                     [&::-webkit-slider-thumb]:shadow-lg"
        />
      </div>

      {/* Airflow slider */}
      <div>
        <label className="text-xs text-slate-400 flex items-center justify-between mb-1">
          <span className="flex items-center gap-1"><Wind size={12} /> Airflow</span>
          <span className="text-slate-300 font-mono">{(airflow * 100).toFixed(0)}%</span>
        </label>
        <input
          type="range"
          min={0.2} max={1.0} step={0.05}
          value={airflow}
          onChange={handleAirflowChange}
          className="w-full h-1.5 rounded-full appearance-none cursor-pointer
                     bg-gradient-to-r from-blue-400/40 to-sky-500/40
                     [&::-webkit-slider-thumb]:appearance-none
                     [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4
                     [&::-webkit-slider-thumb]:rounded-full
                     [&::-webkit-slider-thumb]:bg-sky-400
                     [&::-webkit-slider-thumb]:border-2 [&::-webkit-slider-thumb]:border-white/30
                     [&::-webkit-slider-thumb]:shadow-lg"
        />
      </div>

      {/* Elapsed time & moisture mini-readout */}
      {state && (
        <div className="flex justify-between text-xs text-slate-400 border-t border-white/5 pt-2">
          <span>t = {state.time?.toFixed(1)} min</span>
          <span>M = {(state.moisture * 100).toFixed(1)}%</span>
          <span>T_bed = {state.bed_temp?.toFixed(0)}°C</span>
        </div>
      )}
    </div>
  );
}
