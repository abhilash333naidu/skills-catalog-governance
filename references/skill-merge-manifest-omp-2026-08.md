# Skill merge manifest — OMP (2026-08)

**Type:** manifest record
**Date:** 2026-08
**Session source:** the merge manifest template for the merge campaign on the OMP skill
group (One-Merge-Per-... group), which DOES merge content (Junction 2).

## Shape

- Extends `schemas/manifest.schema.json` with the merge contract: per-group survivor AND
  explicit "merges content from: [ids]" fields.
- Because content merges, the manifest's presence is NOT sufficient — the pipeline
  requires: council verdict per group, loss-check, approval, G1b parity, promotion gates.
- Big merge groups are sliced: one merge per commit/promotion keeps loss-check and G1b
  review tractable.

## Lesson distilled

- A merge manifest (has explicit content joins) must never be filed like a dedup manifest
  (Junction 1). Filing a merge manifest without council + loss-check is file-shaped
  paperwork hiding a 6-of-5 handoff — exactly the class `verify-approval --loss-report`
  exists to re-derive and fail.

## Evidence

- `references/skill-dedup-manifest-2026-08.md` (contrast).
- `references/promotion-gate-merge-to-live-2026-08.md`.
- `schemas/manifest.schema.json`.