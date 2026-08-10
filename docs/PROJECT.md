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
| M2 | Grouping | Similarity net: all-pairs TF-IDF cosine + word-overlap (pure stdlib), candidates flagged, never decided | Paper-verified method (arXiv:2603.22447); over-flag bias (low threshold ~0.3-0.4) | **DONE 2026-08-10** (28 tests pass; real catalog: 89 candidates / 19 groups; commit + tdd families flagged) |
| M3 | Council review | 5-advisor → peer-review → chairman per group; every line of every source read | Council transcript artifact; loss-check | **DONE 2026-08-10 (pilot: commit family)** — verdict: TWO survivors (generator merge caveman-commit+writing-commit-messages; ce-commit untouched); golden-output experiment is the gate before absorption |
| M3.5 | Golden-output experiment | Verify single `style` param reproduces both generator formats on fixed diffs | 6/6 pairs match → ABSORPTION AUTHORIZED | **DONE 2026-08-10** — 6/6 match; absorption authorized; results in docs/golden-output-experiment-20260810.md |
| M4 | Master build | ONE staged master per group, staged OUTSIDE live root | G0/G1/G3 on draft; portability covenant | **DONE 2026-08-10** — draft at skills-merge-drafts/caveman-commit.SKILL.md (180 lines); G0 5/5 (version quoted after fix); covenant clean; golden-output 5/5 pairs reproduced |
| M5 | Live benchmark | Head-to-head vs EACH source, ≥3 runs/cell, with/without baseline | D4 bar; benchmark.json evidence | **DONE 2026-08-10** — G2 confirmation: 36/36 cells format+content PASS (3 runs/cell, 4 conditions incl. no-skill baseline); master strict superset; benchmark.json has run counts |
| M6 | VCS & promotion | git init (or explicit no-VCS snapshot+sha256); snapshot → promote → archive my-store sources → record | sha256 match; literal outputs | **DONE 2026-08-10** — git init'd (a173bb9); promoted caveman-commit v2.0.0 to live (sha256 f81bab01... draft==live MATCH); post-promotion re-audit PASS (frontmatter parses, detect-skills 211/0); vendored herdr tree untouched per council |
| M7 | Public release | LICENSE (MIT), README (problem statement, install, quickstart, architecture), sanitize user-specific paths (C:\Users\abhil, ~/.agents, incident specifics stay in references/ as evidence NOT core rules), portability check (windows/linux/macos, junction-aware but not Windows-only), publish to GitHub | G0 on all docs; fresh-clone install test on a clean machine profile | PENDING |

## Open questions (non-blocking)

- Which groups to run first (ce-skill / superpowers / gstack family is the pilot candidate)
- Whether ~/.agents/skills master becomes the git repo or the skill_gov working dir does
- Skill store dedup junctions must be resolved before counting (junction-aware scan)

## Evidence log

- 2026-08-10: Verified SkillClone paper (arXiv:2603.22447, NTU, targets ASE 2026) — all
  benchmark numbers Claude Desktop quoted match the paper verbatim; replication package
  NOT yet public; no other purpose-built method exists. Method choice: flat TF-IDF +
  word-overlap as Stage-1 recall net; full-content read stays mandatory (Stage 2).
