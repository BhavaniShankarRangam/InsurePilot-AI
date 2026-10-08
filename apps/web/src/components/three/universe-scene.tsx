"use client";

import { AdaptiveDpr, Float, Line, OrbitControls, Sparkles, Stars, useCursor } from "@react-three/drei";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import * as React from "react";
import * as THREE from "three";
import { CATEGORY_META } from "@/lib/categories";
import type { Category, GraphData, GraphNode } from "@/lib/types";
import { money } from "@/lib/utils";
import { CATEGORY_MODEL } from "./models";

const STATUS_COLOR: Record<string, string> = { ok: "#3ddbbd", review: "#f5b544", attention: "#ff6b84", inactive: "#737b8f" };

interface Placed { node: GraphNode; pos: THREE.Vector3; parent?: string }

function layout(data: GraphData): Placed[] {
  const placed: Placed[] = [];
  const user = data.nodes.find((n) => n.type === "user");
  if (user) placed.push({ node: user, pos: new THREE.Vector3(0, 0, 0) });
  const cats = data.nodes.filter((n) => n.type === "category");
  cats.forEach((c, i) => {
    const a = (i / cats.length) * Math.PI * 2;
    placed.push({ node: c, pos: new THREE.Vector3(Math.cos(a) * 5.2, Math.sin(i * 1.7) * 0.9, Math.sin(a) * 5.2) });
  });
  // Claims and providers orbit just outside their category.
  const byPolicyCat = new Map<string, string>();
  data.links.filter((l) => l.kind === "insured_by").forEach((l) => byPolicyCat.set(l.target, l.source));
  const children = data.nodes.filter((n) => n.type === "claim" || n.type === "provider");
  const perCat = new Map<string, number>();
  children.forEach((n) => {
    const link = data.links.find((l) => l.target === n.id);
    const catId = link ? byPolicyCat.get(link.source) : undefined;
    const parent = placed.find((p) => p.node.id === catId);
    if (!parent) return;
    const k = perCat.get(catId!) ?? 0;
    perCat.set(catId!, k + 1);
    const dir = parent.pos.clone().normalize();
    const side = new THREE.Vector3(-dir.z, 0, dir.x);
    placed.push({ node: n, parent: catId, pos: parent.pos.clone().add(dir.multiplyScalar(1.9)).add(side.multiplyScalar((k - 0.5) * 1.3)).add(new THREE.Vector3(0, 0.9 - k * 0.8, 0)) });
  });
  return placed;
}

function CameraRig({ target }: { target: THREE.Vector3 | null }) {
  const { camera } = useThree();
  const look = React.useRef(new THREE.Vector3());
  useFrame((_, dt) => {
    if (!target) return;
    const dest = target.clone().add(target.clone().normalize().multiplyScalar(3.2)).add(new THREE.Vector3(0, 1.4, 0));
    camera.position.lerp(dest, 1 - Math.pow(0.02, dt));
    look.current.lerp(target, 1 - Math.pow(0.02, dt));
    camera.lookAt(look.current);
  });
  return null;
}

function Path({ from, to, color, active }: { from: THREE.Vector3; to: THREE.Vector3; color: string; active: boolean }) {
  const ref = React.useRef<{ material: { dashOffset: number } } | null>(null);
  const mid = from.clone().lerp(to, 0.5).add(new THREE.Vector3(0, 0.8, 0));
  const pts = new THREE.QuadraticBezierCurve3(from, mid, to).getPoints(32);
  useFrame((_, dt) => {
    if (ref.current) ref.current.material.dashOffset -= dt * (active ? 1.2 : 0.35);
  });
  return (
    <Line
      ref={ref as never}
      points={pts}
      color={color}
      lineWidth={active ? 2.4 : 1.2}
      dashed
      dashSize={0.25}
      gapSize={0.18}
      transparent
      opacity={active ? 0.95 : 0.45}
    />
  );
}

