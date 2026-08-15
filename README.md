# AI-Agent Skill Governance

**Discover, consolidate, verify, benchmark, and safely promote skills across coding-agent ecosystems.**

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-green)
![Platform: Windows | Linux | macOS](https://img.shields.io/badge/platform-windows%20%7C%20linux%20%7C%20macos-lightgrey)
![Dependencies: none](https://img.shields.io/badge/dependencies-none-brightgreen)

Skills Catalog Governance is an agent-agnostic pipeline for discovering, consolidating, verifying, benchmarking, and safely promoting AI-agent skills. It treats skill consolidation as a gated engineering process — not a blind merge.

**Who it is for:** Developers and power users running Hermes, Claude Code, OpenCode, Codex, OpenHands, or any Agent Skills-compatible system whose skill catalogs have outgrown manual management.

**What it produces:** Evidence-based decisions about which skills to keep, merge, archive, or promote — with cryptographic integrity checks at every step.

---

## The Problem

AI coding agents accumulate skills quickly. Hermes profiles, Claude Code directories, OpenCode stores, Codex plugins, vendored trees — each harness has its own skills folder with its own accumulated content.

```
         Multiple agents / repositories / skill sources
                        │
                 Skills accumulate
                        │
              Duplicate / overlapping skills
                        │
           Conflicting / stale / uncertain skills
                        │
            Manual deletion or blind LLM merging
                        │
             Risk of lost behaviour / regressions
```

Soon you have 100–200+ skills with overlapping families: three "write a commit message" skills, five "review" skills, a family of `gstack-*` skills. Nobody can tell which is best, whether they should merge, or what they would lose by archiving one.

No public tooling existed for this (verified mid-2026). The agentskills.io spec has no dedup guidance. Academic methods (SkillClone, arXiv:2603.22447) are preprints with unpublished code.

---

## The Solution

**Skills Catalog Governance treats skill consolidation as a gated engineering process rather than a blind merge.**

```
  ┌──────────┐
  │ Discover │  — inventory every skill across stores
  └────┬─────┘
       ▼
  ┌──────────┐
  │  Group   │  — find candidate overlaps by similarity
  └────┬─────┘
       ▼
  ┌───────────┐
  │  Council  │  — decide what to merge (mandatory review)
  └────┬──────┘
       ▼
  ┌─────────────┐
  │  Build      │  — create canonical master skill
  └────┬────────┘
       ▼
  ┌─────────────────┐
  │  Loss Check     │  — verify all source content is preserved
  └────┬────────────┘
       ▼
  ┌─────────────────┐
  │  Golden Gate*   │  — verify output reproduction (formatters only)
  └────┬────────────┘
       ▼
  ┌─────────────┐
  │  Benchmark  │  — compare master vs every source
  └────┬────────┘
       ▼
  ┌────────────────────┐
  │  Hash-Bound       │  — cryptographically bind approval to draft
  │  Approval         │
  └────┬──────────────┘
       ▼
  ┌──────────────┐
  │  Promotion   │  — promote master, archive originals
  └──────────────┘
```

*Golden gate is required only for generated-output skills (formatters, generators, style systems).

---

## Why It Matters

Coding agents are increasingly dependent on reusable procedural knowledge stored as skills. As skill catalogs grow across multiple harnesses and repositories, duplication and inconsistent versions become a quality and maintenance problem.

The value of this project is not merely finding similar files — it is providing **evidence** before replacing multiple skills with one canonical skill. Every consolidation is backed by:

- Content-integrity verification (loss check)
- Behavioural-output verification (golden gate)
- Competitive benchmarking (G2)
- Cryptographic hash binding (approval chain)
- Non-destructive archival (never delete)

> **Similarity generates candidates. Evidence determines promotion.**

---

## Best Use Case: Growing Multi-Agent Skill Catalogs

### Before

A power user with 6 months of agent usage across Hermes, Claude Code, and OpenCode has accumulated 211 skills across multiple store directories. Many are near-duplicates — different names, similar behaviour, uncertain provenance.

### After

A full pipeline run on one family (commit-message skills):

```
211 skills discovered
  → 19 candidate groups identified
    → Council verdict: MERGE two generators + KEEP_SEPARATE one executor
      → Golden gate: 6/6 output match → absorption authorized
        → G2 benchmark: 36/36 cells PASS → promotion cleared
          → 2 survivors promoted, 1 archived
```

The result: one canonical skill replacing multiple overlapping ones, with SHA-256 verification that every source behaviour is preserved.

Full pilot evidence: `docs/` and `artifacts/pilot-commit-family/`.

---

## What Makes It Different

| Capability | What it does |
|---|---|
| **Discovery** | Inventories skills across configured stores with SHA-256 fingerprints |
| **Grouping** | Finds candidate overlaps using TF-IDF cosine + word overlap |
| **Council** | Makes the semantic consolidation decision (mandatory, never skippable) |
| **Loss Check** | Detects missing headings, commands, and content from sources |
| **Golden Gate** | Tests behavioural reproduction byte-for-byte across fixed inputs |
| **Benchmark** | Compares canonical skill against each source (must win or tie every cell) |
| **Integrity** | Binds approvals and operations to SHA-256 hashes |
| **Non-destructive** | Archives instead of silently deleting |
| **Provenance** | Records where consolidated skills came from (`merged-from:` list) |
| **Promotion Gates** | Prevents incomplete/failed changes from being promoted |

---

## Governance-Driven Safety and Integrity

Skills Catalog Governance includes security and integrity controls embedded in its governance pipeline. These protect against accidental data loss, tampering, and unsafe operations during skill consolidation.

**The project includes security and integrity controls, but it is not currently a comprehensive security scanner for malicious or poisoned skills.** The G1 static scan is a first-pass regex check — it catches obvious credential exposures and code-execution patterns but is not a semantic security analyser.

What IS implemented:

| Control | What it does |
|---|---|
| **SHA-256 tree integrity** | Every move operation is verified before, during, and after execution |
| **Hash-bound approval** | Approval documents are cryptographically tied to exact draft content |
| **Tamper detection** | Source changes between planning and execution are detected and blocked |
| **Non-destructive archival** | Skills are moved to archive, never deleted; requires `--apply --yes` |
| **Hardened runner execution** | Golden-gate runners are disabled by default; shell metacharacters and inline-code args are refused |
| **Fail-closed promotion gates** | Every gate produces PASS/FAIL — FAIL blocks the next phase |
| **Provenance tracking** | Consolidated skills carry `merged-from:` source lists |
| **Multi-stage verification** | Loss check → golden gate → benchmark → approval, each gating the next |

See [docs/security-model.md](docs/security-model.md) for the full scope, including acknowledged gaps.

---

## Agent-Agnostic

This is not a Hermes tool, a Claude Code tool, or an OpenCode tool. It operates on the filesystem and works with any system that stores skills as `SKILL.md` files in directories. Supported stores include:

- **Hermes** — `~/.hermes/skills/` and `%APPDATA%/hermes/profiles/*/skills/`
- **Claude Code** — `~/.claude/skills/`
- **OpenCode** — `~/.config/opencode/skills/`
- **Codex** — `~/.codex/skills/`
- **OpenHands / OMP / Pi** — platform-specific skill directories
- **Any filesystem path** — pass `--stores` to scan additional directories

```
  Hermes   Claude Code   OpenCode   Codex   OpenHands   Other sources
     │         │           │         │         │            │
     └─────────┴───────────┴─────────┴─────────┴────────────┘
                              │
                   Skills Catalog Governance
                              │
                       Canonical skill catalog
```

---

## How It Works (Pipeline)

The lifecycle is divided into six phases (M1–M6), each producing a deterministic artifact:

| Phase | Command | Output |
|---|---|---|
| **M1 — Discovery** | `detect-skills` | Tagged inventory with names, descriptions, SHA-256 |
| **M2 — Grouping** | `detect-groups` | Similar-pair candidates + suggested groups |
| **M3 — Council** | (human-supervised LLM review) | Verdict: merge / split / recategorize |
| **M3.5 — Golden Gate** | `golden-gate` | N/N output match = absorption authorized |
| **M4 — Master Build** | `check-master` | G0/G1/G3-gated staged draft |
| **M5 — Benchmark** | `benchmark` | GO/NO-GO verdict |
| **M6 — Promotion** | (manual with gates) | SHA-256-verified live install |

Detailed lifecycle documentation: [docs/lifecycle.md](docs/lifecycle.md).

---

## Quick Start

### Requirements

- Python 3.10+ (stdlib only — no pip dependencies)
- macOS / Linux: `python3` on PATH
- Windows: PowerShell 5+ (or pwsh) or `python` on PATH

### Install

One-liner (detects harnesses on your machine):

```bash
# macOS / Linux
curl -fsSL https://raw.githubusercontent.com/abhilash333naidu/skills-catalog-governance/main/install.sh | bash

# Windows (PowerShell)
irm https://raw.githubusercontent.com/abhilash333naidu/skills-catalog-governance/main/install.ps1 | iex
```

Or specify a target directly:

```bash
python3 scripts/catalog_governance.py install --target <your-skills-dir>
```

Verify the install:

```bash
python3 scripts/catalog_governance.py check-package --root .
# → {"status": "PASS", ...}
```

### First Workflow

```bash
# 1. Discover every skill in default stores
python3 scripts/catalog_governance.py detect-skills --output inventory.json

# 2. Find similar families (candidates only — no decisions)
python3 scripts/catalog_governance.py detect-groups \
    --inventory inventory.json \
    --overlap-threshold 0.50

# 3. For each suggested group, run the council review
#    (see docs/lifecycle.md for the council procedure)

# 4. Build the staged master and run gates
python3 scripts/catalog_governance.py check-master --draft skills-merge-drafts/master.SKILL.md

# 5. Verify output reproduction (for formatter/generator skills)
python3 scripts/catalog_governance.py golden-gate --manifest golden.json --workdir ./work

# 6. Run benchmark verification
python3 scripts/catalog_governance.py benchmark --bundle docs/benchmark.json

# 7. Approve and promote
python3 scripts/catalog_governance.py verify-approval --draft master.SKILL.md --approval approval.json
```

Scan additional stores without modifying them:

```bash
python3 scripts/catalog_governance.py detect-skills --stores ~/third-party/skills
```

---

## Example: Commit-Message Family Pilot

[`artifacts/pilot-commit-family/`](artifacts/pilot-commit-family/) contains the full output of an end-to-end pipeline run on the commit-message skill family:

```
Input:
  211 skills discovered (0 errors)
  19 candidate groups
  Council verdict: MERGE two generators + KEEP_SEPARATE one executor
  Golden gate: 6/6 output match → absorption authorized
  G2 benchmark: 36/36 cells PASS → GO
  Promotion: 2 survivors promoted, 1 archived
```

Full evidence: `docs/benchmark.json`, `docs/council-verdict-commit-family-20260810.md`, and associated artifacts.

---

## Architecture

`scripts/catalog_governance.py` is a single-file Python CLI (stdlib-only, 2059 lines). It operates on local skill directories and produces structured JSON output. The package also includes:

- `schemas/*.json` — JSON schemas for all governance artifacts
- `references/*.md` — Operational documentation and gate bodies
- `tests/test_catalog_governance.py` — 1375-line test suite

Architecture deep dive: [docs/architecture.md](docs/architecture.md).

Governance model: [docs/governance-model.md](docs/governance-model.md).

---

## Documentation

| Document | Content |
|---|---|
| [docs/architecture.md](docs/architecture.md) | Code structure, CLI commands, design principles |
| [docs/lifecycle.md](docs/lifecycle.md) | M1–M6 pipeline: purpose, commands, output of each phase |
| [docs/governance-model.md](docs/governance-model.md) | Gates, non-negotiables, state transitions |
| [docs/benchmarking.md](docs/benchmarking.md) | G2 benchmark conditions, bundle schema, judge honesty |
| [docs/security-model.md](docs/security-model.md) | Governance-driven safety, implemented controls, gaps |
| [docs/golden-gate.md](docs/golden-gate.md) | Output reproduction verification |
| [docs/provenance.md](docs/provenance.md) | Source tracking, version discipline, package integrity |

---

## Future Direction

These are acknowledged future capabilities, not current features:

- **Runtime integration with self-learning agents** — monitoring skill drift and mutation during agent operation
- **Agent-generated skill proposals** — accepting skill candidates produced by agent self-learning
- **Skill freshness and drift detection** — flagging skills that have become stale or behaviourally drifted
- **Stronger semantic security analysis** — extending G1 beyond regex patterns to AST-level scanning
- **External-source trust and signing** — verifying skill provenance from third-party publishers
- **Dependency and vulnerability intelligence** — CVE scanning, lockfile verification
- **Cross-skill interaction analysis** — detecting conflicts, race conditions, and ordering constraints

---

## Platform Support

Windows, Linux, macOS. Junction-aware on Windows, symlink-aware on POSIX. Tested on Windows 10 / git-bash with Python 3.11+.

## License

MIT — see [LICENSE](LICENSE).

## Evidence

The commit-message family pilot (2026-08-10) ran the full pipeline end-to-end: 211 skills discovered (0 errors), 19 groups suggested, council verdict (two survivors), golden-output 6/6 match, G2 benchmark 36/36 cells PASS. Full transcripts and benchmark data in `docs/` and `artifacts/pilot-commit-family/`.