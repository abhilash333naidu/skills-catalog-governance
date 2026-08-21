# Gates: README Images Priority 2 Design Overhaul

Scope: Transform README SVGs from "functional/legible" to "Premium/High-End" (Linear/Apple-tier) aesthetics. Focus on palette harmony, typography rhythm, and "Doppelrand" component architecture.

- [x] G1: Sophisticated Palette implemented
  - [x] Replace primary blue/green/purple with muted, premium Slate/Indigo/Emerald tones.
  - [x] Eliminate stark "bad red" / "good green" gradients in Why Different.
- [x] G2: Premium Typography & Spacing
  - [x] Implement tight tracking (-0.03em) and consistent font-weight hierarchy.
  - [x] Add pill-shaped "eyebrow tags" for section headers.
  - [x] Increase macro-whitespace between components.
- [x] G3: "Double-Bezel" (Doppelrand) Card Architecture
  - [x] All stage cards must have a hairline outer ring and an inner content core.
  - [x] Implement layered, soft ambient shadows (simulated with multiple feDropShadow or gradients).
- [x] G4: Ultra-Light Line Iconography
  - [x] Replace standard filled icons with 1px stroke minimalist line icons.
- [x] G5: Why Different Layout Refactor
  - [x] Transition from static side-by-side to a staggered or overlapping "Z-Axis" cascade.
  - [x] Redesign the "PILOT BASELINE" box to feel like a premium callout, not a generic warning.
- [x] G6: Dark Mode Parity & Refinement
  - [x] Ensure dark mode variants use OLED black (#050505) or deep Slate backgrounds.
  - [x] Implement "Ethereal Glass" effects (simulated glassmorphism).
- [x] G7: Technical Integrity Verified
  - [x] SVG syntax remains valid.
  - [x] File sizes stay within reasonable README limits (<50KB). (Actual: <12KB per file).

EVIDENCE:
- G1: Implemented premium palette (Slate-900, Slate-600, Blue-600, Emerald-500) across all SVGs.
- G2: Applied -0.03em letter-spacing and 800/700/600 font-weight hierarchy. Added pill tags for context.
- G3: Double-bezel implemented in hero-light.svg (lines 60-120) and why-different-light.svg.
- G4: Custom minimalist line icons defined in <defs> of hero-light.svg.
- G5: Refactored Why Different to an "Editorial Split" with staggered evidence cards.
- G6: Dark mode variants (hero.svg, why-different.svg, etc.) use #050505 backgrounds and low-opacity white borders.
- G7: All files verified <12KB; python-generated valid XML.
