# Golden Gate

## Purpose

The golden gate (M3.5) verifies that a merged master skill reproduces the exact output of every source skill it replaces, for a fixed set of inputs. This converts the council's "these skills share a core" premise from assertion to evidence.

## When It Applies

Required only for skills that produce deterministic output: formatters, generators, style systems, template engines, report builders, etc.

For advisory-only skills or those with inherently non-deterministic output, the golden gate is skipped in favour of the G2 benchmark alone.

## How It Works

1. The orchestrator creates a manifest listing the master runner, source runners, and fixed input cases
2. Each input is run through the master runner and each source runner
3. The outputs are compared byte-for-byte (modulo whitespace)
4. N/N matching pairs = absorption authorized

## Runner Safety

Runners are **disabled by default** — the manifest must set `"allow_runners": true`. When enabled:

- Runners are orchestrator-provided argv lists (no shell)
- Shell metacharacters are detected and refused
- Inline-code executor args (`-c`, `-e`, `--eval`, etc.) are refused
- NUL bytes in runner arguments are refused
- Execution has a configurable timeout (max 120s)
- Runner output is captured and hashed locally — never transmitted anywhere

## Pilot Result

6/6 matching pairs on the commit-message family pilot. Full data in `docs/golden-output-experiment-brief-20260810.md` and `docs/golden-output-experiment-20260810.md`.