function NodeMesh({ p, hovered, onHover, onSelect }: { p: Placed; hovered: boolean; onHover: (id: string | null) => void; onSelect: (p: Placed) => void }) {
  const n = p.node;
  const cat = n.category as Category | undefined;
  const color = cat ? CATEGORY_META[cat]?.hue ?? "#8b7bff" : n.type === "user" ? "#8b7bff" : STATUS_COLOR[n.status] ?? "#6ea8ff";
  const Model = n.type === "category" && cat ? CATEGORY_MODEL[cat] : null;
  const ref = React.useRef<THREE.Group>(null);
  useCursor(hovered);
  useFrame((_, dt) => {
    if (!ref.current) return;
    const s = hovered ? 1.18 : 1;
    ref.current.scale.lerp(new THREE.Vector3(s, s, s), 1 - Math.pow(0.001, dt));
    if (Model) ref.current.rotation.y += dt * (hovered ? 0.9 : 0.25);
  });

  return (
    <group position={p.pos}>
      <Float speed={1.4} rotationIntensity={0.15} floatIntensity={0.5}>
        <group
          ref={ref}
          onPointerOver={(e) => { e.stopPropagation(); onHover(n.id); }}
          onPointerOut={() => onHover(null)}
          onClick={(e) => { e.stopPropagation(); onSelect(p); }}
        >
          {n.type === "user" ? (
            <mesh>
              <icosahedronGeometry args={[0.9, 6]} />
              <meshPhysicalMaterial color="#8b7bff" emissive="#5b5bf6" emissiveIntensity={0.9} roughness={0.15} metalness={0.2} clearcoat={1} />
            </mesh>
          ) : Model ? (
            <Model color={color} emissive={hovered ? 0.7 : 0.28} position={[0, -0.3, 0]} />
          ) : (
            <mesh>
              <sphereGeometry args={[0.2, 24, 16]} />
              <meshStandardMaterial color={color} emissive={color} emissiveIntensity={hovered ? 1 : 0.5} />
            </mesh>
          )}
          {/* status halo */}
          {n.type !== "user" && n.status !== "ok" && (
            <mesh rotation={[Math.PI / 2, 0, 0]} position={[0, -0.75, 0]}>
              <ringGeometry args={[0.7, 0.78, 48]} />
              <meshBasicMaterial color={STATUS_COLOR[n.status]} transparent opacity={0.8} side={THREE.DoubleSide} />
            </mesh>
          )}
        </group>
      </Float>
    </group>
  );
}

