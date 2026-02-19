/**
 * Scene3D.jsx - Enhanced 3D viewport with better lighting,
 * grid floor, contact shadows, and floating HUD overlay.
 */

import { Suspense } from "react";
import { Canvas } from "@react-three/fiber";
import {
  OrbitControls,
  Environment,
  PerspectiveCamera,
  Html,
  ContactShadows,
  Grid,
} from "@react-three/drei";
import { motion } from "framer-motion";
import DryerModel from "./DryerModel";

function Loader() {
  return (
    <Html center>
      <div className="text-sky-400 text-sm animate-pulse">Loading 3D Scene...</div>
    </Html>
  );
}

export default function Scene3D({ state, compact = false }) {
  return (
    <div className="w-full h-full relative">
      <Canvas
        shadows
        dpr={[1, 2]}
        gl={{ antialias: true, alpha: true, powerPreference: "high-performance" }}
        style={{ background: "transparent" }}
      >
        <PerspectiveCamera
          makeDefault
          position={compact ? [6, 4, 6] : [7, 5, 7]}
          fov={40}
        />
        <OrbitControls
          enablePan
          enableZoom
          minDistance={4}
          maxDistance={18}
          autoRotate
          autoRotateSpeed={0.4}
          enableDamping
          dampingFactor={0.05}
          maxPolarAngle={Math.PI / 1.8}
        />

        {/* Lighting */}
        <ambientLight intensity={0.2} />
        <directionalLight
          position={[6, 10, 5]}
          intensity={1.5}
          castShadow
          shadow-mapSize={[2048, 2048]}
          shadow-camera-far={30}
          shadow-bias={-0.0001}
        />
        <pointLight position={[-4, 3, -4]} intensity={0.3} color="#38bdf8" />
        <pointLight position={[3, -1, 3]} intensity={0.2} color="#f97316" />
        <spotLight
          position={[0, 8, 0]}
          angle={0.3}
          penumbra={0.8}
          intensity={0.5}
          color="#ffffff"
        />
        <Environment preset="night" background={false} />

        {/* Dryer model */}
        <Suspense fallback={<Loader />}>
          <DryerModel state={state} />
        </Suspense>

        {/* Floor */}
        <ContactShadows
          position={[0, -3.55, 0]}
          opacity={0.4}
          scale={20}
          blur={2}
          far={6}
        />
        <Grid
          position={[0, -3.55, 0]}
          args={[30, 30]}
          cellSize={0.5}
          cellThickness={0.3}
          cellColor="#1e3a5f"
          sectionSize={2}
          sectionThickness={0.8}
          sectionColor="#0ea5e9"
          fadeDistance={15}
          fadeStrength={1.5}
          infiniteGrid
        />
      </Canvas>

      {/* Floating HUD overlay */}
      {state && !compact && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="absolute bottom-4 left-4 right-4 flex gap-2"
        >
          {[
            { label: "Time", value: `${state.time?.toFixed(1)} min`, color: "#94a3b8" },
            { label: "Moisture", value: `${(state.moisture * 100).toFixed(1)}%`, color: "#38bdf8" },
            { label: "Bed Temp", value: `${state.bed_temp?.toFixed(0)}C`, color: "#f97316" },
            { label: "Color", hex: state.color_hex },
          ].map((item) => (
            <div key={item.label} className="glass-sm px-3 py-1.5 flex items-center gap-2 text-xs">
              {item.hex ? (
                <>
                  <div className="w-4 h-4 rounded-full border border-white/20"
                    style={{ background: item.hex, transition: "background 0.5s" }} />
                  <span className="text-slate-400">{item.label}</span>
                </>
              ) : (
                <>
                  <span className="text-slate-500">{item.label}</span>
                  <span className="font-mono font-semibold" style={{ color: item.color }}>
                    {item.value}
                  </span>
                </>
              )}
            </div>
          ))}
        </motion.div>
      )}

      {/* Live badge */}
      {state && (
        <div className="absolute top-3 left-3 glass-sm px-2.5 py-1 flex items-center gap-1.5 text-xs">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span className="text-slate-400">Live</span>
        </div>
      )}
    </div>
  );
}
