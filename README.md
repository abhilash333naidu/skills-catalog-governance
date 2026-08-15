# AI-Agent Skill Governance

<p align="center">
  <strong style="font-size: 1.4em;">Turn Skill Sprawl Into a Governed Skill Catalog</strong><br>
  <em>Discover, consolidate, verify and safely promote canonical skills across AI-agent harnesses.</em>
</p>

<p align="center">
  <img src="assets/brand/hero.svg" alt="Skills Catalog Governance — Turn skill sprawl into governed catalog through verified promotion pipeline" width="100%">
</p>

<p align="center">
  <a href="#quickstart"><img src="https://img.shields.io/badge/quickstart-install-blue" alt="Quickstart"></a>
  <a href="docs/lifecycle.md"><img src="https://img.shields.io/badge/docs-lifecycle-blue" alt="Lifecycle Docs"></a>
  <a href="docs/security-model.md"><img src="https://img.shields.io/badge/docs-security-green" alt="Security Model"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green" alt="License"></a>
  <img src="https://img.shields.io/badge/python-3.10%2B-blue" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/platform-windows%20%7C%20linux%20%7C%20macos-lightgrey" alt="Platform">
  <img src="https://img.shields.io/badge/dependencies-none-brightgreen" alt="No Dependencies">
</p>

<p align="center">
  <strong>Skills Catalog Governance</strong> is an agent-agnostic governance pipeline for discovering, consolidating, verifying, benchmarking, and safely promoting AI-agent skills across coding harnesses.
</p>

---

## The Problem

AI coding agents accumulate skills rapidly. Hermes profiles, Claude Code directories, OpenCode stores, Codex plugins, vendored trees — each harness maintains its own skills folder with accumulated content.

<p align="center">
  <img src="assets/diagrams/before-after.svg" alt="Before and after comparison: multi-harness skill sprawl transformed into a governed canonical skill catalog" width="100%">
</p>

Soon you have 100–200+ skills with overlapping families: three "write a commit message" skills, five "review" skills, a family of `gstack-*` skills. Nobody can tell which is best, whether they should merge, or what they would lose by archiving one.

---

## The Solution

**Skills Catalog Governance treats skill consolidation as a gated engineering process — not a blind merge.**

<p align="center">
  <img src="assets/diagrams/pipeline.svg" alt="Governance pipeline from discovery through promotion with verification gates" width="100%">
</p>

### Core Differentiator

<div align="center">
  <img src="assets/diagrams/why-different.svg" alt="Traditional blind merge vs governance pipeline comparison" width="100%">
</div>

> **Similarity generates candidates. Evidence determines promotion.**

---

## See the Pipeline

<p align="center">
  <img src="assets/demo/governance-pipeline.gif" alt="Animated terminal demo showing the governance pipeline execution from detect-skills through promotion — illustrative replay using actual pilot evidence" width="100%">
</p>

<p align="center"><em>Illustrative replay — based on actual pilot evidence. 162 KB GIF, loops continuously.</em></p>

### Real Tool Output

The commands below produce genuine output. Here is `check-package` verifying a complete installation:

<p align="center">
  <img src="assets/demo/check-package-output.png" alt="Real CLI output from check-package showing PASS with all 32 required files verified" width="85%">
</p>

---

## Real Pilot Evidence

<p align="center">
  <img src="assets/evidence/pilot-result.svg" alt="Real pilot result: 211 skills discovered, 19 candidate families identified, council verdict, 6/6 golden gate, 36/36 benchmark, 2 canonical skills promoted" width="100%">
</p>

**Commit-message family — full pipeline run (2026-08-10).** Pilot result after council review, verification and promotion gates.

| Phase | Command | Result |
|-------|---------|--------|
| **Discover** | `detect-skills` | 211 skills, 0 errors, 5 stores |
| **Group** | `detect-groups` | 19 candidate families (strong-pair) |
| **Council** | `llm-council` / embedded | MERGE 2 generators + KEEP_SEPARATE executor |
| **Loss Check** | `loss-check` | All sources covered ≥35% overlap |
| **Golden Gate** | `golden-gate` | **6 / 6** output match — absorption authorized |
| **Benchmark** | `benchmark` (G2) | **36 / 36** cells PASS — GO |
| **Promote** | `apply-moves` | **2 canonical skills promoted**, 191 archived (preserved) |

> **No skills deleted** — all 191 moved to `skills-archive/` with full SHA-256 provenance.

Full evidence: [`docs/benchmark.json`](docs/benchmark.json) · [`docs/council-verdict-commit-family-20260810.md`](docs/council-verdict-commit-family-20260810.md) · [`artifacts/pilot-commit-family/`](artifacts/pilot-commit-family/)

---

## Key Capabilities

<p align="center">
  <img src="assets/diagrams/capabilities.svg" alt="Six core capabilities: Discover, Group, Council, Verify, Benchmark, Promote" width="100%">
</p>

| Capability | What It Does |
|------------|--------------|
| **DISCOVER** | Inventory every skill across stores with SHA-256 fingerprints |
| **GROUP** | Identify candidate overlaps using TF-IDF + word overlap |
| **COUNCIL** | Make semantic consolidation decisions (mandatory, never skipped) |
| **VERIFY** | Detect content/behaviour loss — loss-check + golden-gate |
| **BENCHMARK** | Compare master against each source — must win or tie every cell |
| **PROMOTE** | Hash-bound, non-destructive promotion with full provenance |

---

## Why Evidence Matters

Traditional approaches stop at similarity. This pipeline continues through **verification gates**:

```
Traditional:  Find similar → LLM merge → Hope it works
                    │
Governance:   Find similar → Candidate group → Council decision
                              │
                              ├── Loss check (content preserved?)
                              ├── Golden gate (output reproduced?)
                              ├── Benchmark (master beats sources?)
                              └── Hash-bound approval (tamper-proof)
                                    │
                              Promote → Archive → Commit
```

**The difference:** Every consolidation decision is backed by measurable evidence, not assumptions.

---

## Who It Is For

**Developers and power users** running AI coding agents whose skill catalogs have outgrown manual management:

- **Hermes** — `~/.hermes/skills/`, `%APPDATA%/hermes/profiles/*/skills/`
- **Claude Code** — `~/.claude/skills/`
- **OpenCode** — `~/.config/opencode/skills/`
- **Codex** — `~/.codex/skills/`
- **OpenHands / OMP / Pi** — platform-specific directories
- **Any filesystem path** — pass `--stores` to scan additional directories

**This is not a Hermes tool, a Claude Code tool, or an OpenCode tool.** It operates on the filesystem and works with any system that stores skills as `SKILL.md` files in directories.

---

## Quickstart

### Requirements

- Python 3.10+ (stdlib only — **no pip dependencies**)
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

## How It Works (Pipeline)

The lifecycle is divided into six phases (M1–M6), each producing a deterministic artifact:

| Phase | Command | Output |
|-------|---------|--------|
| **M1 — Discovery** | `detect-skills` | Tagged inventory with names, descriptions, SHA-256 |
| **M2 — Grouping** | `detect-groups` | Similar-pair candidates + suggested groups |
| **M3 — Council** | (human-supervised LLM review) | Verdict: merge / split / recategorize |
| **M3.5 — Golden Gate** | `golden-gate` | N/N output match = absorption authorized |
| **M4 — Master Build** | `check-master` | G0/G1/G3-gated staged draft |
| **M5 — Benchmark** | `benchmark` | GO/NO-GO verdict |
| **M6 — Promotion** | (manual with gates) | SHA-256-verified live install |

Detailed lifecycle documentation: [`docs/lifecycle.md`](docs/lifecycle.md).

---

## Governance-Driven Safety and Integrity

Skills Catalog Governance includes security and integrity controls embedded in its governance pipeline. These protect against accidental data loss, tampering, and unsafe operations during skill consolidation.

**The project includes security and integrity controls, but it is not currently a comprehensive security scanner for malicious or poisoned skills.** The G1 static scan is a first-pass regex check — it catches obvious credential exposures and code-execution patterns but is not a semantic security analyser.

What IS implemented:

| Control | What It Does |
|---------|--------------|
| **SHA-256 tree integrity** | Every move operation verified before, during, and after execution |
| **Hash-bound approval** | Approval documents cryptographically tied to exact draft content |
| **Tamper detection** | Source changes between planning and execution are detected and blocked |
| **Non-destructive archival** | Skills moved to archive, never deleted; requires `--apply --yes` |
| **Hardened runner execution** | Golden-gate runners disabled by default; shell metacharacters refused |
| **Fail-closed promotion gates** | Every gate produces PASS/FAIL — FAIL blocks next phase |
| **Provenance tracking** | Consolidated skills carry `merged-from:` source lists |
| **Multi-stage verification** | Loss check → golden gate → benchmark → approval, each gating the next |

See [`docs/security-model.md`](docs/security-model.md) for full scope, including acknowledged gaps.

---

## Architecture

`scripts/catalog_governance.py` is a single-file Python CLI (stdlib-only, 2059 lines). It operates on local skill directories and produces structured JSON output.

Architecture deep dive: [`docs/architecture.md`](docs/architecture.md) · Governance model: [`docs/governance-model.md`](docs/governance-model.md)

---

## Documentation

| Document | Content |
|----------|---------|
| [`docs/architecture.md`](docs/architecture.md) | Code structure, CLI commands, design principles |
| [`docs/lifecycle.md`](docs/lifecycle.md) | M1–M6 pipeline: purpose, commands, output of each phase |
| [`docs/governance-model.md`](docs/governance-model.md) | Gates, non-negotiables, state transitions |
| [`docs/benchmarking.md`](docs/benchmarking.md) | G2 benchmark conditions, bundle schema, judge honesty |
| [`docs/security-model.md`](docs/security-model.md) | Governance-driven safety, implemented controls, gaps |
| [`docs/golden-gate.md`](docs/golden-gate.md) | Output reproduction verification |
| [`docs/provenance.md`](docs/provenance.md) | Source tracking, version discipline, package integrity |

---

## Future Direction

Acknowledged future capabilities (not current features):

- Runtime integration with self-learning agents — monitoring skill drift during operation
- Agent-generated skill proposals — accepting skills produced by agent self-learning
- Skill freshness and drift detection — flagging stale or behaviourally drifted skills
- Stronger semantic security analysis — extending G1 beyond regex to AST-level scanning
- External-source trust and signing — verifying skill provenance from third-party publishers
- Dependency and vulnerability intelligence — CVE scanning, lockfile verification
- Cross-skill interaction analysis — detecting conflicts, race conditions, ordering constraints

---

## Platform Support

Windows, Linux, macOS. Junction-aware on Windows, symlink-aware on POSIX. Tested on Windows 10 / git-bash with Python 3.11+.

## License

MIT — see [`LICENSE`](LICENSE).

## Evidence

The commit-message family pilot (2026-08-10) ran the full pipeline end-to-end: 211 skills discovered (0 errors), 19 candidate families identified, council verdict (two canonical skills), golden-output 6/6 match, G2 benchmark 36/36 cells PASS. Full transcripts and benchmark data in [`docs/`](docs/) and [`artifacts/pilot-commit-family/`](artifacts/pilot-commit-family/).