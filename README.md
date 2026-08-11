# skills-catalog-governance

Govern your AI-agent skills catalog like a software project: discover every skill,
group similar families, run an LLM council to build ONE master skill, prove it better
with a live benchmark, and promote it safely.

If you have a bloated skills folder — dozens of similar skills across harnesses, unsure
which to keep, which to merge, which to archive — this skill is the solution.

## The problem

Coding agents accumulate skills fast: Hermes profiles, Claude Code, opencode, codex,
OMP, vendored plugin trees. Soon you have 100-200+ skills with overlapping families
(three "write a commit message" skills, five "review" skills, a whole family of
`gstack-*`). Nobody can tell which is best, whether they should merge, or what they'd
lose by archiving one.

No public tooling exists for this (verified 2026-08): the agentskills.io spec has no
dedup guidance, and the only academic method (SkillClone, arXiv:2603.22447, NTU) is a
preprint with unpublished code. We built the workflow instead.

## What it does

The pipeline (each phase gated by an orchestrator, never by the writer):

| Phase | Command / step | Output |
|---|---|---|
| M1 Discovery | `detect-skills` | tagged inventory: store, path, name, description, sha256 |
| M2 Grouping | `detect-groups` | similar-pair candidates + suggested groups (never a decision) |
| M3 Council | 5 advisors → 5 anonymous reviews → chairman | verdict: merge / split / recategorize, with provenance |
| M3.5 Golden gate | fixed inputs through each source vs one master contract | 6/6 = absorption authorized |
| M4 Master build | staged draft outside live root | G0/G1/G3-clean merged SKILL.md |
| M5 Benchmark | head-to-head vs each source, ≥3 runs/cell | master wins or ties every cell |
| M6 Promotion | snapshot → promote → archive → commit | sha256-verified live install |

Non-negotiables:
- NON-DESTRUCTIVE only — every removal is a move to `skills-archive/`, never `rm -rf`.
- Council is a MANDATORY quality gate, never skippable (embedded fallback procedure
  runs even without the `llm-council` skill).
- Verification Discipline — every claim backed by literal command + literal output.
- Portability covenant — masters never use harness-specific prompts, commands, or telemetry.
- External/vendored skill trees are never edited — content is absorbed in, parent left whole.

## Requirements

- **Python 3.10+** — stdlib only, no pip dependencies. The tool checks this and
  fails with a clean error, never a raw traceback, when your Python is too old.
- **macOS / Linux**: `python3` on your PATH. The one-liner needs `git` only when it
  has to clone the repo; running from a checkout needs nothing extra. Generated
  inventories contain absolute local paths and should not be committed.
- **Windows**: PowerShell 5+ (or pwsh) for `install.ps1`. The installer uses the
  `py` launcher (`py -3`) or `python` on your PATH. No git required — it falls back
  to downloading a zip archive.
- Nothing else: no other tools, permissions, or credentials.

## Install

### One-liner (recommended)

The installer detects the coding harnesses on your machine, lists them, and lets you
pick which one(s) to install into (e.g. opencode, pi, claude, codex, omp, hermes).

macOS / Linux (bash):

```bash
curl -fsSL https://raw.githubusercontent.com/abhilash333naidu/skills-catalog-governance/main/install.sh | bash
```

Windows (PowerShell):

```powershell
irm https://raw.githubusercontent.com/abhilash333naidu/skills-catalog-governance/main/install.ps1 | iex
```

The installer is interactive: it prints the detected harnesses and asks which to use
(type the number, "all", or "custom path"). Pass `--target <name>` to skip the prompt.
In a noninteractive shell, pass `--target` or explicit `--yes`; otherwise installation
fails closed rather than selecting every detected harness. Re-running never overwrites
without confirmation; `--yes` replaces after a timestamped backup.

### Manual

```bash
# Copy the whole folder into any harness's skills directory, e.g.:
cp -r skills-catalog-governance ~/.claude/skills/
# or ~/.config/opencode/skills/, ~/.agents/skills/, a Hermes profile skills dir, etc.
```

Verify the install:

```bash
python3 scripts/catalog_governance.py check-package --root .
# status: PASS means the package is complete
```

## Quickstart

```bash
# 1. Discover every skill in your default stores
python3 scripts/catalog_governance.py detect-skills --output inventory.json

# 2. Find similar families (candidates only — no decisions)
python3 scripts/catalog_governance.py detect-groups --inventory inventory.json --overlap-threshold 0.50

# 3. For each suggested group, run the council (see SKILL.md M3)
# 4. Build the staged master, benchmark it, promote (see SKILL.md M4-M6)
```

Scan additional stores (tagged read-only, never touched):

```bash
python3 scripts/catalog_governance.py detect-skills --stores ~/third-party/skills
```

## How it works

- `detect-skills`: junction/symlink-aware scan, YAML frontmatter parsing with
  dir-name fallback, exact-byte sha256, canonical-path dedup. Fail-closed.
- `detect-groups`: all-pairs flat TF-IDF cosine + word-overlap (pure stdlib; tune
  `--threshold` and `--overlap-threshold`, both defaulting to 0.30 and 0.50),
  method from the SkillClone paper's own ablation — flat TF-IDF is F1 .881 without
  any ML training). Low threshold (0.30) biases toward over-flagging: a false
  positive costs one wasted read; a false negative misses a whole group.
- Council: Karpathy-style LLM council — five thinking-lens advisors, five anonymous
  peer reviews, one chairman synthesis. Honest framing: the advisors are lenses on
  one correlated model, not five independent models; the value is divergent framing
  and blind-spot surfacing.
- Golden gate: for generator/formatter skills, one parameterized master contract
  must reproduce every source's output on fixed inputs before absorption is allowed.
- G2 benchmark: master vs each source, ≥3 runs per cell, plus a no-skill baseline.
  Master must win or tie every cell AND beat the best source overall.

## Security

- Stdlib-only, fail-closed CLI. Never deletes; moves require an explicit plan and
  both `--apply --yes`.
- Refuses collisions, symlinks/junctions, missing SKILL.md, unexpected state changes.
- G1 static scan (regex) on every incoming skill and merge draft for shell/exec
  patterns, credential reads, and unpinned transitive deps.
- No credentials, no telemetry, no network calls in the core workflow.

## Platform support

Windows, Linux, macOS (junction-aware on Windows, symlink-aware on POSIX).
Tested on Windows 10 / git-bash with Python 3.11+.

## License

MIT — see LICENSE.

## Evidence

The commit-message family pilot (2026-08-10) ran the full pipeline end-to-end:
211 skills discovered (0 errors), 19 groups suggested, council verdict (two
survivors — a merged generator + an untouched executor), golden-output 6/6 match,
G2 benchmark 36/36 cells PASS. Full transcripts and benchmark data in `docs/`.