/** Interactive 3D Insurance Universe / Digital Twin. */
export default function UniverseScene({ data, onNavigate, immersive }: { data: GraphData; onNavigate: (link: string) => void; immersive?: boolean }) {
  const placed = React.useMemo(() => layout(data), [data]);
  const [hover, setHover] = React.useState<string | null>(null);
  const [target, setTarget] = React.useState<THREE.Vector3 | null>(null);
  const byId = React.useMemo(() => new Map(placed.map((p) => [p.node.id, p])), [placed]);

  const related = React.useMemo(() => {
    if (!hover) return new Set<string>();
    const s = new Set<string>([hover]);
    data.links.forEach((l) => {
      if (l.source === hover) s.add(l.target);
      if (l.target === hover) s.add(l.source);
    });
    return s;
  }, [hover, data.links]);

  const edges = React.useMemo(() => {
    const out: { a: Placed; b: Placed; key: string }[] = [];
    const user = placed.find((p) => p.node.type === "user");
    placed.forEach((p) => {
      if (p.node.type === "category" && user) out.push({ a: user, b: p, key: `u-${p.node.id}` });
      if (p.parent && byId.get(p.parent)) out.push({ a: byId.get(p.parent)!, b: p, key: `c-${p.node.id}` });
    });
    return out;
  }, [placed, byId]);

  const labels = React.useRef(new Map<string, HTMLDivElement | null>());
  const tooltipRef = React.useRef<HTMLDivElement>(null);
  const hoveredNode = hover ? byId.get(hover)?.node : undefined;
  // Positions DOM labels (id) or the tooltip (null) from projected 3D coordinates, outside React render.
  const place = React.useCallback<Place>((id, x, y, visible) => {
    const el = id === null ? tooltipRef.current : labels.current.get(id);
    if (!el) return;
    el.style.transform = `translate(${x}px, ${y}px)`;
    if (id !== null) el.style.opacity = visible ? "1" : "0";
  }, []);

  return (
    <div className="relative size-full">
    <Canvas camera={{ position: [0, 6, 13], fov: 50 }} dpr={[1, 1.75]} gl={{ antialias: true, powerPreference: "high-performance" }}>
      <AdaptiveDpr pixelated />
      <color attach="background" args={["#07080d"]} />
      <fog attach="fog" args={["#07080d", 14, 34]} />
      <ambientLight intensity={0.45} />
      <pointLight position={[0, 0, 0]} intensity={40} color="#8b7bff" distance={14} />
      <directionalLight position={[6, 10, 6]} intensity={1.4} />
      <Stars radius={60} depth={30} count={immersive ? 2600 : 1400} factor={3} fade speed={0.6} />
      <Sparkles count={immersive ? 120 : 60} scale={14} size={2.2} speed={0.35} color="#9ecbff" opacity={0.6} />

      {edges.map(({ a, b, key }) => (
        <Path key={key} from={a.pos} to={b.pos} color={related.has(b.node.id) && related.has(a.node.id) ? "#8b7bff" : "#3cc8f5"} active={related.has(a.node.id) && related.has(b.node.id)} />
      ))}
      {placed.map((p) => (
        <NodeMesh
          key={p.node.id}
          p={p}
          hovered={hover === p.node.id}
          onHover={setHover}
          onSelect={(sel) => {
            if (!sel.node.link) return;
            setTarget(sel.pos.clone());
            setTimeout(() => onNavigate(sel.node.link!), 950);
          }}
        />
      ))}
      <CameraRig target={target} />
      <Projector placed={placed} hover={hover} place={place} />
      {!target && <OrbitControls enablePan={false} minDistance={6} maxDistance={24} autoRotate={!hover} autoRotateSpeed={0.35} enableDamping />}
    </Canvas>
    {/* DOM overlay: labels + tooltip positioned by projecting 3D points each frame (no extra React roots). */}
    <div className="pointer-events-none absolute inset-0 z-10 overflow-hidden" aria-hidden>
      {placed.map((p) => {
        const big = p.node.type === "user" || p.node.type === "category";
        return (
          <div key={p.node.id} ref={(el) => { labels.current.set(p.node.id, el); }} className="absolute left-0 top-0 will-change-transform">
            <div className={`-translate-x-1/2 whitespace-nowrap rounded-full bg-black/55 px-2.5 py-1 font-medium text-white backdrop-blur ${big ? "text-xs" : "text-[10px] opacity-80"}`}>{p.node.label}</div>
          </div>
        );
      })}
      <div ref={tooltipRef} className="absolute left-0 top-0 transition-opacity duration-150" style={{ opacity: hoveredNode && hoveredNode.type !== "user" ? 1 : 0 }}>
        {hoveredNode && (
          <div className="w-60 -translate-x-1/2 -translate-y-full rounded-2xl border border-white/10 bg-[#10131bdd] p-3 text-left text-white shadow-2xl backdrop-blur-xl">
            <p className="text-sm font-semibold">{hoveredNode.label}</p>
            {hoveredNode.carrier && <p className="text-xs text-white/60">{hoveredNode.carrier}{hoveredNode.premium ? ` · ${money(hoveredNode.premium)}/yr` : ""}</p>}
            {hoveredNode.summary && <p className="mt-1.5 text-xs text-white/80">{hoveredNode.summary}</p>}
            <p className="mt-2 text-[11px] font-medium" style={{ color: STATUS_COLOR[hoveredNode.status] }}>
              {hoveredNode.status === "ok" ? "✓ Healthy" : hoveredNode.status === "attention" ? "▲ Needs attention" : hoveredNode.status === "inactive" ? "○ Inactive" : "? Worth reviewing"}
            </p>
            {hoveredNode.alerts?.slice(0, 2).map((a) => <p key={a} className="mt-1 text-[11px] text-white/70">• {a}</p>)}
            {hoveredNode.link && <p className="mt-2 text-[11px] text-white/50">Click to open</p>}
          </div>
        )}
      </div>
    </div>
    </div>
  );
}

type Place = (id: string | null, x: number, y: number, visible: boolean) => void;

function Projector({ placed, hover, place }: { placed: Placed[]; hover: string | null; place: Place }) {
  const { camera, size } = useThree();
  const v = React.useMemo(() => new THREE.Vector3(), []);
  useFrame(() => {
    for (const p of placed) {
      const offset = p.node.type === "user" ? -1.4 : p.node.type === "category" ? -1.1 : -0.5;
      v.copy(p.pos).add({ x: 0, y: offset, z: 0 } as THREE.Vector3).project(camera);
      place(p.node.id, ((v.x + 1) / 2) * size.width, ((1 - v.y) / 2) * size.height, v.z < 1);
      if (hover === p.node.id) {
        v.copy(p.pos).add({ x: 0, y: 1.1, z: 0 } as THREE.Vector3).project(camera);
        place(null, ((v.x + 1) / 2) * size.width, ((1 - v.y) / 2) * size.height, true);
      }
    }
  });
  return null;
}
