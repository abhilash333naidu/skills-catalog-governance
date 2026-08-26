# Implementation Plan: Skills Catalog Governance V2.2 — Council-Amended Roadmap

## Status

COUNCIL VERDICT: **GO WITH CHANGES** (2026-08-25). All five required changes below
are incorporated into the task list. Build proceeds in the amended order only.

## Overview

Amended post-V2.1 roadmap per LLM council review (5 advisors + peer panel +
chairman; transcript: `council-transcript-v2p2p4-plan-review.md`).

## Required Council Changes (all applied)

1. **decide forces re-evaluation on hash drift** — if a proposal's skill bytes
   changed after evaluation, `decide` refuses APPROVE and requires a fresh
   `evaluate-proposal` + `scan-security` run. Hash-matching alone never clears
   a HIGH security block.
2. **Cut ASPM + hand-rolled YAML parser from Phase 2.** SKILL.md-only ingestion.
   Parse frontmatter per-format at point of use; IR deferred until a fourth
   consumer exists.
3. **Explicit normalization rule for byte-comparison:** strip trailing
   whitespace per line, normalize CRLF→LF, compare exact otherwise. Written
   fenced-block extraction grammar: only ``` / ~~~ fences; an output block is a
   fence whose info string contains `output`; first matching block wins;
   unclosed or nested fences are an explicit FAIL, not a skip.
4. **Split Task 4.1 into 4.1a/4.1b; capture golden detect-skills fixtures
   before any refactor work.**
5. **Exporter deferred** until a named external consumer commits.

Additional adopted items: regex findings labeled "tripwire, not boundary" in
all docs/reports; schema-versioned canonical lockfile design reserved for when
the exporter returns; ~50-line hash-linked append-only decision log adopted as
cheap high-leverage item.

## Binding Constraints (unchanged)

- Stdlib only; never execute skill content; fail closed; SHA-256 bound artifacts;
  legacy commands unchanged; deterministic ordering; Windows-safe paths.

## Amended Task List (build order)

### Task A (FIRST — council "one thing to do first"): decide re-evaluation gate
- `evaluate-proposal` records `evaluated_skill_sha256`. `decide --approve`
  recomputes the current hash; on drift it fails closed requiring fresh
  evaluation; HIGH findings on current hashes block APPROVE unconditionally.
- Acceptance: regression test proves modifying blocked skill bytes cannot yield
  APPROVE without re-evaluation.
- Files: scripts/catalog_governance.py, tests/. Size: M.

### Task B: golden fixture for detect-skills (pre-refactor safety net)
- Capture byte-identical legacy output fixture + test.
- Size: S.

### Phase 3 (grader) — promoted to next build phase:
### Task C: fixture schema (`schemas/skill-fixture.schema.json`)
- Fields: fixture_id, input, expect_exact_output OR expected_tools,
  case_sensitive default true.
- Size: S.
### Task D: `grade-skill` command
- Applies normalization rule + fenced-block grammar exactly as specified above.
- expected_tools requires non-empty intersection AND every listed tool present
  (vacuous zero-tool passes impossible); skills declaring no allowed-tools FAIL
  tool-based fixtures explicitly.
- Reports labeled: structural grading only; behavioral claims advisory.
- Size: M.
### Task E: docs relabel scanner findings as tripwire (README + report text)
- Size: S.

Checkpoint: full suite green; grader deterministic; decide hole proven closed.

### Deferred (not scheduled)
- Phase 2 adapters beyond SKILL.md; ASPM/YAML parser; IR abstraction.
- Phase 4 exporter (returns only when a named consumer commits).
- Expansionist items reserved: standalone verify-catalog script, badge tiers,
  hash-linked decision log (adopted as future cheap task F).

## Verification Commands

```bash
python -m pytest tests/ -q
ruff check scripts/ tests/
python scripts/catalog_governance.py check-package --root .
```

## Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Grader false positives alienate authors | Medium | Advisory labeling; structural scope; explicit FAIL reasons |
| Maintainer-as-attack-vector | Medium | Council flagged; human approval queue discipline documented |
| Scope creep back toward deferred phases | High | Explicitly out-of-scope until named consumer/spec exists |
