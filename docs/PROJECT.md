# PROJECT: skill_gov v3.0 — Skill Lifecycle Governance

**Status:** INCEPTION (interview complete, scope locked 2026-08-10)
**Owner:** Coder CEO (orchestrator) — user is final approver
**Repo:** C:\Users\abhil\Dev\skill_gov  (NOT yet a git repo — see M6)

## Why this project exists

The user cannot tell which skill to use when multiple similar skills exist across
harnesses (e.g. ce-skill vs superpowers vs gstack all covering the same capability).
We are building a v3.0 of `skills-catalog-governance` that solves this by:
1. DISCOVERY — identify every skill across all stores, tagged by store
2. GROUPING — group similar skills into families (automated recall net + mandatory full read)
3. COUNCIL — LLM council reviews every line of every skill in the group
4. MASTER BUILD — council debates and synthesizes ONE master skill (nothing lost)
5. VALIDATE — live head-to-head benchmark: master must beat every source
6. PROMOTE — only on evidence does the master get approved for implementation

This capability does not exist anywhere public (verified 2026-08-10: no SKILL.md
clone-detection/master-build tooling on GitHub, arXiv, agentskills.io spec has no
dedup guidance). We are building something new; proper project methodology applies.

## Locked decisions (interview 2026-08-10, user answers verbatim)

| # | Question | Decision |
|---|----------|----------|
| D1 | Relationship to existing skill | **Extend** skills-catalog-governance into a v3.0 lifecycle skill — discovery + master-build become new phases inside it |
| D2 | Discovery scope | Scan ALL stores: ~/.agents/skills master (211 skills), pi store (~/.pi/agent/skills), Hermes profile skills, AND third-party repos (superpowers/ce/gstack) — tag each skill with its store; external repos are READ-ONLY |
| D3 | What happens to sources | Archive sources in MY stores after promotion; external repos untouched (master lives in my master dir) |
| D4 | Acceptance bar | Head-to-head vs EACH source skill — master must win or tie every benchmark cell (≥3 runs/cell) AND beat the best source overall |
| D5 | Project doc | Yes — this docs/PROJECT.md with milestones/scope/status; SKILL.md stays the authority once shipped |
| D6 | Distribution | **PUBLIC open-source release on GitHub** — other programmers must be able to use this skill when they have a bloated skill list. MIT license, README + usage docs, no user-specific paths/incidents baked in as core rules |

## Non-negotiable inherited rules (from SKILL.md, binding)

- NON-DESTRUCTIVE ONLY: every removal is a MOVE to skills-archive/, never rm -rf
- Council is a MANDATORY quality gate — never skippable (embedded fallback always runs)
- Loss-check is run by the lead (orchestrator), NEVER delegated — single accountable pass +
  a mechanically-different second check
- Repair dispatch carries the COMPLETE numbered defect list, verbatim
- Promotion gates G0-G3 + snapshot → promote (sha256 match) → archive → commit
- Verification Discipline: every claim backed by literal command + literal output
- No VCS fallback: if not a git repo, require snapshot copy + sha256 checksum, print
  "no VCS: snapshot-only" — never silently skip record-keeping

## Milestones

