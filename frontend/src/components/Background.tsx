// The ambient animated backdrop — rendered ONCE at the app-shell level. Uses
// the React Bits "Aurora" WebGL background (vendored under reactbits/) over a
// dark base + grain overlay (CSS in index.css). This is the single heavy
// animated background for the whole app (performance guardrail).
//
// Under prefers-reduced-motion we skip the animated WebGL layer and show only
// the static gradient base, so no non-essential motion runs.

import { useReducedMotion } from "framer-motion";

import Aurora from "./reactbits/Aurora";

export default function Background() {
  const reduce = useReducedMotion();
  return (
    <div className="bg-aurora" aria-hidden="true">
      {!reduce && (
        <div className="absolute inset-0 opacity-80">
          <Aurora colorStops={["#7c3aed", "#ec4899", "#6366f1"]} amplitude={1.15} blend={0.6} />
        </div>
      )}
    </div>
  );
}
