/**
 * App.jsx - Root shell with Sidebar navigation + animated page switching.
 */

import { useState, useCallback } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { useWebSocket } from "./hooks/useWebSocket";
import { useCoPilot } from "./hooks/useCoPilot";
import Sidebar from "./components/Navigation/Sidebar";
import HomePage from "./pages/HomePage";
import TwinPage from "./pages/TwinPage";
import ControlsPage from "./pages/ControlsPage";
import BenchmarkPage from "./pages/BenchmarkPage";

const pageVariants = {
  initial:  { opacity: 0, y: 24, scale: 0.98 },
  animate:  { opacity: 1, y: 0,  scale: 1 },
  exit:     { opacity: 0, y: -16, scale: 0.98 },
};

const pageTransition = { duration: 0.35, ease: [0.4, 0, 0.2, 1] };

export default function App() {
  const [activeTab, setActiveTab] = useState("home");
  const { state, history, status, simStatus, sendCmd, clearHistory } = useWebSocket();
  const { alerts, clearAlerts } = useCoPilot(state);

  const navigate = useCallback((tab) => setActiveTab(tab), []);

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#060b18]">
      {/* Left sidebar */}
      <Sidebar activeTab={activeTab} setActiveTab={navigate} wsStatus={status} />

      {/* Page area */}
      <main className="flex-1 min-w-0 overflow-hidden relative">
        <AnimatePresence mode="wait">
          {activeTab === "home" && (
            <motion.div
              key="home"
              className="absolute inset-0 overflow-y-auto overflow-x-hidden"
              variants={pageVariants}
              initial="initial"
              animate="animate"
              exit="exit"
              transition={pageTransition}
            >
              <HomePage navigate={navigate} state={state} />
            </motion.div>
          )}

          {activeTab === "twin" && (
            <motion.div
              key="twin"
              className="absolute inset-0"
              variants={pageVariants}
              initial="initial"
              animate="animate"
              exit="exit"
              transition={pageTransition}
            >
              <TwinPage state={state} simStatus={simStatus} sendCmd={sendCmd} history={history} alerts={alerts} clearAlerts={clearAlerts} />
            </motion.div>
          )}

          {activeTab === "controls" && (
            <motion.div
              key="controls"
              className="absolute inset-0 overflow-y-auto overflow-x-hidden"
              variants={pageVariants}
              initial="initial"
              animate="animate"
              exit="exit"
              transition={pageTransition}
            >
              <ControlsPage state={state} simStatus={simStatus} sendCmd={sendCmd} />
            </motion.div>
          )}

          {activeTab === "benchmark" && (
            <motion.div
              key="benchmark"
              className="absolute inset-0 overflow-y-auto overflow-x-hidden"
              variants={pageVariants}
              initial="initial"
              animate="animate"
              exit="exit"
              transition={pageTransition}
            >
              <BenchmarkPage state={state} />
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  );
}
