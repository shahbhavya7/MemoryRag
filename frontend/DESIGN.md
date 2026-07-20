# MemoryRAG — Liquid-Glass Design System

A small, strict design system so every screen looks like one cohesive glass UI
floating over an animated backdrop. **One primitive, one set of values, used
everywhere.** If you're adding UI, use these — don't invent one-off styles.

The source of truth is [`src/index.css`](src/index.css) (tokens + the `.glass`
primitive) and [`src/components/GlassPanel.tsx`](src/components/GlassPanel.tsx)
(the React wrapper).

---

## 1. Tokens

Defined as CSS variables in `:root` and mirrored into Tailwind's theme
(`@theme`) so utilities like `text-fg`, `bg-accent`, `text-mt-decision` exist.

### Color

| Token | Value | Use |
|---|---|---|
| `--bg-base` | `#0a0711` | Page background base — near-black with a violet cast |
| `--fg` | `#f4f2f8` | **Body text** — warm near-white, high contrast. Never gray body text on glass. |
| `--fg-muted` | `#c7c3d4` | Secondary labels only (still AA on our dark glass) |
| `--fg-faint` | `#8b8598` | Decorative text only, never body copy |
| `--accent` | `#a855f7` | **Primary** accent (violet) — interactive/active states |
| `--accent-2` | `#7c3aed` | **Secondary** accent (deep violet) — the far end of the gradient |
| `--danger` / `--ok` | `#fb7185` / `#34d399` | Error / success |

**The identity is a violet gradient on true black.** Primary buttons, the
wordmark, and the aurora run light violet (`#a855f7`) into deep violet
(`#7c3aed`)/indigo. Two accents total — the glass + background do the heavy
lifting; accents are punctuation (active nav pill, focus ring, primary button,
wordmark, one badge tint).

### Per-memory-type tints (badges only)

`--mt-document #38bdf8` · `--mt-code #34d399` · `--mt-decision #fbbf24` ·
`--mt-workflow #a78bfa` · `--mt-conversation #f472b6`

Each is used as a *tint* on a glass badge (10–18% fill + colored text/border),
not a solid fill — so badges stay within the glass language.

### Shape & type

- Radius: `--glass-radius: 20px` (one radius everywhere).
- Font: **Inter** (`--font-sans`), with a system fallback.
- Scale: `h1` 1.7rem/700, `h2` 1.15rem/600, body 15px/1.55, eyebrow 0.72rem
  uppercase. Comfortable line-height (1.55), never cramped.

---

## 2. The glass recipe (`.glass`)

The **only** place `backdrop-filter` is defined. Every panel gets it via the
`.glass` class (or `<GlassPanel>`).

```css
.glass {
  background-color: rgba(17, 19, 31, 0.45);          /* dark translucent body -> readable text */
  background-image: linear-gradient(135deg,
      rgba(255,255,255,0.13), rgba(255,255,255,0.04) 42%, transparent); /* light frost sheen */
  border: 1px solid rgba(255, 255, 255, 0.14);        /* hairline edge */
  border-radius: 20px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.42),            /* drop shadow (depth) */
              inset 0 1px 0 rgba(255,255,255,0.18);   /* inset highlight = fake light top edge */
  backdrop-filter: blur(20px) saturate(160%);
}
```

Why a **dark** translucent body rather than pure white-over-dark? Contrast. A
dark (blue-black) base guarantees near-white text stays readable no matter what
bright part of the aurora is behind it — while the diagonal sheen + inset
highlight still give the frosted-glass look.

**What keeps it from looking generic (the signature):**
- The sheen and hairline are **cool-tinted** (cyan → faint blue), not plain
  white — the glass reads as "our glass," not a stock frosted panel.
- A two-part inset shadow fakes a **specular edge**: a bright light top edge
  plus a faint cyan rim light around the whole panel.
- The background carries a fine **grain overlay** (SVG noise, ~5% opacity, blend
  `overlay`) so it never looks like a flat gradient fill.
