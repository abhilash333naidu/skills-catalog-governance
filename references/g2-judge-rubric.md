# G2 Judge Rubric — explicit scoring criteria + model-limitation honesty note

**Purpose:** make the G2 empirical A/B judge's criteria explicit, reproducible, and
bounded. A judge without a published rubric is a moving target; a judge with a
published rubric can be audited, challenged, and repeated by any harness.

## The judge (who/what)

The G2 judge is the LEAD (orchestrator) reading outputs against this rubric, optionally
with a second model for cross-model stability (agentskills evals literature). In the
2026-08-10 M5 run, the judge was the same base model family that GENERATED the outputs
(DeepSeek-V4-Pro serial). This is the single biggest validity caveat in the whole gate.

## HONESTY NOTE (binding — never omit from any benchmark artifact)

> The G2 judge in the pilot (and typically in any single-model run) is a CORRELATED
> judge: the same base model family that produced the candidate outputs. This tests
> INSTRUCTION-SET COVERAGE and FORMAT CONFORMANCE of the skill, NOT model-independent
> quality. A correlated judge can systematically favor the style of output it was
> prompted to produce. Do NOT claim G2 evidence as "independent validation". Real
> cross-model validation requires a DIFFERENT provider/model as judge (e.g. judge =
> one model family, generator = another), which is a deliberate, higher-cost run.
>
> Any `benchmark.json` or G2 evidence file MUST carry this note verbatim or a
> pointer to this file. A benchmark without the honesty note is not a governed
> G2 artifact.

## Scoring rubric (the 2 axes, both required for a PASS cell)

### Axis 1 — Format conformance (deterministic where possible)
Check the output's STRUCTURE against the skill's stated contract:
- conventional-commit prefix present & valid (`feat|fix|chore|docs|refactor|test|perf|...`)
- subject length within contract (e.g. ≤50 chars, imperative mood, no trailing period)
- subsystem prefix style honored (e.g. `terminal/osc`) when the contract requires it
- fenced code-block output shape, if the contract specifies one
Prefer PROGRAMMATIC checks (regex) over eyeballing — the pilot used a checker script.
Record per-cell: pass/fail + the failing rule.

### Axis 2 — Content completeness (judge read)
Does the output capture the DIFF'S KEY FACTS? For a commit-message benchmark:
- every changed file/subsystem mentioned that matters
- the semantic intent (what changed and why) present
- no hallucinated facts (files not in diff, wrong operations)
- no dropped facts that a human reviewer would flag as important
Judge read is the lead's manual pass; record a one-line justification per cell.

### Cell verdict
- with_skill PASS + without_skill FAIL → **VALUE** (skill earns its keep)
- both PASS → tighten the assertion (the cell is too easy — refine prompt)
- both FAIL → broken skill or broken test (investigate before re-running)
- with_skill FAIL + without_skill PASS → REGRESSION (the skill actively harms)

### ≥3 runs/cell
LLM nondeterminism: a single run per cell is indicative, NOT proof. The standing gate
is ≥3 runs/cell (agentskills evals literature). Record run counts in `benchmark.json`.

## Cross-model judge procedure (when budget allows — the honest upgrade)

1. Generate candidate outputs with model A (the skill's normal executor).
2. Judge with model B from a DIFFERENT provider/family (or a human reviewer).
3. Judge model B reads ONLY the outputs + this rubric — never the skill body
   (avoids the "judge sees the answer key" confound).
4. Record judge model + provider in benchmark.json; if judge==generator family,
   the honesty note above applies verbatim.

## When to use

- Any G2 empirical A/B run (post-merge battle-test, M5-style live benchmark).
- Any claim containing "proven", "validated", or "battle-tested" about skill value.
- Writing a new benchmark.json or extending an existing one.
