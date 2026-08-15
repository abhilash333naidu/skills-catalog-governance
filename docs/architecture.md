# Architecture

## Overview

Skills Catalog Governance is a single-file Python CLI (`scripts/catalog_governance.py`) that operates on skill directories on the local filesystem. It is stdlib-only by design — zero pip dependencies, zero network calls, zero telemetry.

```
┌──────────────────────────────────────────────────────┐
│                Skills Catalog Governance              │
│  scripts/catalog_governance.py  │  schemas/*.json      │
│  SKILL.md                        │  references/*.md     │
└──────────────────────────────────────────────────────┘
          │
          │ operates on
          ▼
┌──────────────────────────────────────────────────────┐
│              AI-Agent Skill Stores                    │
│  ┌────────┐ ┌──────────┐ ┌────────┐ ┌────────┐      │
│  │ Hermes │ │ClaudeCode│ │OpenCode│ │ Codex  │ ...   │
│  └────────┘ └──────────┘ └────────┘ └────────┘      │
└──────────────────────────────────────────────────────┘
```

## Design Principles

| Principle | Description |
|---|---|
| **Stdlib-only** | Python 3.10+ standard library only. No pip install required. |
| **Fail-closed** | Any validation error produces a structured FAIL report. No silent best-effort paths. |
| **Non-destructive** | Skills are moved to archive, never deleted. Requires explicit `--apply --yes`. |
| **Hash-verified** | Every operation is bound to SHA-256 digests of source content. |
| **Evidence-based** | Every claim in output is backed by literal command output and hashes. |
| **Agent-agnostic** | Works with any harness that stores skills as `SKILL.md` files in directories. |

## Code Structure

```
scripts/
  catalog_governance.py    Single-file CLI (2059 lines)

schemas/
  approval.schema.json     Approval document schema
  benchmark.schema.json    G2 benchmark bundle schema
  council-verdict.schema.json  Council decision schema
  golden.schema.json       Golden-gate manifest schema
  loss-check.schema.json   Loss-check report schema
  manifest.schema.json     Archive manifest schema
  provenance.schema.json   Provenance tracking schema

references/
  *.md                     Operational documentation and gate bodies

docs/
  *.md                     Product documentation, pilot evidence

tests/
  test_catalog_governance.py  1375-line test suite
```

## CLI Commands

| Command | Purpose |
|---|---|
| `detect-skills` | Discover and inventory skills across stores |
| `detect-groups` | Find candidate similar-skill families |
| `check-package` | Verify governance package completeness |
| `validate-manifest` | Validate an archive/merge manifest |
| `validate-council-verdict` | Validate a council decision document |
| `preflight-moves` | Plan skill moves with hash verification |
| `apply-moves` | Execute verified skill moves |
| `loss-check` | Detect missing content between source and draft |
| `verify-approval` | Verify a hash-bound approval against live state |
| `check-master` | Run G0/G1/G3 gates on a staged master skill |
| `golden-gate` | Verify output reproduction across inputs |
| `benchmark` | Verify G2 benchmark conditions |
| `repair` | Iterative draft repair against loss-check defects |
| `install` | Install into detected harness skill stores |