- The wordmark uses a cyan → blue **gradient text** accent.

`.glass-strong` (denser base) is for text-heavy panels (auth card, etc.) as
extra contrast insurance.

---

## 3. Guardrails (the difference between premium and vibe-coded)

1. **Contrast is non-negotiable.** Body text is `--fg` (near-white) on a
   dark-tinted glass base → passes WCAG AA even over the brightest aurora blob
   (worst case ≈ near-white on a dark-violet mid-tone: high contrast). Muted
   text is only for secondary labels. **No gray body text on glass.**
2. **Blur is expensive → few, large panels only.** `backdrop-filter` lives on
   the sidebar, top bar, and page cards — not on buttons, badges, inputs, or
   list rows (those use plain translucent fills). **No nested blur:** the
   content area between the glass shell and the page cards is transparent, so a
   glass card never sits inside another glass panel.
3. **Motion with restraint (Framer Motion).** Route transitions (fade + slight
   rise), panel mount (subtle opacity/scale/rise), hover micro-lifts. Durations
   **150–400ms**, gentle easing (`[0.22,1,0.36,1]`). No bounce, no infinite
   attention loops — the **only** infinite animation is the slow ambient
   background drift. All of it is disabled under `prefers-reduced-motion`.
4. **Consistency.** Every surface = the same `.glass` values (radius, blur,
   border, shadow). Reuse `<GlassPanel>` / `<GlassCard>` — no bespoke panels.
5. **Graceful fallback.** `@supports not (backdrop-filter…)` raises the panel to
   a near-opaque solid so it degrades to readable instead of transparent-mush.

---

## 4. The animated background

Rendered **once** at the app root (`<Background/>` in `App.tsx`) — the single
heavy animated background for the whole app (performance guardrail). It's a
`position: fixed` layer (`.bg-aurora`, z-index -1) composed of:

- a deep-blue CSS base + three soft radial gradients (cyan / blue / deep-cyan),
- the **React Bits "Aurora"** WebGL component on top (violet→magenta→indigo
  color stops), and
- a **fine grain overlay** (`.bg-aurora::after`) so it never looks like a flat
  fill.

The CSS base doubles as the **reduced-motion fallback**: under
`prefers-reduced-motion` we skip the animated WebGL layer entirely and show only
the static gradient. The Aurora canvas's animation is the one allowed ambient
loop; the panels' `backdrop-filter` blurs *this* background — that's what gives
the glass something to refract.

---

## 4b. React Bits components used

All vendored (copied-in) under `src/components/reactbits/`, per React Bits'
copy-in install model (MIT license). Each was verified against the current
catalog at reactbits.dev and pulled from the official shadcn-style registry
(`public/r/<Name>-TS-TW.json`), TypeScript + Tailwind variant. The only edit is
swapping the `motion/react` import to the `framer-motion` package already in
this app (same library).

| Component | Category | Where it's used | Extra dep |
|---|---|---|---|
| **Aurora** | Backgrounds | The app-wide animated background (`Background.tsx`) | `ogl` |
| **BlurText** | Text Animations | Login/Register titles (words blur-fade in) | — (framer-motion) |
| **CountUp** | Text Animations | Evaluation page — the accuracy headline animates 0→value | — (framer-motion) |

---

## 5. Using it

```tsx
import { GlassPanel, GlassCard } from "./components/GlassPanel";

// A padded content card that animates in on mount:
<GlassCard>…</GlassCard>

// A bare panel (you control padding), denser tint, hover-liftable:
<GlassPanel strong interactive className="p-6">…</GlassPanel>
```

`<GlassPanel>` is a `motion.div`: it plays the mount animation by default
(`animateIn`), respects reduced-motion automatically, and forwards any
Framer-Motion / div props. `<GlassCard>` is just `<GlassPanel>` with `p-5`.

**Rule of thumb:** if it's a surface, it's a `GlassPanel`. If it's inside a
surface, it's plain translucent (`bg-white/6`, a hairline border) — never
another blurred panel.
