/**
 * DryerModel.jsx - Enhanced 3D Fluidized Bed Dryer model.
 *
 * Geometry: detailed cylindrical chamber with structural rings, flanges,
 * inlet plenum, exhaust stack, tea-bed particles with per-particle colour,
 * heat-haze volumetric effect, steam exhaust, airflow vortex, and
 * 3D annotations.
 */

import { useRef, useMemo } from "react";
import { useFrame } from "@react-three/fiber";
import { Float, Text } from "@react-three/drei";
import * as THREE from "three";

/* -------- Tea Bed Particles (instanced, colour-shifting) -------- */
function TeaBed({ color = "#7e7f51", moisture = 0.7, count = 500 }) {
  const meshRef = useRef();
  const dummy = useMemo(() => new THREE.Object3D(), []);
  const col = useMemo(() => new THREE.Color(color), [color]);

  const particles = useMemo(() => {
    const arr = [];
    for (let i = 0; i < count; i++) {
      const angle = Math.random() * Math.PI * 2;
      const r = Math.sqrt(Math.random()) * 1.65;
      arr.push({
        x: Math.cos(angle) * r,
        z: Math.sin(angle) * r,
        y: -0.6 + Math.random() * 0.9,
        phase: Math.random() * Math.PI * 2,
        size: 0.04 + Math.random() * 0.04,
      });
    }
    return arr;
  }, [count]);

  useFrame(() => {
    if (!meshRef.current) return;
    const speed = 0.4 + (1 - moisture) * 3;
    const t = performance.now() * 0.001 * speed;
    particles.forEach((p, i) => {
      const bounce = Math.sin(t * 1.3 + p.phase + i * 0.1) * (0.04 + (1 - moisture) * 0.1);
      dummy.position.set(
        p.x + Math.sin(t * 0.5 + p.phase) * 0.02,
        p.y + bounce,
        p.z + Math.cos(t * 0.5 + p.phase) * 0.02
      );
      const s = p.size * (0.9 + Math.sin(t + i) * 0.1);
      dummy.scale.setScalar(s);
      dummy.rotation.set(t * 0.3 + i, t * 0.2, 0);
      dummy.updateMatrix();
      meshRef.current.setMatrixAt(i, dummy.matrix);
    });
    meshRef.current.instanceMatrix.needsUpdate = true;
    meshRef.current.material.color.lerp(col, 0.08);
  });

  return (
    <instancedMesh ref={meshRef} args={[null, null, count]} castShadow>
      <icosahedronGeometry args={[1, 0]} />
      <meshStandardMaterial color={color} roughness={0.85} metalness={0.05} />
    </instancedMesh>
  );
}

/* -------- Heat Haze (volumetric rising particles) -------- */
function HeatHaze({ temperature = 80 }) {
  const ref = useRef();
  const count = 120;
  const dummy = useMemo(() => new THREE.Object3D(), []);

  const particles = useMemo(() => {
    const arr = [];
    for (let i = 0; i < count; i++) {
      const angle = Math.random() * Math.PI * 2;
      const r = Math.random() * 1.5;
      arr.push({
        x: Math.cos(angle) * r,
        z: Math.sin(angle) * r,
        speed: 0.2 + Math.random() * 0.6,
        phase: Math.random() * Math.PI * 2,
        wobble: 0.1 + Math.random() * 0.3,
      });
    }
    return arr;
  }, [count]);

  useFrame(() => {
    if (!ref.current) return;
    const intensity = Math.min(1, Math.max(0, (temperature - 50) / 80));
    const t = performance.now() * 0.001;
    particles.forEach((p, i) => {
      const y = ((t * p.speed + p.phase) % 3.5) - 0.5;
      const fade = 1 - y / 3.5;
      dummy.position.set(
        p.x + Math.sin(t * p.wobble + p.phase) * 0.25,
        y,
        p.z + Math.cos(t * p.wobble + p.phase) * 0.25
      );
      const s = (0.015 + intensity * 0.03) * fade;
      dummy.scale.setScalar(Math.max(0.001, s));
      dummy.updateMatrix();
      ref.current.setMatrixAt(i, dummy.matrix);
    });
    ref.current.instanceMatrix.needsUpdate = true;
  });

  const opacity = Math.min(0.5, (temperature - 50) / 120);
  return (
    <instancedMesh ref={ref} args={[null, null, count]}>
      <sphereGeometry args={[1, 6, 6]} />
      <meshBasicMaterial color="#ffaa44" transparent opacity={opacity} depthWrite={false} />
    </instancedMesh>
  );
}

