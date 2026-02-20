/**
 * TwinPage.jsx - Combined Digital Twin + Analytics + AI Co-Pilot.
 *
 * Layout:  Left  (55%) = full 3D scene + floating sim controls + Co-Pilot feed
 *          Right (45%) = scrollable analytics panel (stats, charts, cost dashboard, gauges, sensors)
 */

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Settings, X, Play, Pause, Square, RotateCcw, Flame, Wind, Timer,
  Droplets, Thermometer, Leaf, Activity, Beaker, ChevronLeft, ChevronRight,
  Zap,
} from "lucide-react";
import Scene3D from "../components/Scene3D/Scene3D";
import QualityCard from "../components/Dashboard/QualityCard";
import AnimatedNumber from "../components/AnimatedNumber";
import Gauge from "../components/Dashboard/Gauge";
import { MoistureChart, TemperatureChart, QualityChart } from "../components/Dashboard/Charts";
import CostDashboard from "../components/Dashboard/CostDashboard";
import CoPilotFeed from "../components/Dashboard/CoPilotFeed";

/*  Animation helpers  */
const stagger = {
  hidden: {},
  show: { transition: { staggerChildren: 0.05, delayChildren: 0.1 } },
};
const fadeUp = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0, transition: { type: "spring", stiffness: 140, damping: 22 } },
};

/*  Stat mini-card  */
function Stat({ label, value, unit, icon: Icon, color, decimals = 1 }) {
  return (
    <motion.div variants={fadeUp} whileHover={{ scale: 1.03, y: -1 }} className="glass glass-hover p-3">
      <div className="flex items-center justify-between mb-1">
        <div className="w-7 h-7 rounded-lg flex items-center justify-center" style={{ background: `${color}12` }}>
          <Icon size={14} style={{ color }} />
        </div>
        <span className="text-[9px] uppercase tracking-wider text-slate-500">{label}</span>
      </div>
      <div className="flex items-baseline gap-1">
        <AnimatedNumber value={value} decimals={decimals} className="text-lg font-bold text-white" />
        <span className="text-xs text-slate-500">{unit}</span>
      </div>
    </motion.div>
  );
}

/*  Constants  */
const SPEEDS = [1, 2, 5, 10, 25, 50];

/* 
   Main Component
    */
