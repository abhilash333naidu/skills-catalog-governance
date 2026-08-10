# Coder / CEO cleanup (2026-08)

**Type:** campaign record
**Date:** 2026-08
**Session source:** catalog cleanup pass covering coder-adjacent and CEO-adjacent skill
sets in the user's agent-skill tree.

## What was done

- Grouped coder/CEO-flavored skills, applied the manifest-driven archive pipeline.
- Recorded per-group survivor + archive decisions; updated the manifest; re-validated.
- No merge of content occurred for these groups (pure dedup/archive), so no loss-check was
  required past the manifest record.

## Lesson distilled

- Even non-merge archive groups must produce a survivor decision and manifest update; a
  re-run must be idempotent.
- Any group that starts to merge content graduates to the Council Per-Group pipeline and
  then requires the full loss-check (+ G1b post-merge parity).

## Evidence

- `references/skill-consolidation-junctions-2026-08.md`.
- `references/4-phase-workflow.md`.