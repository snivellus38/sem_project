/**
 * AnalyticsPage.jsx — Full analytics view with large charts,
 * gauges grid, sensor readout, and quality assessment.
 */

import { motion } from 'framer-motion';
import AnimatedNumber from '../components/AnimatedNumber';
import Gauge from '../components/Dashboard/Gauge';
import { MoistureChart, TemperatureChart, QualityChart } from '../components/Dashboard/Charts';
import QualityCard from '../components/Dashboard/QualityCard';
import { Droplets, Thermometer, Wind, Leaf, Activity, Beaker } from 'lucide-react';

const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.06, delayChildren: 0.1 } },
};

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0, transition: { type: 'spring', stiffness: 120, damping: 20 } },
};

function StatCard({ label, value, unit, icon: Icon, color, decimals = 1 }) {
  return (
    <motion.div variants={fadeUp} whileHover={{ scale: 1.02, y: -2 }} className="glass glass-hover p-4">
      <div className="flex items-center justify-between mb-2">
        <div className="w-9 h-9 rounded-xl flex items-center justify-center" style={{ background: `${color}12` }}>
          <Icon size={18} style={{ color }} />
        </div>
        <span className="text-[10px] uppercase tracking-wider text-slate-500">{label}</span>
      </div>
      <div className="flex items-baseline gap-1">
        <AnimatedNumber value={value} decimals={decimals} className="text-2xl font-bold text-white" />
        <span className="text-sm text-slate-500">{unit}</span>
      </div>
    </motion.div>
  );
}

export default function AnalyticsPage({ state, history }) {
  const moisture = state?.moisture != null ? state.moisture * 100 : 0;
  const bedTemp = state?.bed_temp ?? 0;
  const inletTemp = state?.inlet_temp ?? 0;
  const airflow = state?.airflow != null ? state.airflow * 100 : 0;
  const enzyme = state?.enzyme_activity != null ? state.enzyme_activity * 100 : 100;
  const pyrazine = state?.pyrazine ?? 0;

  return (
    <motion.div
      key="analytics"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.4 }}
      className="h-full overflow-y-auto bg-scene px-6 py-5"
    >
      <motion.div variants={container} initial="hidden" animate="show" className="max-w-6xl mx-auto">
        {/* Header */}
        <motion.div variants={fadeUp} className="mb-6">
          <h1 className="text-2xl font-bold text-white">Analytics Dashboard</h1>
          <p className="text-sm text-slate-500 mt-1">Real-time telemetry & quality metrics</p>
        </motion.div>

        {/* Stats row */}
        <div className="grid grid-cols-3 lg:grid-cols-6 gap-3 mb-6">
          <StatCard label="Moisture" value={moisture} unit="%" icon={Droplets} color="#38bdf8" />
          <StatCard label="Bed Temp" value={bedTemp} unit="°C" icon={Thermometer} color="#f97316" />
          <StatCard label="Inlet Temp" value={inletTemp} unit="°C" icon={Thermometer} color="#ef4444" />
          <StatCard label="Airflow" value={airflow} unit="%" icon={Wind} color="#60a5fa" decimals={0} />
          <StatCard label="Enzyme" value={enzyme} unit="%" icon={Leaf} color="#a78bfa" />
          <StatCard label="Pyrazine" value={pyrazine} unit="µg/g" icon={Beaker} color="#4ade80" decimals={2} />
        </div>

        {/* Charts grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 mb-6">
          <motion.div variants={fadeUp} className="glass p-4">
            <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-1.5">
              <Droplets size={12} className="text-sky-400" /> Moisture Profile
            </h3>
            <div className="h-[200px]">
              <MoistureChart history={history} />
            </div>
          </motion.div>

          <motion.div variants={fadeUp} className="glass p-4">
            <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-1.5">
              <Thermometer size={12} className="text-orange-400" /> Temperature Profile
            </h3>
            <div className="h-[200px]">
              <TemperatureChart history={history} />
            </div>
          </motion.div>
        </div>

        {/* Bottom row: Quality chart + card + sensors */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
          <motion.div variants={fadeUp} className="lg:col-span-2 glass p-4">
            <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-1.5">
              <Activity size={12} className="text-emerald-400" /> Quality Indicators
            </h3>
            <div className="h-[200px]">
              <QualityChart history={history} />
            </div>
          </motion.div>

          <motion.div variants={fadeUp} className="flex flex-col gap-3">
            <QualityCard state={state} />

            {/* Sensor readout */}
            {state?.sensors?.enose && (
              <div className="glass-sm p-3 flex-1">
                <h3 className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider mb-2">
                  E-Nose Array (8-ch MOS)
                </h3>
                <div className="grid grid-cols-4 gap-1">
                  {state.sensors.enose.voltages.map((v, i) => (
                    <motion.div
                      key={i}
                      whileHover={{ scale: 1.05 }}
                      className="bg-white/4 rounded-lg p-1.5 text-center"
                      style={{ borderBottom: `2px solid hsl(${i * 45}, 70%, 55%)` }}
                    >
                      <div className="text-[9px] text-slate-500">CH{i}</div>
                      <div className="text-xs font-mono text-slate-300">{v.toFixed(2)}</div>
                    </motion.div>
                  ))}
                </div>
                {state.sensors.thermocouple && (
                  <div className="mt-2 flex gap-2 text-[10px]">
                    <span className="text-slate-500">TC:</span>
                    <span className="text-orange-400">
                      In {state.sensors.thermocouple.inlet?.toFixed(0)}°
                    </span>
                    <span className="text-red-400">
                      Bed {state.sensors.thermocouple.bed?.toFixed(0)}°
                    </span>
                    <span className="text-slate-400">
                      Ex {state.sensors.thermocouple.exhaust?.toFixed(0)}°
                    </span>
                  </div>
                )}
                {state.sensors.humidity && (
                  <div className="mt-1 text-[10px] text-slate-500">
                    RH: {state.sensors.humidity.rh_percent?.toFixed(1)}% · Dew: {state.sensors.humidity.dewpoint_c?.toFixed(1)}°C
                  </div>
                )}
              </div>
            )}
          </motion.div>
        </div>

        {/* Gauges row */}
        <motion.div variants={fadeUp} className="mt-6 glass p-4">
          <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
            Gauge Overview
          </h3>
          <div className="flex flex-wrap gap-3 justify-center">
            <Gauge label="Moisture" value={moisture} unit="%" min={0} max={75} color="#38bdf8" />
            <Gauge label="Bed Temp" value={bedTemp} unit="°C" min={20} max={140}
              color={bedTemp > 100 ? '#ef4444' : '#f97316'} />
            <Gauge label="Inlet Temp" value={inletTemp} unit="°C" min={20} max={140} color="#f97316" />
            <Gauge label="Airflow" value={airflow} unit="%" min={0} max={100} color="#60a5fa" />
            <Gauge label="Enzyme" value={enzyme} unit="%" min={0} max={100} color="#a78bfa" />
            <Gauge label="Pyrazine" value={pyrazine} unit="µg/g" min={0} max={5} color="#4ade80" />
          </div>
        </motion.div>

        <div className="h-6" />
      </motion.div>
    </motion.div>
  );
}