export default function TwinPage({ state, simStatus, sendCmd, history, alerts, clearAlerts }) {
  const [panelOpen, setPanelOpen] = useState(true);
  const [analyticsOpen, setAnalyticsOpen] = useState(true);
  const [inletTemp, setInletTemp] = useState(105);
  const [airflow, setAirflow] = useState(0.7);
  const [speed, setSpeed] = useState(10);

  const isRunning = simStatus === "running";
  const isPaused  = simStatus === "paused";
  const isFinished = simStatus === "finished";
  const isIdle    = simStatus === "idle";

  const statusColor = {
    idle: "#94a3b8", running: "#4ade80", paused: "#fbbf24", finished: "#38bdf8",
  }[simStatus] || "#94a3b8";

  /* Derived values */
  const moisture  = state?.moisture != null ? state.moisture * 100 : 0;
  const bedTemp   = state?.bed_temp ?? 0;
  const inletT    = state?.inlet_temp ?? 0;
  const af        = state?.airflow != null ? state.airflow * 100 : 0;
  const enzyme    = state?.enzyme_activity != null ? state.enzyme_activity * 100 : 100;
  const pyrazine  = state?.pyrazine ?? 0;

  return (
    <div className="h-full w-full flex bg-scene">

      {/*  LEFT: 3D Scene  */}
      <div className={`relative transition-all duration-300 ease-out ${analyticsOpen ? "flex-[55] min-w-0" : "flex-1"}`}>
        <div className="absolute inset-0">
          <Scene3D state={state} />
        </div>

        {/* Sim-control toggle */}
        <motion.button
          whileHover={{ scale: 1.1 }} whileTap={{ scale: 0.9 }}
          onClick={() => setPanelOpen(!panelOpen)}
          className="absolute top-4 right-4 z-20 w-10 h-10 rounded-xl glass
                     flex items-center justify-center text-slate-300 hover:text-white transition-colors"
        >
          {panelOpen ? <X size={18} /> : <Settings size={18} />}
        </motion.button>

        {/* Floating sim-control panel */}
        <AnimatePresence>
          {panelOpen && (
            <motion.div
              initial={{ x: 80, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: 80, opacity: 0 }}
              transition={{ type: "spring", stiffness: 300, damping: 30 }}
              className="absolute top-4 right-16 bottom-4 w-[250px] z-10
                         glass p-3 flex flex-col gap-2.5 overflow-y-auto"
            >
              {/* Status */}
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-bold text-white">Simulation</h3>
                <motion.span
                  animate={{ scale: [1, 1.05, 1] }}
                  transition={{ duration: 2, repeat: Infinity }}
                  className="text-[9px] uppercase font-semibold px-2 py-0.5 rounded-full"
                  style={{ background: `${statusColor}18`, color: statusColor, border: `1px solid ${statusColor}33` }}
                >
                  {simStatus}
                </motion.span>
              </div>

              {/* Transport */}
              <div className="flex gap-1.5">
                {(isIdle || isPaused || isFinished) && (
                  <motion.button whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
                    onClick={() => sendCmd("start", { speed })}
                    className="flex-1 flex items-center justify-center gap-1 py-1.5 rounded-xl
                               bg-emerald-500/15 hover:bg-emerald-500/25 text-emerald-400
                               border border-emerald-500/20 text-[10px] font-medium transition-all">
                    <Play size={11} /> {isPaused ? "Resume" : "Start"}
                  </motion.button>
                )}
                {isRunning && (
                  <motion.button whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
                    onClick={() => sendCmd("pause")}
                    className="flex-1 flex items-center justify-center gap-1 py-1.5 rounded-xl
                               bg-amber-500/15 hover:bg-amber-500/25 text-amber-400
                               border border-amber-500/20 text-[10px] font-medium transition-all">
                    <Pause size={11} /> Pause
                  </motion.button>
                )}
                {(isRunning || isPaused) && (
                  <motion.button whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
                    onClick={() => sendCmd("stop")}
                    className="flex-1 flex items-center justify-center gap-1 py-1.5 rounded-xl
                               bg-red-500/15 hover:bg-red-500/25 text-red-400
                               border border-red-500/20 text-[10px] font-medium transition-all">
                    <Square size={11} /> Stop
                  </motion.button>
                )}
                <motion.button whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
                  onClick={() => sendCmd("reset")}
                  className="w-8 flex items-center justify-center rounded-xl
                             bg-slate-500/15 hover:bg-slate-500/25 text-slate-400
                             border border-slate-500/20 transition-all">
                  <RotateCcw size={11} />
                </motion.button>
              </div>

              {/* Speed */}
              <div>
                <label className="text-[9px] text-slate-500 uppercase tracking-wider flex items-center gap-1 mb-1">
                  <Timer size={9} /> Speed
                </label>
                <div className="flex gap-1">
                  {SPEEDS.map((s) => (
                    <motion.button key={s} whileHover={{ scale: 1.08 }} whileTap={{ scale: 0.95 }}
                      onClick={() => { setSpeed(s); sendCmd("set_speed", { speed: s }); }}
                      className={`flex-1 py-1 rounded-lg text-[9px] font-medium transition-all
                        ${speed === s
                          ? "bg-sky-500/25 text-sky-300 border border-sky-500/30"
                          : "bg-white/4 text-slate-500 border border-transparent hover:bg-white/8"}`}>
                      {s}
                    </motion.button>
                  ))}
                </div>
              </div>

              {/* Temp */}
              <div>
                <label className="text-[9px] text-slate-500 uppercase tracking-wider flex items-center justify-between mb-1">
                  <span className="flex items-center gap-1"><Flame size={9} /> Inlet Temp</span>
                  <span className="text-orange-400 font-mono">{inletTemp}C</span>
                </label>
                <input type="range" min={80} max={130} step={1} value={inletTemp}
                  onChange={(e) => { const v = +e.target.value; setInletTemp(v); sendCmd("set_controls", { inlet_temp: v, airflow }); }}
                  className="w-full" style={{ accentColor: "#f97316" }} />
              </div>

              {/* Airflow */}
              <div>
                <label className="text-[9px] text-slate-500 uppercase tracking-wider flex items-center justify-between mb-1">
                  <span className="flex items-center gap-1"><Wind size={9} /> Airflow</span>
                  <span className="text-sky-400 font-mono">{(airflow * 100).toFixed(0)}%</span>
                </label>
                <input type="range" min={0.2} max={1.0} step={0.05} value={airflow}
                  onChange={(e) => { const v = +e.target.value; setAirflow(v); sendCmd("set_controls", { inlet_temp: inletTemp, airflow: v }); }}
                  className="w-full" style={{ accentColor: "#38bdf8" }} />
              </div>

              <div className="border-t border-white/5" />
              <QualityCard state={state} />
            </motion.div>
          )}
        </AnimatePresence>

        {/* Floating Co-Pilot Feed (bottom-left of 3D viewport) */}
        <div className="absolute bottom-4 left-4 z-10 w-[320px]">
          <CoPilotFeed alerts={alerts} onClear={clearAlerts} />
        </div>
      </div>

      {/*  DIVIDER: analytics toggle  */}
      <motion.button
        whileHover={{ scale: 1.1 }} whileTap={{ scale: 0.9 }}
        onClick={() => setAnalyticsOpen(!analyticsOpen)}
        className="relative z-20 w-5 shrink-0 flex items-center justify-center
                   bg-white/[0.03] hover:bg-white/[0.06] border-x border-white/[0.04]
                   transition-colors group"
      >
        {analyticsOpen
          ? <ChevronRight size={14} className="text-slate-500 group-hover:text-white transition-colors" />
          : <ChevronLeft  size={14} className="text-slate-500 group-hover:text-white transition-colors" />}
      </motion.button>

      {/*  RIGHT: Analytics Panel  */}
      <AnimatePresence>
        {analyticsOpen && (
          <motion.div
            key="analytics-panel"
            initial={{ width: 0, opacity: 0 }}
            animate={{ width: "45%", opacity: 1 }}
            exit={{ width: 0, opacity: 0 }}
            transition={{ type: "spring", stiffness: 200, damping: 28 }}
            className="shrink-0 overflow-hidden"
          >
            <div className="h-full overflow-y-auto overflow-x-hidden px-4 py-4">
              <motion.div variants={stagger} initial="hidden" animate="show">

                {/* Section title */}
                <motion.div variants={fadeUp} className="mb-4">
                  <h2 className="text-lg font-bold text-white">Live Analytics</h2>
                  <p className="text-[11px] text-slate-500">Real-time telemetry & quality metrics</p>
                </motion.div>

                {/* Stat cards */}
                <div className="grid grid-cols-3 gap-2 mb-4">
                  <Stat label="Moisture" value={moisture} unit="%" icon={Droplets} color="#38bdf8" />
                  <Stat label="Bed Temp" value={bedTemp} unit="C" icon={Thermometer} color="#f97316" />
                  <Stat label="Inlet" value={inletT} unit="C" icon={Thermometer} color="#ef4444" />
                  <Stat label="Airflow" value={af} unit="%" icon={Wind} color="#60a5fa" decimals={0} />
                  <Stat label="Enzyme" value={enzyme} unit="%" icon={Leaf} color="#a78bfa" />
                  <Stat label="Pyrazine" value={pyrazine} unit="µg/g" icon={Beaker} color="#4ade80" decimals={2} />
                </div>

                {/* Live Cost Dashboard */}
                <div className="mb-3">
                  <CostDashboard state={state} />
                </div>

                {/* Moisture chart */}
                <motion.div variants={fadeUp} className="glass p-3 mb-3">
                  <h3 className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                    <Droplets size={11} className="text-sky-400" /> Moisture Profile
                  </h3>
                  <div className="h-[160px]">
                    <MoistureChart history={history} />
                  </div>
                </motion.div>

                {/* Temperature chart */}
                <motion.div variants={fadeUp} className="glass p-3 mb-3">
                  <h3 className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                    <Thermometer size={11} className="text-orange-400" /> Temperature Profile
                  </h3>
                  <div className="h-[160px]">
                    <TemperatureChart history={history} />
                  </div>
                </motion.div>

                {/* Quality chart */}
                <motion.div variants={fadeUp} className="glass p-3 mb-3">
                  <h3 className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                    <Activity size={11} className="text-emerald-400" /> Quality Indicators
                  </h3>
                  <div className="h-[160px]">
                    <QualityChart history={history} />
                  </div>
                </motion.div>

                {/* Quality card + sensors */}
                <div className="grid grid-cols-1 xl:grid-cols-2 gap-3 mb-3">
                  <motion.div variants={fadeUp}>
                    <QualityCard state={state} />
                  </motion.div>

                  {/* Sensor readout */}
                  {state?.sensors?.enose && (
                    <motion.div variants={fadeUp} className="glass-sm p-3">
                      <h3 className="text-[9px] font-semibold text-slate-500 uppercase tracking-wider mb-2">
                        E-Nose Array (8-ch MOS)
                      </h3>
                      <div className="grid grid-cols-4 gap-1">
                        {state.sensors.enose.voltages.map((v, i) => (
                          <motion.div key={i} whileHover={{ scale: 1.05 }}
                            className="bg-white/4 rounded-lg p-1 text-center"
                            style={{ borderBottom: `2px solid hsl(${i * 45}, 70%, 55%)` }}>
                            <div className="text-[8px] text-slate-500">CH{i}</div>
                            <div className="text-[10px] font-mono text-slate-300">{v.toFixed(2)}</div>
                          </motion.div>
                        ))}
                      </div>
                      {state.sensors.thermocouple && (
                        <div className="mt-1.5 flex gap-2 text-[9px]">
                          <span className="text-slate-500">TC:</span>
                          <span className="text-orange-400">In {state.sensors.thermocouple.inlet?.toFixed(0)}</span>
                          <span className="text-red-400">Bed {state.sensors.thermocouple.bed?.toFixed(0)}</span>
                          <span className="text-slate-400">Ex {state.sensors.thermocouple.exhaust?.toFixed(0)}</span>
                        </div>
                      )}
                      {state.sensors.humidity && (
                        <div className="mt-1 text-[9px] text-slate-500">
                          RH: {state.sensors.humidity.rh_percent?.toFixed(1)}%  Dew: {state.sensors.humidity.dewpoint_c?.toFixed(1)}C
                        </div>
                      )}
                    </motion.div>
                  )}
                </div>

                {/* Gauges */}
                <motion.div variants={fadeUp} className="glass p-3 mb-4">
                  <h3 className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-2">
                    Gauge Overview
                  </h3>
                  <div className="flex flex-wrap gap-2 justify-center">
                    <Gauge label="Moisture" value={moisture} unit="%" min={0} max={75} color="#38bdf8" />
                    <Gauge label="Bed Temp" value={bedTemp} unit="C" min={20} max={140}
                      color={bedTemp > 100 ? "#ef4444" : "#f97316"} />
                    <Gauge label="Inlet" value={inletT} unit="C" min={20} max={140} color="#f97316" />
                    <Gauge label="Airflow" value={af} unit="%" min={0} max={100} color="#60a5fa" />
                    <Gauge label="Enzyme" value={enzyme} unit="%" min={0} max={100} color="#a78bfa" />
                    <Gauge label="Pyrazine" value={pyrazine} unit="µg/g" min={0} max={5} color="#4ade80" />
                  </div>
                </motion.div>

              </motion.div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
