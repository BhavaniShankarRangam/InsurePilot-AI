"use client";

import { AdaptiveDpr, Float, Line, MeshDistortMaterial, Sparkles } from "@react-three/drei";
import { Canvas, useFrame } from "@react-three/fiber";
import * as React from "react";
import * as THREE from "three";
import { CarModel, ClaimModel, DocumentModel, HealthModel, HouseModel, PhoneModel } from "./models";

const OBJECTS = [
  { Model: CarModel, pos: [-3.3, 1.1, -0.4], color: "#5b8cff", rot: [0.2, 0.6, 0] },
  { Model: HouseModel, pos: [3.1, 1.5, -0.8], color: "#22b8cf", rot: [0.1, -0.5, 0] },
  { Model: HealthModel, pos: [3.5, -1.3, 0.2], color: "#2ec4a6", rot: [0.3, 0.4, 0.2], scale: 0.8 },
  { Model: DocumentModel, pos: [-3.0, -1.5, 0.4], color: "#8b7bff", rot: [0.1, 0.5, -0.15] },
  { Model: PhoneModel, pos: [0.4, 2.7, -1.6], color: "#3cc8f5", rot: [0.2, -0.3, 0.1], scale: 0.85 },
  { Model: ClaimModel, pos: [0.2, -2.6, -0.8], color: "#f2a33a", rot: [-0.1, 0.3, 0.1], scale: 0.9 },
] as const;

function Rig() {
  const group = React.useRef<THREE.Group>(null);
  useFrame((state, dt) => {
    if (!group.current) return;
    const { x, y } = state.pointer;
    group.current.rotation.y = THREE.MathUtils.damp(group.current.rotation.y, x * 0.25, 3, dt);
    group.current.rotation.x = THREE.MathUtils.damp(group.current.rotation.x, -y * 0.15, 3, dt);
  });
  return (
    <group ref={group}>
      <AIOrb />
      {OBJECTS.map(({ Model, pos, color, rot, ...rest }, i) => (
        <React.Fragment key={i}>
          <Beam to={new THREE.Vector3(...pos)} color={color} />
          <Float speed={1.2 + i * 0.15} rotationIntensity={0.4} floatIntensity={0.9}>
            <Model color={color} position={pos as unknown as THREE.Vector3Tuple} rotation={rot as unknown as THREE.Vector3Tuple} scale={"scale" in rest ? rest.scale : 1} />
          </Float>
        </React.Fragment>
      ))}
    </group>
  );
}

function AIOrb() {
  const ref = React.useRef<THREE.Mesh>(null);
  useFrame((s) => {
    if (ref.current) ref.current.rotation.y = s.clock.elapsedTime * 0.25;
  });
  return (
    <group>
      <mesh ref={ref}>
        <sphereGeometry args={[1.05, 64, 64]} />
        <MeshDistortMaterial color="#7c6cff" emissive="#4b3fff" emissiveIntensity={0.7} roughness={0.1} metalness={0.25} distort={0.32} speed={1.6} />
      </mesh>
      <mesh scale={1.45}>
        <sphereGeometry args={[1, 32, 32]} />
        <meshBasicMaterial color="#3cc8f5" transparent opacity={0.07} />
      </mesh>
      <pointLight intensity={30} color="#8b7bff" distance={9} />
    </group>
  );
}

function Beam({ to, color }: { to: THREE.Vector3; color: string }) {
  const ref = React.useRef<{ material: { dashOffset: number } } | null>(null);
  const pts = React.useMemo(() => {
    const mid = to.clone().multiplyScalar(0.5).add(new THREE.Vector3(0, 0.6, 0.6));
    return new THREE.QuadraticBezierCurve3(new THREE.Vector3(0, 0, 0), mid, to).getPoints(40);
  }, [to]);
  useFrame((_, dt) => {
    if (ref.current) ref.current.material.dashOffset -= dt * 0.8;
  });
  return <Line ref={ref as never} points={pts} color={color} lineWidth={1.4} dashed dashSize={0.18} gapSize={0.14} transparent opacity={0.7} />;
}

export default function HeroScene() {
  return (
    <Canvas camera={{ position: [0, 0, 9], fov: 45 }} dpr={[1, 1.75]} gl={{ antialias: true, alpha: true, powerPreference: "high-performance" }}>
      <AdaptiveDpr pixelated />
      <ambientLight intensity={0.55} />
      <directionalLight position={[4, 6, 5]} intensity={1.5} />
      <Sparkles count={70} scale={11} size={2} speed={0.3} color="#a5b4ff" opacity={0.7} />
      <Rig />
    </Canvas>
  );
}
