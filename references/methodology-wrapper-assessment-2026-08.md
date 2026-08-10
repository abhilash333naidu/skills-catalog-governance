# Methodology wrapper assessment (2026-08)

**Type:** methodology note
**Date:** 2026-08
**Session source:** review of how the catalog-governance methodology wraps the underlying
skill-execution harnesses (`using-agent-skills` / meta-skill routing).

## What it covers

- The catalog-governance package is a WRAPPER over harness skill-execution: it governs
  `SKILL.md` files of cataloged skills but does not re-implement their runtime.
- Wrapper obligations: (a) package hygiene gates apply to cataloged skills, not just this
  package; (b) the council and loss-check apply at merge time regardless of harness; (c)
  portability covenant — a cataloged skill must be self-contained and not depend on the
  harness that authored it.
- The embedded council procedure exists precisely to keep the wrapper viable in ANY
  harness (`references/embedded-council-procedure.md`).

## Lesson distilled

- A methodology wrapper must not drift into pretending it is the underlying system;
  claims about "what skills do" come from the skills' own artifacts, verified fresh
  (G4), not from the wrapper's narrative.

## Evidence

- `references/embedded-council-procedure.md`.
- `references/agent-self-audit-catalog-2026-08.md`.