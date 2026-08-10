# Agent self-audit of the skills catalog (2026-08)

**Type:** campaign record / process evidence
**Date:** 2026-08
**Session source:** audit run of the skills catalog that surfaced the set of catalog
governance defects later captured as hardening gates G0–G4.

## What was done

- Ran a fresh-session, plan-mode audit over the catalog root with a full artifact scan
  (bias to the artifact, not the memory).
- Self-audit checklist applied: description length (`<=1024`) per package; rule line
  length; `name == directory` frontmatter rule; dangling `references/*` links as failure;
  rule text kept in sync with any behavior change; package passed its own gates at promotion.
- Found and put on the record: `name != directory` mismatch at the package root itself
  (frontmatter `name: skills-catalog-governance`, directory `skill_gov`), package line
  length over-runs, and the seed set of reference files that promotion later proved
  missing.

## Lesson distilled

- Claim "package passed its own gates" must be backed by a concrete artifact
  (`run-record/package.json`, `council-verdict-*.md`), not by narrative (G4).
- The root package is subject to the same G0 hygiene it enforces on `skills/`.
- Fresh-context audit catches "bias to the memory" defects that in-session checks miss.

## Evidence

- `scripts/catalog_governance.py` `check-package` output (see `run-record/package.json`
  when a run was recorded).
- Hardening gates detail: `references/hardening-gates.md`.