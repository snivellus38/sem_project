/**
 * HomePage.jsx — full-width, low-chrome control room landing.
 */

import { useEffect, useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { ArrowRight, BarChart3, Droplets, Gauge, Leaf, Thermometer, Zap } from 'lucide-react';
import AnimatedNumber from '../components/AnimatedNumber';

const taglines = [
  'Predictive Drying Intelligence',
  'Fuel and Quality in Balance',
  'RL-Controlled Tea Processing',
];

const processSteps = ['Sense', 'Predict', 'Act', 'Verify'];

function ParticleBg() {
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      <div className="absolute -top-20 -left-24 h-80 w-80 rounded-full bg-emerald-500/14 blur-3xl" />
      <div className="absolute top-1/3 -right-28 h-96 w-96 rounded-full bg-amber-400/10 blur-3xl" />
      {Array.from({ length: 8 }).map((_, i) => (
        <motion.div
          key={i}
          className="absolute h-1 w-1 rounded-full bg-emerald-200/20"
          initial={{ x: `${Math.random() * 100}%`, y: '110%', opacity: 0 }}
          animate={{ y: '-10%', opacity: [0, 0.28, 0], x: `${Math.random() * 100}%` }}
          transition={{ duration: 12 + Math.random() * 6, repeat: Infinity, delay: Math.random() * 5, ease: 'linear' }}
        />
      ))}
    </div>
  );
}

function Spark({ color, points }) {
  const bars = points.map((v, i) => (
    <div
      key={i}
      className="w-1 rounded-full"
      style={{
        height: `${8 + Math.max(2, Math.min(24, v))}px`,
        background: `${color}${i > points.length - 4 ? '' : '88'}`,
      }}
    />
  ));
  return <div className="flex items-end gap-[2px] h-7">{bars}</div>;
}

function KpiStripItem({ icon: Icon, label, value, unit, color, trend, points, bordered = true }) {
  return (
    <motion.div whileHover={{ y: -1.5 }} className={`py-3 px-3 sm:px-4 ${bordered ? 'xl:border-r xl:border-white/10' : ''}`}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg flex items-center justify-center" style={{ background: `${color}1f` }}>
            <Icon size={15} style={{ color }} />
          </div>
          <span className="text-[11px] uppercase tracking-[0.14em] text-slate-400">{label}</span>
        </div>
        <span className="text-[10px] font-medium" style={{ color }}>{trend}</span>
      </div>
      <div className="flex items-end justify-between gap-3">
        <div className="flex items-baseline gap-1">
          <AnimatedNumber value={value} decimals={1} className="text-[1.85rem] leading-none font-semibold text-white" />
          <span className="text-xs text-slate-400">{unit}</span>
        </div>
        <Spark color={color} points={points} />
      </div>
    </motion.div>
  );
}

function TrendRibbon() {
  const points = [
    [0, 58], [8, 56], [16, 57], [24, 52], [32, 50], [40, 47], [48, 49],
    [56, 43], [64, 41], [72, 38], [80, 36], [88, 32], [96, 30], [100, 28],
  ];

  const d = points
    .map(([x, y], i) => `${i === 0 ? 'M' : 'L'} ${x} ${y}`)
    .join(' ');

  return (
    <svg viewBox="0 0 100 60" preserveAspectRatio="none" className="w-full h-[92px] sm:h-[110px]">
      <defs>
        <linearGradient id="ribbonStroke" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="rgba(74, 222, 128, 0.3)" />
          <stop offset="55%" stopColor="rgba(16, 185, 129, 0.9)" />
          <stop offset="100%" stopColor="rgba(245, 158, 11, 0.7)" />
        </linearGradient>
      </defs>
      <path d={d} fill="none" stroke="url(#ribbonStroke)" strokeWidth="1.8" />
    </svg>
  );
}

