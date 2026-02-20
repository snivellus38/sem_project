/**
 * CostDashboard.jsx — Live Financial & Energy Cost Estimator panel.
 *
 * Shows real-time energy consumption, operating cost, SEC, power draw,
 * and batch economics with animated counters and sparkline visual.
 */

import { motion } from "framer-motion";
import {
  Zap, IndianRupee, Gauge as GaugeIcon, Droplets, Factory, TrendingDown,
} from "lucide-react";
import AnimatedNumber from "../AnimatedNumber";

const fadeUp = {
  hidden: { opacity: 0, y: 12 },
  show: { opacity: 1, y: 0, transition: { type: "spring", stiffness: 160, damping: 20 } },
};

/* Micro metric tile */
function CostMetric({ icon: Icon, label, value, unit, color, decimals = 2, large }) {
  return (
    <div className={`flex flex-col ${large ? "col-span-2" : ""}`}>
      <div className="flex items-center gap-1.5 mb-0.5">
        <div
          className="w-5 h-5 rounded-md flex items-center justify-center"
          style={{ background: `${color}15` }}
        >
          <Icon size={11} style={{ color }} />
        </div>
        <span className="text-[8px] uppercase tracking-wider text-slate-500 leading-none">
          {label}
        </span>
      </div>
      <div className="flex items-baseline gap-1">
        <AnimatedNumber
          value={value}
          decimals={decimals}
          className={`${large ? "text-xl" : "text-sm"} font-bold text-white font-mono`}
        />
        <span className="text-[9px] text-slate-500">{unit}</span>
      </div>
    </div>
  );
}

/* Power bar — horizontal fill showing instantaneous draw */
function PowerBar({ kw, maxKw = 30 }) {
  const pct = Math.min((kw / maxKw) * 100, 100);
  const barColor =
    pct > 80 ? "#ef4444" : pct > 50 ? "#f59e0b" : "#22c55e";

  return (
    <div className="mt-1">
      <div className="flex items-center justify-between text-[8px] text-slate-500 mb-0.5">
        <span>Power Draw</span>
        <span className="font-mono" style={{ color: barColor }}>
          {kw.toFixed(1)} kW
        </span>
      </div>
      <div className="h-1.5 rounded-full bg-white/5 overflow-hidden">
        <motion.div
          className="h-full rounded-full"
          style={{ background: barColor }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.4, ease: "easeOut" }}
        />
      </div>
    </div>
  );
}

/* Profit margin mini indicator */
function MarginIndicator({ cost, value }) {
  const margin = value > 0 ? ((value - cost) / value) * 100 : 0;
  const isPositive = margin > 0;

  return (
    <div className="flex items-center justify-between mt-2 pt-2 border-t border-white/5">
      <div className="flex items-center gap-1.5">
        <TrendingDown
          size={11}
          className={isPositive ? "text-emerald-400 rotate-180" : "text-red-400"}
          style={{ transform: isPositive ? "scaleY(-1)" : undefined }}
        />
        <span className="text-[9px] text-slate-500">Batch Margin</span>
      </div>
      <span
        className="text-xs font-bold font-mono"
        style={{ color: isPositive ? "#4ade80" : "#ef4444" }}
      >
        {isPositive ? "+" : ""}
        {margin.toFixed(1)}%
      </span>
    </div>
  );
}

export default function CostDashboard({ state }) {
  const energy = state?.energy_kwh ?? 0;
  const cost = state?.operating_cost_inr ?? 0;
  const sec = state?.sec ?? 0;
  const power = state?.power_kw ?? 0;
  const waterRemoved = state?.water_removed_kg ?? 0;
  const batchValue = state?.batch_value_inr ?? 0;

  return (
    <motion.div variants={fadeUp} className="glass p-3">
      <h3 className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-2.5 flex items-center gap-1.5">
        <Zap size={11} className="text-amber-400" />
        Live Cost Dashboard
      </h3>

      {/* Primary metrics: cost + energy */}
      <div className="grid grid-cols-2 gap-3 mb-2">
        <CostMetric
          icon={IndianRupee}
          label="Operating Cost"
          value={cost}
          unit="₹"
          color="#f59e0b"
          decimals={2}
          large
        />
        <CostMetric
          icon={Zap}
          label="Energy Used"
          value={energy}
          unit="kWh"
          color="#38bdf8"
          decimals={3}
          large
        />
      </div>

      {/* Secondary metrics */}
      <div className="grid grid-cols-3 gap-2 mb-1">
        <CostMetric
          icon={GaugeIcon}
          label="SEC"
          value={sec}
          unit="kWh/kg"
          color="#a78bfa"
          decimals={2}
        />
        <CostMetric
          icon={Droplets}
          label="Water Out"
          value={waterRemoved}
          unit="kg"
          color="#38bdf8"
          decimals={2}
        />
        <CostMetric
          icon={Factory}
          label="Batch Value"
          value={batchValue}
          unit="₹"
          color="#4ade80"
          decimals={0}
        />
      </div>

      {/* Power bar */}
      <PowerBar kw={power} />

      {/* Margin indicator */}
      <MarginIndicator cost={cost} value={batchValue} />
    </motion.div>
  );
}
