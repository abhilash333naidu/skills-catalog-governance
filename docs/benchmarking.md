# Benchmarking (G2)

## Overview

The G2 benchmark is a deterministic verification gate that prevents promoting a merged master skill unless it demonstrably outperforms every source it was built from.

**Important:** The G2 gate validates a benchmark bundle — it does not run the benchmarks itself. The orchestrator (human or automated) conducts the benchmark runs, collects verdicts from an LLM judge (or human reviewer), and produces a benchmark bundle that `benchmark` validates.

## Conditions for GO

1. **Every** master_vs_source cell verdict is WIN or TIE (no LOSS cells)
2. **Master beats the best source overall** — total master wins > any single source's losses
3. **At least one** master_vs_baseline cell exists (proves the skill does something)
4. **All cells** have runs ≥ 3 (LLM nondeterminism requires multiple trials)
5. **`runs_per_cell`** field ≥ 3

## Bundle Schema

```json
{
  "schema": "skills-catalog-benchmark-1",
  "runs_per_cell": 3,
  "cells": [
    {
      "id": "format-standards",
      "kind": "master_vs_source",
      "source": "src-a",
      "runs": 3,
      "verdict": "WIN"
    },
    {
      "id": "no-skill-baseline",
      "kind": "master_vs_baseline",
      "runs": 3,
      "verdict": "WIN"
    }
  ]
}
```

## Judge Honesty Note

The G2 judge is typically the same base model family that generated the outputs (correlated judge). This tests instruction-set coverage and format conformance, NOT model-independent quality.

A correlated judge can systematically favour the output style it was prompted to produce. Any benchmark artifact MUST carry this honesty note. Genuinely independent validation requires a different provider/model as judge.

## Pilot Result

36/36 cells PASS on the commit-message family pilot. Full data in `docs/benchmark.json`, `docs/benchmark-g2-d1.json`, `docs/benchmark-g2-d2.json`, `docs/benchmark-g2-d3.json`.