export default function HomePage({ setActiveTab, navigate, state }) {
  const goTo = setActiveTab || navigate;

  const moisture = state?.moisture != null ? state.moisture * 100 : 70;
  const bedTemp = state?.bed_temp ?? 28;
  const enzyme = state?.enzyme_activity != null ? state.enzyme_activity * 100 : 100;
  const airflow = state?.airflow != null ? state.airflow * 100 : 70;
  const speed = state?.speed ?? 1;
  const status = state?.status ?? 'idle';

  const [taglineIndex, setTaglineIndex] = useState(0);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    const id = setInterval(() => setTaglineIndex((i) => (i + 1) % taglines.length), 2600);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    const id = setInterval(() => setTick((t) => t + 1), 1200);
    return () => clearInterval(id);
  }, []);

  const lastUpdate = useMemo(() => `${tick % 60}s ago`, [tick]);
  const statusTone = status === 'running'
    ? 'border-emerald-500/25 bg-emerald-500/10 text-emerald-300'
    : status === 'paused'
      ? 'border-amber-500/25 bg-amber-500/10 text-amber-300'
      : 'border-slate-500/25 bg-slate-500/10 text-slate-300';

  const stage = useMemo(() => {
    if (moisture > 55) return 0;
    if (moisture > 30) return 1;
    if (moisture > 10) return 2;
    return 3;
  }, [moisture]);

  const stateLine = useMemo(() => {
    if (status === 'running') return `RL is running at ${speed.toFixed(1)}x with moisture trending down.`;
    if (status === 'paused') return 'Simulation paused. Control state is preserved and ready to resume.';
    return 'System idle. Start a batch to activate live intelligence.';
  }, [status, speed]);

  const rlError = Math.max(1.6, 6.2 - moisture / 25);
  const pidError = rlError + 3.1;
  const fuelDelta = Math.max(4, 17 - moisture / 8);

  const kpis = [
    { icon: Droplets, label: 'Moisture', value: moisture, unit: '%', color: '#4ad6b8', trend: '-0.8%/min', points: [5, 7, 10, 12, 13, 15, 17, 19, 20] },
    { icon: Thermometer, label: 'Bed Temp', value: bedTemp, unit: 'C', color: '#f59e0b', trend: '+0.4C/min', points: [9, 11, 12, 14, 15, 14, 16, 17, 18] },
    { icon: Leaf, label: 'Enzyme', value: enzyme, unit: '%', color: '#7dd3a7', trend: '-0.2%/min', points: [18, 18, 17, 16, 16, 15, 14, 14, 13] },
    { icon: Gauge, label: 'Airflow', value: airflow, unit: '%', color: '#34d399', trend: 'stable', points: [12, 13, 12, 13, 14, 13, 13, 12, 13] },
  ];

  return (
    <motion.div key="home" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.3 }} className="h-full overflow-y-auto relative bg-scene">
      <ParticleBg />

      <div className="relative z-10 w-full h-full min-h-[760px] px-4 sm:px-6 lg:px-8 xl:px-10 py-6 sm:py-7 flex flex-col">
        <section className="border-b border-white/10 pb-6 sm:pb-7">
          <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 xl:gap-8 items-end">
            <div className="xl:col-span-8">
              <div className="flex items-center gap-2 mb-2.5">
                <motion.span key={taglineIndex} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.25 }} className="inline-flex px-3 py-1 rounded-full text-[10px] sm:text-xs uppercase tracking-[0.2em] text-emerald-200 bg-emerald-500/10 border border-emerald-300/20">
                {taglines[taglineIndex]}
              </motion.span>
              </div>

              <h1 className="text-4xl sm:text-5xl lg:text-[4.2rem] font-semibold leading-[0.9] text-white mb-2.5">
                <span className="brand-neuraleaf">NeuraLeaf</span>
                <span className="block text-white/85 mt-1">Control Room</span>
              </h1>

              <p className="text-base text-slate-300/85 mb-5 max-w-2xl">Live AI co-pilot for precision tea drying.</p>

              <div className="flex flex-wrap gap-3">
                <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.97 }} onClick={() => goTo?.('twin')} className="inline-flex items-center gap-2 px-5 py-3 rounded-full bg-gradient-to-r from-emerald-500 to-teal-400 text-[#032018] font-semibold text-sm shadow-[0_0_20px_rgba(16,185,129,0.25)]">
                  Enter Twin <ArrowRight size={15} />
                </motion.button>
                <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.97 }} onClick={() => goTo?.('controls')} className="inline-flex items-center gap-2 px-5 py-3 rounded-full border border-amber-200/30 bg-amber-400/8 text-amber-100 font-medium text-sm">
                  Tune Controls <Zap size={15} />
                </motion.button>
              </div>
            </div>

            <div className="xl:col-span-4">
              <div className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-4 sm:px-5">
                <div className="flex items-center justify-between mb-3">
                  <h2 className="text-xs uppercase tracking-[0.2em] text-slate-400">Live Status</h2>
                  <span className={`text-[10px] px-2 py-1 rounded-full border ${statusTone}`}>{status.toUpperCase()}</span>
                </div>
                <p className="text-sm text-slate-300 leading-relaxed mb-3 min-h-[42px]">{stateLine}</p>
                <div className="text-xs text-slate-500 mb-3.5">Last update: {lastUpdate}</div>
                <div className="grid grid-cols-2 gap-2.5 pt-3 border-t border-white/10 text-xs">
                  <div>
                    <div className="text-slate-500 uppercase tracking-[0.12em] mb-1">Sim Speed</div>
                    <div className="text-white font-semibold">{speed.toFixed(1)}x</div>
                  </div>
                  <div>
                    <div className="text-slate-500 uppercase tracking-[0.12em] mb-1">Mode</div>
                    <div className="text-white font-semibold">{status === 'running' ? 'Auto RL' : 'Standby'}</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="mt-3.5 border-b border-white/10 pb-3.5">
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-y-2">
            {kpis.map((kpi, idx) => (
              <KpiStripItem key={kpi.label} {...kpi} bordered={idx !== kpis.length - 1} />
            ))}
          </div>
        </section>

        <section className="mt-4 flex-1 min-h-[250px] rounded-2xl border border-white/10 bg-white/[0.02] overflow-hidden">
          <div className="h-full grid grid-cols-1 xl:grid-cols-12">
            <div className="xl:col-span-8 p-4 sm:p-5 xl:pr-6 border-b xl:border-b-0 xl:border-r border-white/10 flex flex-col">
              <div className="flex items-center justify-between gap-2 flex-wrap mb-2.5">
                <h2 className="text-xs uppercase tracking-[0.18em] text-slate-400">Process Loop</h2>
                <span className="text-[10px] text-slate-500">Active: {processSteps[stage]}</span>
              </div>

              <div className="grid grid-cols-4 gap-2 mb-3.5">
                {processSteps.map((item, idx) => (
                  <div key={item} className={`text-center text-[10px] sm:text-[11px] py-2 rounded-full border transition-colors ${idx === stage ? 'border-emerald-300/35 bg-emerald-400/10 text-emerald-200' : 'border-white/10 text-slate-500'}`}>
                    {item}
                  </div>
                ))}
              </div>

              <div className="mt-auto">
                <div className="flex items-center justify-between text-[10px] uppercase tracking-[0.14em] text-slate-500 mb-1.5">
                  <span>Drying Trajectory</span>
                  <span>Target Window: 2.0 - 3.0</span>
                </div>
                <TrendRibbon />
                <div className="grid grid-cols-3 gap-3 mt-1 text-xs">
                  <div>
                    <div className="text-slate-500">Current Error</div>
                    <div className="text-emerald-300 font-semibold">{rlError.toFixed(2)}</div>
                  </div>
                  <div>
                    <div className="text-slate-500">Energy Rate</div>
                    <div className="text-amber-200 font-semibold">{(2.2 + speed / 3).toFixed(2)} kWh/kg</div>
                  </div>
                  <div>
                    <div className="text-slate-500">Batch Progress</div>
                    <div className="text-cyan-300 font-semibold">{Math.max(4, Math.min(96, 100 - moisture)).toFixed(0)}%</div>
                  </div>
                </div>
              </div>
            </div>

            <div className="xl:col-span-4 p-4 sm:p-5 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-2.5">
                  <h2 className="text-xs uppercase tracking-[0.18em] text-slate-400">Benchmark Preview</h2>
                  <span className="text-[10px] text-amber-200 bg-amber-400/10 border border-amber-200/25 px-2 py-1 rounded-full">RL vs PID</span>
                </div>

                <div className="grid grid-cols-3 gap-2.5 mb-3.5">
                  <div>
                    <div className="text-[10px] text-slate-500 uppercase tracking-[0.14em] mb-1">RL Error</div>
                    <div className="text-xl font-semibold text-emerald-300">{rlError.toFixed(2)}</div>
                  </div>
                  <div>
                    <div className="text-[10px] text-slate-500 uppercase tracking-[0.14em] mb-1">PID Error</div>
                    <div className="text-xl font-semibold text-rose-300">{pidError.toFixed(2)}</div>
                  </div>
                  <div>
                    <div className="text-[10px] text-slate-500 uppercase tracking-[0.14em] mb-1">Fuel Delta</div>
                    <div className="text-xl font-semibold text-cyan-300">-{fuelDelta.toFixed(1)}%</div>
                  </div>
                </div>
              </div>

              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.97 }}
                onClick={() => goTo?.('benchmark')}
                className="inline-flex items-center gap-2 px-4 py-2.5 rounded-full border border-white/20 hover:border-emerald-300/35 text-slate-200 text-sm w-fit"
              >
                Open Benchmark <BarChart3 size={14} />
              </motion.button>
            </div>
          </div>
        </section>
      </div>
    </motion.div>
  );
}