/* -------- Steam from Exhaust -------- */
function SteamExhaust({ temperature = 80, moisture = 0.7 }) {
  const ref = useRef();
  const count = 60;
  const dummy = useMemo(() => new THREE.Object3D(), []);

  const particles = useMemo(() => {
    const arr = [];
    for (let i = 0; i < count; i++) {
      arr.push({
        phase: Math.random() * Math.PI * 2,
        speed: 0.3 + Math.random() * 0.5,
        drift: (Math.random() - 0.5) * 0.5,
      });
    }
    return arr;
  }, [count]);

  useFrame(() => {
    if (!ref.current) return;
    const t = performance.now() * 0.001;
    particles.forEach((p, i) => {
      const life = ((t * p.speed + p.phase) % 3);
      const y = life * 1.2;
      const spread = life * 0.4;
      dummy.position.set(
        Math.sin(p.phase) * spread + p.drift * life,
        y,
        Math.cos(p.phase) * spread
      );
      const s = (0.03 + life * 0.06) * moisture;
      dummy.scale.setScalar(Math.max(0.001, s));
      dummy.updateMatrix();
      ref.current.setMatrixAt(i, dummy.matrix);
    });
    ref.current.instanceMatrix.needsUpdate = true;
  });

  return (
    <group position={[0, 3.3, 0]}>
      <instancedMesh ref={ref} args={[null, null, count]}>
        <sphereGeometry args={[1, 5, 5]} />
        <meshBasicMaterial color="#aaccee" transparent opacity={0.15} depthWrite={false} />
      </instancedMesh>
    </group>
  );
}

/* -------- Structural Ring (decorative) -------- */
function StructuralRing({ y, radius = 2.05, color = "#475569" }) {
  return (
    <mesh position={[0, y, 0]} rotation={[Math.PI / 2, 0, 0]}>
      <torusGeometry args={[radius, 0.035, 8, 48]} />
      <meshStandardMaterial color={color} metalness={0.9} roughness={0.3} />
    </mesh>
  );
}

/* -------- Flange bolts around a ring -------- */
function FlangeRing({ y, radius = 2.1, boltCount = 12 }) {
  return (
    <group position={[0, y, 0]}>
      {Array.from({ length: boltCount }).map((_, i) => {
        const angle = (i / boltCount) * Math.PI * 2;
        return (
          <mesh key={i} position={[Math.cos(angle) * radius, 0, Math.sin(angle) * radius]}>
            <sphereGeometry args={[0.04, 6, 6]} />
            <meshStandardMaterial color="#94a3b8" metalness={0.95} roughness={0.2} />
          </mesh>
        );
      })}
    </group>
  );
}

/* -------- Temperature Glow Ring -------- */
function TempRing({ bedTemp }) {
  const ringColor = bedTemp > 100 ? "#ef4444" : bedTemp > 75 ? "#f97316" : bedTemp > 50 ? "#fbbf24" : "#60a5fa";
  const emissiveIntensity = 0.3 + Math.min(1, (bedTemp - 40) / 80) * 0.7;

  return (
    <mesh position={[0, -0.5, 0]} rotation={[Math.PI / 2, 0, 0]}>
      <torusGeometry args={[2.08, 0.04, 12, 48]} />
      <meshStandardMaterial
        color={ringColor}
        emissive={ringColor}
        emissiveIntensity={emissiveIntensity}
        transparent
        opacity={0.9}
      />
    </mesh>
  );
}

/* -------- 3D Label -------- */
function Label3D({ position, text, color = "#94a3b8" }) {
  return (
    <Float speed={1} rotationIntensity={0} floatIntensity={0.3}>
      <Text
        position={position}
        fontSize={0.15}
        color={color}
        anchorX="left"
        anchorY="middle"
        font={undefined}
      >
        {text}
      </Text>
    </Float>
  );
}

