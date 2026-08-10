# Skill dedup manifest (2026-08)

**Type:** manifest record
**Date:** 2026-08
**Session source:** manifest produced for a dedup-only archive campaign (Junction 1 —
no content merges).

## Shape

Per `schemas/manifest.schema.json` plus the dedup fields from `SKILL.md` Phase 2:

- `roots`: catalog root dirs; `outcome_destinations`, `audit-archive root`.
- Group size TARGET (ids listed, one survivor reserved); per-group survivor.
- `payload` entries with "key description" values abstracting the payload from catalog
  `SKILL.md` details; pacing defined, deadlines NOT defined in the manifest.
- Dedup groups reference the survivor decision but carry no merge instructions (nothing to
  loss-check).

## Lesson distilled

- A dedup manifest must NOT smuggle merge intent into archive groups; when the manifest
  starts implying content joins, the group graduates to Junction 2 and demands the council
  + loss-check.

## Evidence

- `references/skill-consolidation-junctions-2026-08.md`.
- `schemas/manifest.schema.json`.