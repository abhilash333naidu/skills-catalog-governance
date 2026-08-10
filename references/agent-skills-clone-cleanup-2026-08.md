# Agent-skills clone cleanup (2026-08)

**Type:** campaign record
**Date:** 2026-08
**Session source:** discovery during catalog audit of a cloned/duplicated skill collection
(`~/.agent-skills/skills/*`) overlapping the catalog under governance.

## What was done

- Used `using-agent-skills` (the meta-skill surfacing this package) to map the skill set,
  flag duplicated/cloned skills, and determine which copy was canonical.
- Catalog dedup process (see Council Per-Group / Phase 2 manifest) applied: group by
  function, pick survivor, archive duplicates to `skills-archive`, update manifest.
- Cleaned only clone copies; kept the canonical skill and recorded the survivor decision.

## Lesson distilled

- Duplicated skill sets are a primary source of catalog drift; audit clone trees as part
  of the finding phase (Phase 1 of the 4-phase workflow).
- A clone is not a merge candidate unless it carries unique content; verify with loss-check
  before consolidation.
- Portability covenant from `SKILL.md` — skills must be self-contained and not depend on
  the user's harness-specific config.

## Evidence

- `references/4-phase-workflow.md` (archive/dedup pipeline).
- `references/skill-dedup-manifest-2026-08.md`.
- `references/skill-merge-manifest-omp-2026-08.md`.