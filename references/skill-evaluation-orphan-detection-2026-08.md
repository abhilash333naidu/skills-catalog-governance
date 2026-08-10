# Skill evaluation / orphan detection (2026-08)

**Type:** methodology note
**Date:** 2026-08
**Session source:** detection of orphaned skills — skills a catalog stores but no workflow
loads, and generated files nobody owns.

## Orphan classes

1. **Unreferenced skill:** no meta-skill route table, no workflow, no portability request
   references it (the "curse of knowledge" risk is assuming past use). Detection: search
   route tables / `using-agent-skills` config + session logs; fresh context, not memory.
2. **Dangling catalog entries:** a manifest/index entry with no on-disk skill — same
   two-directional reconcile as G3/G3.5.
3. **Generated/scratch files** (`__pycache__`, temp outputs, unstaged run-records) that are
   neither packaged nor ignored. Detection: `.gitignore` + `check-package` package-presence.

## Evaluation

- Legitimacy audit per `references/methodology-wrapper-assessment-2026-08.md`: only three
  legitimate find-sources (existing run-records, skills used in delivered workflows,
  direct portability requests).
- Orphans get evaluated, not auto-deleted: archive (Junction 1) if a duplicate/record
  exists, else leave + document pending a portability request.

## Evidence

- `references/skill-consolidation-junctions-2026-08.md`.
- `references/hardening-gates.md` (G3/G3.5).