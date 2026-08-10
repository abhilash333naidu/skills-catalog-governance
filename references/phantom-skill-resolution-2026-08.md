# Phantom skill resolution (2026-08)

**Type:** incident record
**Date:** 2026-08
**Session source:** catalog audit found skills that existed in the manifest / index but not
on disk (or vice versa) — "phantom" entries.

## What was done

- Correlated `references/`-listed files, manifest paths, and on-disk tree.
- Root causes seen: a reference file listed in `SKILL.md` with no file on disk
  (dangling reference, G3); a file on disk never listed in the References section
  (G3.5(a)); a manifest entry whose path escaped the catalog root (manifest validation
  fail).
- Resolution: scrub both directions — required files derived from `SKILL.md` must exist
  (G3), and the References section must be reconciled against on-disk files (G3.5).

## Lesson distilled

- "Phantom" = state mismatch between what is referenced and what exists. The fix is a
  two-directional reconcile, made mechanical by check-package (G3/G3.5), never a manual
  "I believe it's there."

## Evidence

- `references/hardening-gates.md` (G3, G3.5).
- `scripts/catalog_governance.py` `check-package` `missing_references`.