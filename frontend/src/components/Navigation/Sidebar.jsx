/**
 * Sidebar.jsx — Left-side navigation with animated tab indicators.
 *
 * Tabs: Home, Digital Twin, Analytics, Controls
 * Features: animated active indicator, icon + label, glassmorphism
 */

import { motion } from 'framer-motion';
import { Home, Box, SlidersHorizontal, Wifi, WifiOff } from 'lucide-react';

const tabs = [
  { id: 'home',    label: 'Home',         icon: Home },
  { id: 'twin',    label: 'Digital Twin',  icon: Box },
  { id: 'controls', label: 'Controls',    icon: SlidersHorizontal },
];

export default function Sidebar({ activeTab, setActiveTab, wsStatus }) {
  const connected = wsStatus === 'connected';

  return (
    <motion.nav
      initial={{ x: -80, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      transition={{ type: 'spring', stiffness: 200, damping: 25 }}
      className="w-[72px] h-full flex flex-col items-center py-4 gap-2 glass shrink-0"
      style={{ borderRadius: '0 20px 20px 0', borderLeft: 'none' }}
    >
      {/* Logo */}
      <motion.div
        whileHover={{ scale: 1.1, rotate: 5 }}
        whileTap={{ scale: 0.95 }}
        className="w-10 h-10 rounded-xl bg-gradient-to-br from-sky-400 to-emerald-400
                   flex items-center justify-center text-white font-bold text-lg
                   shadow-lg cursor-pointer mb-4 glow-sky"
        onClick={() => setActiveTab('home')}
      >
        A
      </motion.div>

      {/* Nav items */}
      <div className="flex-1 flex flex-col gap-1 w-full px-2">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;

          return (
            <motion.button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              className={`relative w-full aspect-square rounded-2xl flex flex-col items-center
                         justify-center gap-0.5 transition-colors duration-200 group
                         ${isActive
                           ? 'text-sky-400'
                           : 'text-slate-500 hover:text-slate-300'
                         }`}
            >
              {/* Active background glow */}
              {isActive && (
                <motion.div
                  layoutId="nav-active"
                  className="absolute inset-0 rounded-2xl bg-sky-500/10 border border-sky-500/20"
                  transition={{ type: 'spring', stiffness: 350, damping: 30 }}
                />
              )}
              <Icon size={20} className="relative z-10" />
              <span className="text-[8px] font-medium relative z-10 tracking-wide">
                {tab.label}
              </span>
            </motion.button>
          );
        })}
      </div>

      {/* Connection status */}
      <motion.div
        animate={{ opacity: connected ? 1 : 0.5 }}
        className="flex flex-col items-center gap-1"
      >
        {connected ? (
          <Wifi size={14} className="text-emerald-400" />
        ) : (
          <WifiOff size={14} className="text-red-400" />
        )}
        <span className="text-[7px] text-slate-500">
          {connected ? 'LIVE' : 'OFFLINE'}
        </span>
      </motion.div>
    </motion.nav>
  );
}
