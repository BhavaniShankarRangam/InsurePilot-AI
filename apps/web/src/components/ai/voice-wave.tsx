"use client";

import { motion, useReducedMotion } from "framer-motion";

/** Animated voice waveform driven by microphone level. */
export function VoiceWave({ level, active, bars = 18 }: { level: number; active: boolean; bars?: number }) {
  const reduce = useReducedMotion();
  return (
    <div className="flex h-6 items-center gap-[3px]" aria-hidden>
      {Array.from({ length: bars }).map((_, i) => {
        const center = 1 - Math.abs(i - bars / 2) / (bars / 2);
        const h = active ? 4 + (level * 18 + 4) * (0.4 + center * 0.6) : 4;
        return (
          <motion.span
            key={i}
            className="w-[3px] rounded-full bg-accent-gradient"
            animate={reduce ? { height: h } : { height: active ? [h * 0.6, h, h * 0.75] : 4 }}
            transition={{ duration: 0.35 + (i % 4) * 0.08, repeat: active && !reduce ? Infinity : 0, repeatType: "mirror" }}
          />
        );
      })}
    </div>
  );
}
