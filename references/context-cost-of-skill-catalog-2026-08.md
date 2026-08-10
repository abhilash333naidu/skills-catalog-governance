# Context cost of the skill catalog (2026-08)

**Type:** measurement note
**Date:** 2026-08
**Session source:** observation during catalog audit: catalog `SKILL.md` files get loaded
into every session start (via `using-agent-skills` / meta-skill routing).

## The problem

Large, verbose skill bodies inflate the fixed session-loading context. In this package
root, `SKILL.md` was ~680 lines — far over the package's own G0 121–400 line rule — and
directly raised load cost. Cost scales with surface area: every line a skill's body
exposes must be read, deduped, and reasoned over per session.

## The response

- Claim: "Skill file exploded by N% (smaller, cleaner, cheaper — barely any context debt
  left)." This claim is a marketing-sounding absolute with no baseline artifact; treat it
  as unverified; any real "cost" claim must be grounded in before/after line counts or
  token measurements, not vibes (G4).
- G0 hygiene (line length) is the primary cost control, plus hard caps on description
  length.
- Progressive disclosure: keep only binding gate text in `SKILL.md`; move bulky gate
  bodies and procedures to `references/` (this package's collapse of gates/toolkit/
  workflow into `references/*` is that pattern applied).
- Compatibility covenant: `references/*` links must resolve under G3; a skill that cannot
  slimmed under its own rules instead documents why.

## Lesson distilled

- Context cost is governed by load-set size; catalog skills must pass their own hygiene
  gates or they tax every session they load into.
- "Smaller/cleaner" claims need an artifact (line count, token delta), not an adjective.

## Evidence

- G0 gate: `references/hardening-gates.md`.
- This package's `references/` collapse (`hardening-toolkit.md`, `hardening-gates.md`,
  `embedded-council-procedure.md`, `4-phase-workflow.md`).