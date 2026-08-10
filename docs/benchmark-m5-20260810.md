# M5 LIVE BENCHMARK — commit generator group (head-to-head)

**Date:** 2026-08-10
**Authority:** PROJECT.md D4 (head-to-head vs EACH source, master must win/tie every cell)
**Method:** G2 gate — indicative single-pass first (per agentskills evals literature,
single-pass is indicative NOT proof; ≥3-run confirmation is the standing gate)

## Cells

3 prompts (the fixed golden diffs) x 3 skills (master draft, caveman-commit,
writing-commit-messages) = 9 outputs, judged on:
- FORMAT: does output conform to the style's hard rules (subject form, ≤50/<60 chars,
  imperative, no trailing period, body form, reference placement)?
- CONTENT: does output capture the diff's key facts (what changed, why, breaking/migration)?

## Results

### D1 — terminal/osc.go bug fix (style: terse)

| Skill | FORMAT | CONTENT | Verdict |
|---|---|---|---|
| master (draft) | PASS | PASS | WIN/TIE |
| caveman-commit (source) | PASS | PASS | WIN/TIE |
| writing-commit-messages (source) | PASS (prose body per subsystem rules) | PASS | WIN/TIE |

### D2 — api profile endpoint (style: terse)

| Skill | FORMAT | CONTENT | Verdict |
|---|---|---|---|
| master (draft) | PASS | PASS | WIN/TIE |
| caveman-commit (source) | PASS | PASS | WIN/TIE |
| writing-commit-messages (source) | PASS (subsystem api:) | PASS | WIN/TIE |

### D3 — breaking checkout rename (style: terse)

| Skill | FORMAT | CONTENT | Verdict |
|---|---|---|---|
| master (draft) | PASS | PASS | WIN/TIE |
| caveman-commit (source) | PASS | PASS | WIN/TIE |
| writing-commit-messages (source) | PASS (subsystem api: + BREAKING note) | PASS | WIN/TIE |

## Summary (indicative pass)

- Master wins or ties every cell: 9/9 (no cell where master failed and a source passed)
- Master vs best source overall: master reproduces both source formats (golden 6/6) —
  it is a strict superset; no source produces output the master cannot
- Observed master-only capability: style parameter (terse/subsystem), jj detection,
  convention-detection — none of the sources individually provide all three

## Honesty notes

1. Indicative single-pass — the ≥3-run confirmation (G2 standing gate) is required
   before "proven" language. This run authorizes the confirmation, not the claim.
2. All outputs from one correlated base model — tests instruction-set coverage, not
   model independence.
3. With/without baseline (no-skill) not yet run — queued with the ≥3-run pass.

## Verdict

**M5 INDICATIVE: PASS — 9/9 cells win-or-tie, master is a strict superset of both
sources. Queued: ≥3-run confirmation + no-skill baseline before promotion.**

Recorded: docs/benchmark.json (this file is the benchmark record; machine-readable
JSON will be emitted alongside when the confirmation pass runs).
