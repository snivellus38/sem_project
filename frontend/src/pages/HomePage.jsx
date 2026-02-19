/**
 * HomePage.jsx — Landing page with hero, feature cards, live stats, and CTA.
 */

import { motion } from 'framer-motion';
import { Box, BarChart3, Brain, Thermometer, Droplets, Leaf, Zap, ArrowRight } from 'lucide-react';
import AnimatedNumber from '../components/AnimatedNumber';

const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.08, delayChildren: 0.15 } },
};

const fadeUp = {
  hidden: { opacity: 0, y: 30 },
  show: { opacity: 1, y: 0, transition: { type: 'spring', stiffness: 100, damping: 20 } },
};

const features = [
  {
    icon: Box, title: '3D Digital Twin',
    desc: 'Real-time 3D visualization of your Fluidized Bed Dryer with live colour-changing tea bed particles.',
    color: '#38bdf8',
  },
  {
    icon: Brain, title: 'RL Agent (PPO/SAC)',
    desc: 'Reinforcement Learning agent that outperforms PID controllers by optimizing fuel and quality simultaneously.',
    color: '#a78bfa',
  },
  {
    icon: BarChart3, title: 'Live Analytics',
    desc: 'Moisture curves, temperature profiles, enzyme kinetics, and CIELAB colour tracking in real time.',
    color: '#4ade80',
  },
  {
    icon: Zap, title: 'Sensor Fusion',
    desc: '8-channel e-Nose, 3-zone thermocouples, humidity, and colorimetry — all simulated with realistic noise.',
    color: '#fbbf24',
  },
];

function ParticleBg() {
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      {Array.from({ length: 20 }).map((_, i) => (
        <motion.div
          key={i}
          className="absolute w-1 h-1 rounded-full bg-sky-400/30"
          initial={{
            x: `${Math.random() * 100}%`,
            y: `${110}%`,
            opacity: 0,
          }}
          animate={{
            y: `-10%`,
            opacity: [0, 0.6, 0.6, 0],
            x: `${Math.random() * 100}%`,
          }}
          transition={{
            duration: 8 + Math.random() * 6,
            repeat: Infinity,
            delay: Math.random() * 5,
            ease: 'linear',
          }}
        />
      ))}
    </div>
  );
}