| # | Milestone | Deliverable | Gates | Status |
|---|-----------|-------------|-------|--------|
| M1 | Discovery engine | `detect-skills` phase: scan all stores, emit tagged inventory (store, path, name, desc, sha256) | G0 on output schema; literal scan output | **DONE 2026-08-10** (211 skills, 0 errors; D1-D5 closed, D6 non-bug) |
| M2 | Grouping | Similarity net: all-pairs TF-IDF cosine + word-overlap (pure stdlib), candidates flagged, never decided | Paper-verified method (arXiv:2603.22447); over-flag bias (low threshold ~0.3-0.4) | **DONE 2026-08-10** (28 tests pass; real catalog: 89 candidates / 19 groups; commit + tdd families flagged) → **v3.1 FIXED** over-grouping (strong-pair + size cap): 7 clean groups, mega-group eliminated |
| M3 | Council review | 5-advisor → peer-review → chairman per group; every line of every source read | Council transcript artifact; loss-check | **DONE 2026-08-10 (pilot: commit family)** — verdict: TWO survivors (generator merge caveman-commit+writing-commit-messages; ce-commit untouched); golden-output experiment is the gate before absorption |
| M3.5 | Golden-output experiment | Verify single `style` param reproduces both generator formats on fixed diffs | 6/6 pairs match → ABSORPTION AUTHORIZED | **DONE 2026-08-10** — 6/6 match; absorption authorized; results in docs/golden-output-experiment-20260810.md |
| M4 | Master build | ONE staged master per group, staged OUTSIDE live root | G0/G1/G3 on draft; portability covenant | **DONE 2026-08-10** — draft at skills-merge-drafts/caveman-commit.SKILL.md (180 lines); G0 5/5 (version quoted after fix); covenant clean; golden-output 5/5 pairs reproduced |
| M5 | Live benchmark | Head-to-head vs EACH source, ≥3 runs/cell, with/without baseline | D4 bar; benchmark.json evidence | **DONE 2026-08-10** — G2 confirmation: 36/36 cells format+content PASS (3 runs/cell, 4 conditions incl. no-skill baseline); master strict superset; benchmark.json has run counts |
| M6 | VCS & promotion | git init (or explicit no-VCS snapshot+sha256); snapshot → promote → archive my-store sources → record | sha256 match; literal outputs | **DONE 2026-08-10** — git init'd (a173bb9); promoted caveman-commit v2.0.0 to live (sha256 f81bab01... draft==live MATCH); post-promotion re-audit PASS (frontmatter parses, detect-skills 211/0); vendored herdr tree untouched per council |
| M7 | Public release | LICENSE (MIT), README (problem statement, install, quickstart, architecture), sanitize user-specific paths (C:\Users\abhil, ~/.agents, incident specifics stay in references/ as evidence NOT core rules), portability check (windows/linux/macos, junction-aware but not Windows-only), publish to GitHub | G0 on all docs; fresh-clone install test on a clean machine profile | **DONE 2026-08-10** — LIVE at github.com/abhilash333naidu/skills-catalog-governance (PUBLIC); LICENSE MIT, README, SKILL.md v3.0.0, sanitized, cross-platform verified |
| v3.2 | Harness-detecting installer | `install` subcommand + install.sh + install.ps1; harness detection (opencode/pi/claude/codex/omp/hermes/master/gstack); interactive picker; idempotent (no silent overwrite; --yes + timestamped .bak) | parse-check install.sh/install.ps1; unit tests for picker + install paths | **DONE 2026-08-11** (d85d3d2) — spec docs/spec-installer-20260810.md; picker unit-tested; --target CLI path tested |
| v3.2.1 | MSYS path fix | cygpath conversion for native python under git-bash | install.sh smoke test | **DONE 2026-08-11** (da690d4) |
| v3.2.2/3 | One-liner URL fixes + branch rename | README one-liners point at correct branch; default branch master→main | URL fetch 200s | **DONE 2026-08-11** (c984564, 64ef66b) |
| v3.2.4 | One-liner curl\|bash fix (R2) | install.sh survives pipe execution; picker fires under curl\|bash | non-tty pipe install PASS; interactive picker selects only chosen harness; file-mode regression PASS; 35 tests; check-package PASS | **DONE 2026-08-11** (9333c34) — Defect 1: BASH_SOURCE[0] unbound under set -u in pipe mode (one-liner died instantly); Defect 2: /dev/tty reconnect probed by (exec 0</dev/tty) not -r permission bit (open fails ENXIO in no-tty contexts) |

## Refinement backlog execution (P1 — correctness, 2026-08-11)

Backlog source: docs/HANDOFF-20260811.md. P1 = hard bugs first; P2/P3 queued.