/* ======== MAIN DRYER ASSEMBLY ======== */
export default function DryerModel({ state }) {
  const groupRef = useRef();
  const color = state?.color_hex ?? "#7e7f51";
  const moisture = state?.moisture ?? 0.7;
  const bedTemp = state?.bed_temp ?? 25;
  const airflow = state?.airflow ?? 0.6;

  return (
    <group ref={groupRef}>
      {/* --- Chamber body (outer cylinder, semi-transparent) --- */}
      <mesh position={[0, 0.5, 0]} castShadow>
        <cylinderGeometry args={[2, 2, 3.8, 48, 1, true]} />
        <meshPhysicalMaterial
          color="#1e3a5f"
          metalness={0.85}
          roughness={0.25}
          transparent
          opacity={0.25}
          side={THREE.DoubleSide}
          envMapIntensity={0.5}
        />
      </mesh>

      {/* Inner glass cylinder (smaller, more opaque) */}
      <mesh position={[0, 0.5, 0]}>
        <cylinderGeometry args={[1.92, 1.92, 3.6, 48, 1, true]} />
        <meshPhysicalMaterial
          color="#0f2744"
          metalness={0.3}
          roughness={0.5}
          transparent
          opacity={0.12}
          side={THREE.BackSide}
        />
      </mesh>

      {/* --- Top flange + lid --- */}
      <mesh position={[0, 2.4, 0]}>
        <cylinderGeometry args={[2.15, 2.15, 0.12, 48]} />
        <meshStandardMaterial color="#334155" metalness={0.9} roughness={0.25} />
      </mesh>
      <mesh position={[0, 2.5, 0]}>
        <cylinderGeometry args={[2.0, 2.0, 0.08, 48]} />
        <meshPhysicalMaterial color="#1e293b" metalness={0.8} roughness={0.3} transparent opacity={0.6} />
      </mesh>
      <FlangeRing y={2.4} />

      {/* --- Bottom distributor plate --- */}
      <mesh position={[0, -1.4, 0]}>
        <cylinderGeometry args={[2.15, 2.15, 0.15, 48]} />
        <meshStandardMaterial color="#475569" metalness={0.85} roughness={0.3} />
      </mesh>
      {/* Perforated look - ring of holes */}
      <mesh position={[0, -1.35, 0]}>
        <cylinderGeometry args={[1.8, 1.8, 0.06, 48]} />
        <meshStandardMaterial color="#334155" metalness={0.7} roughness={0.4} wireframe />
      </mesh>
      <FlangeRing y={-1.4} />

      {/* --- Structural rings --- */}
      <StructuralRing y={0.0} />
      <StructuralRing y={1.2} />
      <StructuralRing y={-0.8} />

      {/* --- Inlet plenum (below distributor) --- */}
      <mesh position={[0, -2.1, 0]}>
        <cylinderGeometry args={[0.7, 0.9, 1.2, 24]} />
        <meshStandardMaterial color="#334155" metalness={0.75} roughness={0.35} />
      </mesh>
      {/* Inlet pipe */}
      <mesh position={[0, -2.8, 0]}>
        <cylinderGeometry args={[0.4, 0.5, 0.3, 16]} />
        <meshStandardMaterial color="#475569" metalness={0.8} roughness={0.3} />
      </mesh>

      {/* --- Exhaust stack --- */}
      <mesh position={[0, 3.0, 0]}>
        <cylinderGeometry args={[0.55, 0.45, 1.0, 24]} />
        <meshStandardMaterial color="#475569" metalness={0.75} roughness={0.35} />
      </mesh>
      <mesh position={[0, 3.55, 0]}>
        <cylinderGeometry args={[0.6, 0.55, 0.1, 24]} />
        <meshStandardMaterial color="#334155" metalness={0.9} roughness={0.25} />
      </mesh>

      {/* --- Support legs --- */}
      {[0, 1, 2, 3].map((i) => {
        const angle = (i / 4) * Math.PI * 2 + Math.PI / 4;
        const x = Math.cos(angle) * 1.8;
        const z = Math.sin(angle) * 1.8;
        return (
          <group key={`leg-${i}`}>
            <mesh position={[x, -2.5, z]}>
              <cylinderGeometry args={[0.06, 0.08, 2.0, 8]} />
              <meshStandardMaterial color="#475569" metalness={0.8} roughness={0.3} />
            </mesh>
            <mesh position={[x, -3.5, z]}>
              <cylinderGeometry args={[0.15, 0.15, 0.04, 8]} />
              <meshStandardMaterial color="#64748b" metalness={0.7} roughness={0.4} />
            </mesh>
          </group>
        );
      })}

      {/* --- Temperature glow ring --- */}
      <TempRing bedTemp={bedTemp} />

      {/* --- Tea bed --- */}
      <group position={[0, -0.2, 0]}>
        <TeaBed color={color} moisture={moisture} count={500} />
      </group>

      {/* --- Heat haze --- */}
      <group position={[0, 0.8, 0]}>
        <HeatHaze temperature={bedTemp} />
      </group>

      {/* --- Steam exhaust --- */}
      <SteamExhaust temperature={bedTemp} moisture={moisture} />

      {/* --- Labels --- */}
      <Label3D position={[2.5, 2.5, 0]} text={`Exhaust ${bedTemp > 50 ? "" : ""}`} color="#64748b" />
      <Label3D position={[2.5, 0.0, 0]} text={`Bed ${bedTemp.toFixed(0)}C`} color={bedTemp > 90 ? "#f97316" : "#64748b"} />
      <Label3D position={[2.5, -2.0, 0]} text={`Inlet ${(airflow * 100).toFixed(0)}%`} color="#60a5fa" />
    </group>
  );
}