export default function HomePage({ setActiveTab, state }) {
  const moisture = state?.moisture != null ? (state.moisture * 100) : 70;
  const bedTemp = state?.bed_temp ?? 28;
  const enzyme = state?.enzyme_activity != null ? (state.enzyme_activity * 100) : 100;

  return (
    <motion.div
      key="home"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.4 }}
      className="h-full overflow-y-auto relative bg-scene"
    >
      <ParticleBg />

      <div className="relative z-10 max-w-5xl mx-auto px-6 py-10">
        {/* Hero */}
        <motion.div variants={container} initial="hidden" animate="show" className="mb-12">
          <motion.div variants={fadeUp} className="mb-2">
            <span className="text-xs uppercase tracking-[0.25em] text-sky-400 font-semibold">
              AI-Powered Tea Processing
            </span>
          </motion.div>

          <motion.h1 variants={fadeUp} className="text-5xl font-bold leading-tight mb-4">
            <span className="text-gradient">AuraSense</span>
            <br />
            <span className="text-white/90">Digital Twin Platform</span>
          </motion.h1>

          <motion.p variants={fadeUp} className="text-lg text-slate-400 max-w-2xl leading-relaxed mb-8">
            An AI-driven sensor fusion retrofit kit for legacy Fluidized Bed Dryers
            in Assam's tea industry. Replace reactive PID controllers with predictive
            RL agents to co-optimize&nbsp;
            <span className="text-sky-400">fuel consumption</span> and&nbsp;
            <span className="text-emerald-400">tea quality</span> in real time.
          </motion.p>

          <motion.div variants={fadeUp} className="flex gap-3">
            <motion.button
              whileHover={{ scale: 1.03, y: -1 }}
              whileTap={{ scale: 0.97 }}
              onClick={() => setActiveTab('twin')}
              className="flex items-center gap-2 px-6 py-3 rounded-2xl
                         bg-gradient-to-r from-sky-500 to-emerald-500
                         text-white font-semibold text-sm shadow-lg glow-sky
                         transition-shadow"
            >
              Launch Digital Twin <ArrowRight size={16} />
            </motion.button>
            <motion.button
              whileHover={{ scale: 1.03, y: -1 }}
              whileTap={{ scale: 0.97 }}
              onClick={() => setActiveTab('twin')}
              className="flex items-center gap-2 px-6 py-3 rounded-2xl
                         glass glass-hover text-slate-300 font-medium text-sm"
            >
              View Analytics <BarChart3 size={16} />
            </motion.button>
          </motion.div>
        </motion.div>

        {/* Live Stats Bar */}
        <motion.div
          variants={container} initial="hidden" animate="show"
          className="grid grid-cols-3 gap-3 mb-12"
        >
          {[
            { label: 'Moisture', value: moisture, unit: '%', icon: Droplets, color: '#38bdf8' },
            { label: 'Bed Temp', value: bedTemp, unit: '°C', icon: Thermometer, color: '#f97316' },
            { label: 'Enzyme', value: enzyme, unit: '%', icon: Leaf, color: '#a78bfa' },
          ].map((stat) => (
            <motion.div
              key={stat.label}
              variants={fadeUp}
              className="glass glass-hover p-4 flex items-center gap-4"
            >
              <div
                className="w-12 h-12 rounded-2xl flex items-center justify-center"
                style={{ background: `${stat.color}15` }}
              >
                <stat.icon size={22} style={{ color: stat.color }} />
              </div>
              <div>
                <div className="flex items-baseline gap-1">
                  <AnimatedNumber value={stat.value} decimals={1} className="text-2xl font-bold text-white" />
                  <span className="text-sm text-slate-400">{stat.unit}</span>
                </div>
                <span className="text-xs text-slate-500">{stat.label}</span>
              </div>
            </motion.div>
          ))}
        </motion.div>

        {/* Feature Cards */}
        <motion.div variants={container} initial="hidden" animate="show">
          <motion.h2 variants={fadeUp} className="text-sm uppercase tracking-[0.2em] text-slate-500 font-semibold mb-4">
            Platform Features
          </motion.h2>
          <div className="grid grid-cols-2 gap-3">
            {features.map((f, i) => (
              <motion.div
                key={f.title}
                variants={fadeUp}
                whileHover={{ scale: 1.02, y: -3 }}
                className="glass glass-hover p-5 cursor-default"
              >
                <div
                  className="w-10 h-10 rounded-xl flex items-center justify-center mb-3"
                  style={{ background: `${f.color}12` }}
                >
                  <f.icon size={20} style={{ color: f.color }} />
                </div>
                <h3 className="text-sm font-bold text-white mb-1">{f.title}</h3>
                <p className="text-xs text-slate-400 leading-relaxed">{f.desc}</p>
              </motion.div>
            ))}
          </div>
        </motion.div>

        {/* Architecture Diagram */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6, duration: 0.6 }}
          className="mt-12 glass p-6"
        >
          <h2 className="text-sm uppercase tracking-[0.2em] text-slate-500 font-semibold mb-4">
            System Architecture
          </h2>
          <div className="flex items-center justify-between gap-2 text-center">
            {[
              { label: 'Physics\nEngine', sub: 'Page Model · Arrhenius', color: '#38bdf8' },
              { label: 'Sensor\nFusion', sub: 'e-Nose · Color · Thermo', color: '#4ade80' },
              { label: 'RL Agent', sub: 'PPO / SAC · SB3', color: '#a78bfa' },
              { label: 'FastAPI', sub: 'REST + WebSocket', color: '#f97316' },
              { label: 'React\nFrontend', sub: 'R3F · Recharts', color: '#ec4899' },
            ].map((block, i) => (
              <div key={block.label} className="flex items-center gap-2">
                <motion.div
                  whileHover={{ scale: 1.05 }}
                  className="glass-sm p-4 min-w-[120px]"
                  style={{ borderColor: `${block.color}30` }}
                >
                  <div className="text-xs font-bold whitespace-pre-line" style={{ color: block.color }}>
                    {block.label}
                  </div>
                  <div className="text-[9px] text-slate-500 mt-1">{block.sub}</div>
                </motion.div>
                {i < 4 && (
                  <motion.div
                    animate={{ x: [0, 4, 0] }}
                    transition={{ duration: 1.5, repeat: Infinity }}
                    className="text-slate-600"
                  >
                    →
                  </motion.div>
                )}
              </div>
            ))}
          </div>
        </motion.div>

        <div className="h-8" />
      </div>
    </motion.div>
  );
}
