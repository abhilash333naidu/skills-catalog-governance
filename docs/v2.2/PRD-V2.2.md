# PRD: Skills Catalog Governance V2.2

**Status:** Council-approved scope (GO WITH CHANGES, 2026-08-25)
**Evidence base:** `council-transcript-v2p2p4-plan-review.md`, `tasks/plan.md`

## Problem statement

AI agents install skills written by strangers. Today nothing gates what lands in a
catalog beyond human goodwill. Two failure modes dominate:

1. **Malicious skills** — instructions that exfiltrate data, disable safeguards, or
   hijack agent behavior when activated.
2. **Degrading skills** — well-intentioned skills whose actual structure (missing
   tool declarations, malformed output contracts) silently degrades agent reliability.

V2.0 shipped intake gating + hash-bound human approval + rollback. V2.1 shipped a
static scanner. V2.2 closes the remaining hole (a decision path that lets edited
bytes escape a security block) and adds honest, structural grading — because as the
First Principles advisor put it: *every phase must amplify protection against
malicious/degrading installed skills or get cut.*

## User stories

### Skill authors
- As a **skill author**, I want explicit FAIL reasons (`unclosed_fence`,
  `no_tools_declared`) so I can fix my skill without guessing.
- As a **skill author**, I want normalization rules written down (CRLF, trailing
  whitespace) so my Windows-authored skill isn't failed spuriously.
- As a **skill author**, I want grading labeled advisory/structural so I'm not held
  to behavioral claims the tool doesn't make.

### Repo maintainers
- As a **maintainer**, I want `decide` to refuse APPROVE when skill bytes changed
  after evaluation, so nobody can slip edits past review.
- As a **maintainer**, I want a golden detect-skills fixture captured before any
  refactor, so legacy output regressions surface immediately.
- As a **maintainer**, I want deterministic GO/NO-GO reports I can attach to PRs.

### Security reviewers
- As a **security reviewer**, I want HIGH findings to hard-block APPROVE with no
  bypass short of remediation and fresh scanning.
- As a **security reviewer**, I want scanner findings labeled "tripwire, not
  boundary" so downstream consumers don't over-trust 7 regexes as OWASP coverage.
- As a **security reviewer**, I want tool expectations to require real usage — no
  vacuous passes from skills that declare zero tools.

## Success metrics

| Metric | Target |
|---|---|
| Decide drift hole | Regression test proving modified blocked bytes cannot APPROVE without re-evaluation |
| Grader determinism | Byte-identical reports across repeated runs |
| False-positive rate on honest skills | Tracked; spurious failures must cite a specific rule |
| Legacy regression safety | Golden detect-skills fixture byte-equal in CI |
| Suite health | Full pytest green; ruff clean; `check-package` green |

## Non-goals

- **NO live LLM execution.** Grader is static/structural. We never run skill content.
- **NO ASPM/YAML ingestion.** Hand-rolled YAML parsing is cut (council change #2).
  SKILL.md-only; parse per-format at point of use; IR waits for a fourth consumer.
- **NO exporter until a named consumer commits.** An unread catalog export is
  liability surface, not value.
- **NO behavioral grading claims.** Reports say loudly: structural grading only;
  behavioral claims advisory.
