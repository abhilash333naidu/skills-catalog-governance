# DEFECT REPORT — M1 detect-skills (orchestrator verification, 2026-08-10)

**Status:** M1 detect-skills is DONE. D1-D5 closed; D6 was reclassified as non-bug (see below).

## D1-D5 (CLOSED 2026-08-10, orchestrator-verified)

D1-D5 were repaired and re-verified by the orchestrator after a final review pass:
- pytest: 17 passed (was 14, +3 new D2 regression tests covering multi-line descriptions)
- real catalog: 211 skills cataloged, 0 errors, status PASS (was 74/137 failed pre-repair)
- gstack family (formerly fully broken) now successfully parsed
- multi-line description: continuation lines handled correctly (join with " " for plain
  scalars, preserve "\n" for `|` literal block scalars — per YAML spec)

## D6 (RECLASSIFIED — NOT A BUG)

Originally flagged as "26% of descriptions have embedded newlines". Re-verified
against YAML specification:

- When a SKILL.md uses `description: |` (literal block scalar marker), the YAML
  spec REQUIRES preserving newlines verbatim.
- The parser correctly joins plain-scalar continuation lines with a single space
  (line 158 in catalog_governance.py) and preserves newlines for `|` markers
  (line 156). Both behaviors are YAML-spec-conformant.
- Real file example (`gstack/SKILL.md`):
  ```
  description: |
    Router for the gstack skill suite. Sends any gstack request to the right skill
    (planning, review, QA, shipping, debugging, docs, security, design). For browser/QA
  ```
- The output `'Router for the gstack skill suite. Sends any gstack request to the right skill\n(planning, review, QA, ...'` is CORRECT, not a bug.

**Decision:** Leave parser as-is. Downstream consumers (M2 grouping, M3 council, etc.)
must handle multi-line descriptions correctly. Add a downstream note for M2 that
similarity checks should normalize whitespace (split + rejoin) before comparing
descriptions.

## Original D1-D5 detail (for historical reference)

## D1 (CRITICAL) — Multi-line description: frontmatter rejected as malformed

Real SKILL.md files have plain-scalar continuation lines indented under
`description:` (e.g. line 2 of the frontmatter starts `  Use when: ...`).
The current parser regex flags these as "malformed frontmatter line" and
drops the skill from inventory.

PROOF (orchestrator ran this): detect-skills on the real catalog reports
74 parse errors out of 137 skills (54%), including the entire gstack
family, caveman/cavecrew, ponytail, brainstorming-dialog, agent-reach.
These files are VALID YAML, not malformed.

Example (real file, ~/.agents/skills/tdd-iron-law-compact/SKILL.md):
  ---
  name: tdd-iron-law-compact
  description: Compact TDD iron-law enforcement card. ...
    Use when: about to write logic that needs a test; ...
  ---

## D2 (CRITICAL) — Missing regression test for multi-line descriptions

The 5 unit tests did not cover multi-line description scalars, which is why
"14 passed" while the real catalog fails. ADD a regression test: a fixture
with a two-line description (first line + indented continuation line),
asserting that it parses and `description` contains both lines.

## D3 (MODERATE) — Parser must distinguish key lines from continuation lines

- A new key (`name:` / `description:` at column 0) ends the previous value.
- Any indented line that is NOT a list item and NOT a new key is a
  CONTINUATION of the current value — do not raise on it.
- Only raise for genuinely malformed input: unclosed `---` block, or a
  top-level line that is neither key, continuation, nor list item.

## D4 (MINOR) — Nested vendor dirs scanned

Nested vendor dirs (e.g. herdr/vendor/libghostty-vt/.agents/skills/
writing-commit-messages) are scanned. Acceptable for M1; ensure canonical
dedup handles them; do not fail the run on their presence.

## D5 (GATE) — Re-verification requirement

After repair, run BOTH:
1. `python -m pytest tests/ -x -q`
2. `python scripts/catalog_governance.py detect-skills` on the real catalog

Report the NEW error count — it must be ZERO parse errors (or only
genuinely-malformed files you can name, with proof). Show literal outputs.
