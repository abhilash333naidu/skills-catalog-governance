# Delegated full-read comparison (2026-08)

**Type:** methodology note
**Date:** 2026-08
**Session source:** experiment during loss-check hardening comparing single-session manual
comparison vs delegated comparison.

## The experiment

- Full read of every source `SKILL.md` (fresh context) executed as a delegated subagent
  task, output compressed, then diffed against the merged draft.
- Compared against the lead's own single-session read of the same sources.

## Result

- The delegated, fresh-context full read caught drift (missing heading / reordered block)
  that the lead's single-session read had tolerated as "known context."
- Compression of the delegate's output preserved the defect set (headings, command
  blocks, hash-relevant spans) while cutting context cost — consistent with
  `references/context-cost-of-skill-catalog-2026-08.md`.
- Lesson: comparisons performed inside the session that wrote the draft inherit that
  session's "curse of knowledge"; a fresh-context reader is a stronger verification signal
  (echoes G1b's fresh-session verification and G4's fresh-context audit).

## Lesson distilled

- Prefer a fresh-context, delegated full-read for the authoritative comparison; keep the
  mechanical loss-check as the cheap second signal.
- Delegated output must still be grounded (G4): the delegate returns findings, the lead
  verifies against the artifact.

## Evidence

- `references/hardening-gates.md` (G1b).
- `references/council-merge-loss-check-2026-08.md`.