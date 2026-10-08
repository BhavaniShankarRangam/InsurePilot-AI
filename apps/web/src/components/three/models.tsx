"use client";

import { RoundedBox } from "@react-three/drei";
import type { ThreeElements } from "@react-three/fiber";

/** Stylized low-poly insurance objects built from primitives (no external assets to load). */
type G = ThreeElements["group"] & { color: string; emissive?: number };

function Mat({ color, emissive = 0.25 }: { color: string; emissive?: number }) {
  return <meshStandardMaterial color={color} emissive={color} emissiveIntensity={emissive} roughness={0.32} metalness={0.35} />;
}
function Glass() {
  return <meshPhysicalMaterial color="#ffffff" transmission={0.6} roughness={0.08} thickness={0.4} transparent opacity={0.7} />;
}

export function CarModel({ color, emissive, ...p }: G) {
  return (
    <group {...p}>
      <RoundedBox args={[1.4, 0.38, 0.72]} radius={0.12} position={[0, 0.22, 0]}><Mat color={color} emissive={emissive} /></RoundedBox>
      <RoundedBox args={[0.78, 0.32, 0.64]} radius={0.12} position={[-0.06, 0.52, 0]}><Glass /></RoundedBox>
      {[[-0.45, 0.38], [0.45, 0.38], [-0.45, -0.38], [0.45, -0.38]].map(([x, z], i) => (
        <mesh key={i} position={[x, 0.04, z]} rotation={[Math.PI / 2, 0, 0]}>
          <cylinderGeometry args={[0.16, 0.16, 0.12, 20]} />
          <meshStandardMaterial color="#1b1f2a" roughness={0.6} />
        </mesh>
      ))}
    </group>
  );
}

export function HouseModel({ color, emissive, ...p }: G) {
  return (
    <group {...p}>
      <RoundedBox args={[0.95, 0.7, 0.85]} radius={0.06} position={[0, 0.35, 0]}><Mat color={color} emissive={emissive} /></RoundedBox>
      <mesh position={[0, 0.95, 0]} rotation={[0, Math.PI / 4, 0]}>
        <coneGeometry args={[0.8, 0.55, 4]} />
        <meshStandardMaterial color="#e9ecf5" roughness={0.4} />
      </mesh>
      <mesh position={[0, 0.22, 0.43]}><boxGeometry args={[0.2, 0.36, 0.02]} /><meshStandardMaterial color="#1b1f2a" /></mesh>
    </group>
  );
}

export function HealthModel({ color, emissive, ...p }: G) {
  return (
    <group {...p}>
      <RoundedBox args={[0.32, 1, 0.32]} radius={0.08}><Mat color={color} emissive={emissive} /></RoundedBox>
      <RoundedBox args={[1, 0.32, 0.32]} radius={0.08}><Mat color={color} emissive={emissive} /></RoundedBox>
    </group>
  );
}

export function LifeModel({ color, emissive, ...p }: G) {
  return (
    <group {...p}>
      <mesh position={[0, 0.3, 0]}><sphereGeometry args={[0.62, 24, 12, 0, Math.PI * 2, 0, Math.PI / 2]} /><Mat color={color} emissive={emissive} /></mesh>
      <mesh position={[0, -0.15, 0]}><cylinderGeometry args={[0.03, 0.03, 0.9, 8]} /><meshStandardMaterial color="#e9ecf5" /></mesh>
    </group>
  );
}

export function PetModel({ color, emissive, ...p }: G) {
  return (
    <group {...p}>
      <mesh position={[0, -0.12, 0]} scale={[1, 0.85, 0.6]}><sphereGeometry args={[0.36, 24, 16]} /><Mat color={color} emissive={emissive} /></mesh>
      {[[-0.38, 0.28], [-0.14, 0.46], [0.14, 0.46], [0.38, 0.28]].map(([x, y], i) => (
        <mesh key={i} position={[x, y, 0]} scale={[1, 1, 0.6]}><sphereGeometry args={[0.13, 16, 12]} /><Mat color={color} emissive={emissive} /></mesh>
      ))}
    </group>
  );
}

export function PlaneModel({ color, emissive, ...p }: G) {
  return (
    <group {...p}>
      <mesh rotation={[0, 0, Math.PI / 2]}><capsuleGeometry args={[0.13, 1, 8, 16]} /><Mat color={color} emissive={emissive} /></mesh>
      <RoundedBox args={[0.32, 0.04, 1.3]} radius={0.02}><meshStandardMaterial color="#e9ecf5" /></RoundedBox>
      <RoundedBox args={[0.18, 0.3, 0.04]} radius={0.02} position={[-0.52, 0.18, 0]}><Mat color={color} emissive={emissive} /></RoundedBox>
    </group>
  );
}

export function BusinessModel({ color, emissive, ...p }: G) {
  return (
    <group {...p}>
      <RoundedBox args={[0.5, 1.1, 0.5]} radius={0.04} position={[-0.2, 0.55, 0]}><Mat color={color} emissive={emissive} /></RoundedBox>
      <RoundedBox args={[0.42, 0.7, 0.42]} radius={0.04} position={[0.3, 0.35, 0]}><Glass /></RoundedBox>
    </group>
  );
}

export function DocumentModel({ color, emissive, ...p }: G) {
  return (
    <group {...p}>
      <RoundedBox args={[0.78, 1, 0.05]} radius={0.03}><meshStandardMaterial color="#f4f6fb" roughness={0.5} /></RoundedBox>
      {[0.28, 0.12, -0.04, -0.2].map((y, i) => (
        <mesh key={i} position={[-0.04 + (i === 3 ? -0.1 : 0), y, 0.03]}><boxGeometry args={[i === 3 ? 0.36 : 0.56, 0.05, 0.01]} /><Mat color={color} emissive={emissive} /></mesh>
      ))}
    </group>
  );
}

export function PhoneModel({ color, emissive, ...p }: G) {
  return (
    <group {...p}>
      <RoundedBox args={[0.56, 1.08, 0.07]} radius={0.08}><meshStandardMaterial color="#141823" metalness={0.6} roughness={0.25} /></RoundedBox>
      <RoundedBox args={[0.48, 0.96, 0.01]} radius={0.06} position={[0, 0, 0.04]}><Mat color={color} emissive={emissive ?? 0.6} /></RoundedBox>
    </group>
  );
}

export function ClaimModel({ color, emissive, ...p }: G) {
  return (
    <group {...p}>
      <DocumentModel color={color} emissive={emissive} />
      <mesh position={[0.28, -0.32, 0.06]}><sphereGeometry args={[0.18, 20, 16]} /><meshStandardMaterial color="#3ddbbd" emissive="#3ddbbd" emissiveIntensity={0.6} /></mesh>
    </group>
  );
}

export const CATEGORY_MODEL = {
  auto: CarModel,
  home: HouseModel,
  renters: HouseModel,
  health: HealthModel,
  life: LifeModel,
  pet: PetModel,
  travel: PlaneModel,
  commercial: BusinessModel,
} as const;