| Item | Result | Evidence |
|---|---|---|
| R1 install.ps1 end-to-end | **DONE — PASS** | pwsh 7.6.4; local-checkout path install → status PASS, check_package PASS; real one-liner `irm ... \| iex` with isolated HOME → detected pi harness, installed, check_package PASS; installed SKILL.md sha256 == repo (bbf6a035...) |
| R2 one-liner picker tty | **DONE — bug found + fixed (v3.2.4)** | curl\|bash died instantly (BASH_SOURCE[0] unbound, set -u); fix shipped; 3 acceptance tests PASS (non-tty pipe install, interactive picker via WSL pty selects only chosen harness, file-mode regression) |
| R3 multi-harness "all" | **DONE — PASS** | install --yes with 4 fake harnesses (opencode/pi/claude/master): all installed, aggregate check_package PASS (4 results), zero errors; per-harness check-package all PASS |
| R4 promotion rollback | **DONE — PASS** | install v1 → install --yes (creates .bak) → corrupt (rm SKILL.md + script) → check FAIL detected → restore .bak → check PASS; restored sha256 == repo (bbf6a035...) |
| R10 PROJECT.md spine | **DONE** | v3.2/v3.2.1/v3.2.2/v3.2.3/v3.2.4 milestone entries added above |
| R5 grouping heuristic 2nd catalog | **DONE — VALIDATED** | tech-leads-club/agent-skills registry (88 real skills, 0 junctions): 51 candidates / 7 groups / 0 oversized @ threshold 0.4, max 8. Deploy family (4/4) + figma/react/subagent-creator/rfc pairs all genuine; security trio (best-practices/ownership-map/threat-model) correctly NOT grouped (cos≤0.44, overlap≤0.37 — distinct workflows sharing vocabulary). No code change needed |
| R6 real .usage.json | **DONE — bug found + fixed (v3.2.5, commit 09d63f6)** | REAL Hermes shape is nested objects ({"skill": {"use_count": N, ...}}) — loader only accepted flat ints → 163-entry real file yielded 0 counts (silent no-op). Fix reads use_count from nested objects; flat back-compat; fail-open kept. Verified: 40 tests (5 new), real file → 163 counts, detect-skills end-to-end enrichment works |
| R7 G2 judge limitation | **DONE — rubric + loud note (commit 884c77f)** | references/g2-judge-rubric.md: scoring axes, cell verdicts, ≥3 runs/cell bar, cross-model judge procedure; SKILL.md M5 carries loud correlated-judge honesty note (mandatory in every benchmark artifact). benchmark.json already had an honesty field — now the gate itself documents it |
| R8 council verdict schema | **DONE — commit 78c89e3 (v3.2.6)** | validate-council-verdict subcommand + schemas/council-verdict.schema.json (verdict enum MERGE/SPLIT/RECATEGORIZE/KEEP_SEPARATE/NO_MERGE, survivors[], recategorizations[], absorbed[], gates_passed[]); stdlib YAML-list parser; required_payload updated. Verified: 47 tests (7 new), check-package PASS, legacy prose verdict → clean machine-readable FAIL |
| R9 oversized-group guidance | **DONE — commit 8c7cacd** | SKILL.md M3 now has explicit oversized-group handling: do not council a group over max-group-size; re-run with lower threshold; split along single-signal seams; only clean ≤max sub-groups go to council. Body trimmed to 499 lines for G0 |
| R12 version reconciliation | **DONE — commit 8c7cacd** | SKILL.md frontmatter version 3.1.0 → 3.2.6; description updated. G0/G1/G3/G3.5 all PASS |
| R11 real .usage.json fixture | **DONE** | tests/fixtures/usage-real-shape.json (real Hermes shape, anonymized) + loader test asserting use_count 39/0/131 from the committed fixture. 48 tests pass, check-package PASS |
| R13 prereq doc + enforcement (v3.2.7) | **DONE** | README Requirements section moved above Install (Python 3.10+, no-git Windows zip fallback, PowerShell); install.sh + install.ps1 probe the interpreter version BEFORE invoking Python (fail-closed plain error, was a raw SyntaxError traceback on 3.8/3.9); catalog_governance.py top-of-file guard emits structured JSON FAIL on <3.10 (covers direct invocation skipping the installer); 2 new tests (old-version probe → FAIL JSON + exit 1) |

## Refinement backlog: ALL CLEAR (P1 + P2 + P3, 2026-08-11)

R1-R12 all done/verified. The 7 clean groups are clear to run via the council
pipeline: understand-*, caveman-help/ponytail-help, careful/guard,
context-restore/save, qa/qa-only, tdd-iron-law/compact,
web-design-guidelines/writing-guidelines.

## Open questions (non-blocking)

- Which groups to run first (ce-skill / superpowers / gstack family is the pilot candidate)
- Whether ~/.agents/skills master becomes the git repo or the skill_gov working dir does
- Skill store dedup junctions must be resolved before counting (junction-aware scan)

## Evidence log

- 2026-08-10: Verified SkillClone paper (arXiv:2603.22447, NTU, targets ASE 2026) — all
  benchmark numbers Claude Desktop quoted match the paper verbatim; replication package
  NOT yet public; no other purpose-built method exists. Method choice: flat TF-IDF +
  word-overlap as Stage-1 recall net; full-content read stays mandatory (Stage 2).
