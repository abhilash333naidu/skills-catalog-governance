# Restore vs rewrite follow-up (2026-08)

**Type:** methodology note
**Date:** 2026-08
**Session source:** decision recorded during recovery of a skill whose source tree had
drifted from its manifest/canonical copy.

## The rule

When a cataloged skill's on-disk state no longer matches its recorded state (manifest
hash, archive hash, or canonical copy):

- **Restore** is the default when the canonical copy exists and the drift is corruption,
  truncation, or accidental edit. Verify by comparing tree hashes after restore (G2).
- **Rewrite** is chosen ONLY when the canonical copy is itself wrong/outdated and a
  deliberate change is authorized (approval required; if content merges, the full council
  + loss-check pipeline applies).

## Lesson distilled

- Never "fix forward" by rewriting when restoring reproduces the intended state; rewrite
  silently is how content is lost. Restoration is verified by hash equality; rewriting is a
  promotion (all promotion gates apply).

## Evidence

- `references/hardening-gates.md` (G2 post-move revalidation).
- `references/promotion-gate-merge-to-live-2026-08.md`.