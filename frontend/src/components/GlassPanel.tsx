// The ONE glass surface primitive. Every panel/card in the app is built from
// this so radius/blur/border/shadow stay identical everywhere (see .glass in
// index.css). Includes a subtle Framer-Motion mount animation, disabled when
// the user prefers reduced motion.

import { motion, useReducedMotion, type HTMLMotionProps } from "framer-motion";

interface GlassPanelProps extends HTMLMotionProps<"div"> {
  /** Denser tint for text-heavy panels (extra contrast insurance). */
  strong?: boolean;
  /** Play the mount animation (on by default). */
  animateIn?: boolean;
  /** Add a gentle hover lift for clickable cards. */
  interactive?: boolean;
}

export function GlassPanel({
  strong = false,
  animateIn = true,
  interactive = false,
  className = "",
  children,
  ...rest
}: GlassPanelProps) {
  const reduce = useReducedMotion();
  const shouldAnimate = animateIn && !reduce;

  return (
    <motion.div
      initial={shouldAnimate ? { opacity: 0, y: 10, scale: 0.99 } : false}
      animate={shouldAnimate ? { opacity: 1, y: 0, scale: 1 } : undefined}
      transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
      whileHover={interactive && !reduce ? { y: -3 } : undefined}
      className={`glass ${strong ? "glass-strong" : ""} ${className}`}
      {...rest}
    >
      {children}
    </motion.div>
  );
}

/** A GlassPanel with card padding baked in — the default surface for content. */
export function GlassCard({ className = "", ...props }: GlassPanelProps) {
  return <GlassPanel className={`p-5 ${className}`} {...props} />;
}
