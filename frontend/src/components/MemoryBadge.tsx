// A distinct glass badge per memory type, each tinted with its own accent.
// This is the visual centerpiece: it animates in when the router's decision
// arrives, making "which memory did it pick?" impossible to miss.

import { motion, useReducedMotion } from "framer-motion";

import { memoryMeta } from "../lib/memoryTypes";

export default function MemoryBadge({
  type,
  index = 0,
  size = "md",
}: {
  type: string;
  index?: number;
  size?: "sm" | "md";
}) {
  const reduce = useReducedMotion();
  const meta = memoryMeta(type);
  const Icon = meta.Icon;
  const pad = size === "sm" ? "px-2 py-0.5 text-[0.68rem]" : "px-2.5 py-1 text-xs";
  const iconSize = size === "sm" ? 12 : 14;

  return (
    <motion.span
      initial={reduce ? false : { opacity: 0, scale: 0.8, y: 4 }}
      animate={reduce ? undefined : { opacity: 1, scale: 1, y: 0 }}
      transition={{ duration: 0.3, delay: index * 0.07, ease: [0.22, 1, 0.36, 1] }}
      className={`inline-flex items-center gap-1.5 rounded-full border font-semibold ${pad}`}
      style={{
        color: meta.color,
        borderColor: `${meta.color}59`, // ~35% alpha
        background: `${meta.color}1f`, // ~12% alpha tint
        boxShadow: `0 0 18px ${meta.color}22`,
      }}
    >
      <Icon size={iconSize} className="shrink-0" aria-hidden="true" />
      {meta.label}
    </motion.span>
  );
}
