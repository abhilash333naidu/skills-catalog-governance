---
name: skills-catalog-governance
description: "Use when cleaning skills catalog: archive, merge, verify. Governs merging duplicate skill families into ONE survivor via council + loss-check + G0-G3 gates + safe promote. v3.2 fixes: over-grouping (strong-pair + group-size cap), usage-aware discovery, real .usage.json shape. Self-contained as one packaged folder; package completeness is verified before use. Prereq guard: fail-closed Python 3.10+ check in installers + script."
version: "3.2.7"
author: Coder CEO
license: MIT
platforms: [windows, linux, macos]
metadata:
  status: released
  base_version: "2.1.0-draft"
  released: 2026-08-10
  source: gap-analysis + external NotebookLM review + first full lifecycle pilot run (commit family)
  promotion_status: "PROMOTED — v3.0 lifecycle pipeline piloted end-to-end on commit family (M1-M6), promoted to live"
---

# Skills Catalog Governance

Class-level workflow for maintaining a Hermes profile's skills catalog: archive never-used
skills, merge duplicate skills into survivors, remove nested duplicates, and verify with
literal command outputs. Distilled from the coder_ceo audit chain (planner → executor →
reviewer) that produced `skills/.audit_plan.md` + `skills/.audit_manifest.json` + the
sibling `skills-archive/` directory.

> **OPEN-SOURCE PACKAGING GUARANTEE:** this skill is self-contained when its complete
> package is installed: `SKILL.md`, the listed `references/` files, `schemas/`, and
> `scripts/`. Run `python3 scripts/catalog_governance.py check-package --root .` before
> trusting the package; a missing referenced file is a hard failure, not an optional
> warning. It has NO hard dependency on any other skill. The council in Step 2 is a
> MANDATORY quality gate that ALWAYS runs: it uses the `llm-council` skill only if the
> harness happens to have it, otherwise the Embedded Council Procedure
> (`references/embedded-council-procedure.md`) runs the same 5-advisor → peer-review →
> chairman flow inline. The council is never skipped, and nothing silently breaks when a
> harness lacks a related skill.

> **v2.1.0-draft NOTICE:** this revision adds 10 new/changed items (marked `[NEW]` or
> `[CHANGED]` below) from a gap analysis + an external NotebookLM expert-review pass
> (2026-08-10) + an in-house LLM-council design review (2026-08-10). None of the new gates/procedures have a G2-style empirical validation run
> yet — they carry the same intent as G0/G1/G3 but are UNPROVEN until run once for real.
> Do not treat `[NEW]` items as "PROVEN" the way G0's 1,342-char catch or G2's 15/15-vs-9/15
> result were — those are real incidents; these are not, yet. Promote to live only after:
> (1) this file sits in a directory literally named `skills-catalog-governance` (current
> staging path breaks the G0 name==dir check), (2) a human read-through, (3) ideally one
> real run of each `[NEW]` gate with literal output captured.

> **v3.0 RELEASE NOTE (2026-08-10):** this revision adds the full LIFECYCLE pipeline — M1
> discovery → M2 grouping → M3 council → M3.5 golden-output → M4 master-build → M5 benchmark
> → M6 promotion — in `scripts/catalog_governance.py` (`detect-skills`, `detect-groups`),
> piloted end-to-end on the commit-message family and PROMOTED to live. Pilot: 211 skills,
> 19 groups, council verdict (two survivors), golden-output 6/6, G2 36/36 cells. Evidence in
> `docs/` (see References).

## Lifecycle Pipeline (v3.0, BINDING for new merges)

The v3.0 pipeline extends the legacy archive/merge workflow. For a NEW group being
consolidated, run these phases IN ORDER. Each phase is gated by the orchestrator (lead),
never by the writer.

### M1 — Discovery (`detect-skills`)

Scan skill stores and emit a tagged inventory. Stdlib-only, fail-closed.

```bash
python scripts/catalog_governance.py detect-skills --output inventory.json
```

- Default stores (only when present): `~/.agents/skills` (master), `~/.pi/agent/skills`
  (pi), `~/.hermes/skills` (hermes). Explicit `--stores` paths are tagged `external`
  with `read_only: true` regardless of location (conservative).
- Junction/symlink handling: skip symlink/reparse-point skill DIRECTORIES (mirrors);
  dedupe by canonical path (same real skill appears once, first-seen store wins);
  BUT resolve a store ROOT that is itself a symlink/junction and scan its real target.
- Output schema per entry: `{store, path, name, description, sha256}`. `name` from
  frontmatter with dir-name fallback; `description` empty-string fallback; sha256 over
  exact raw SKILL.md bytes.
- Frontmatter: YAML-style `---` block only. Plain-scalar continuation lines join with a
  single space; `|` literal block scalars preserve `\n` (YAML-spec-conformant — do NOT
  flatten them; downstream consumers must normalize whitespace before comparing).
- Fail-closed: unreadable/malformed file → error entry, never a guess. Status FAIL if
  any error, PASS otherwise.

### M2 — Grouping (`detect-groups`)

All-pairs similarity over the M1 inventory. Candidates only — NEVER a merge decision.

```bash
python scripts/catalog_governance.py detect-groups --inventory inventory.json --threshold 0.30 --overlap-threshold 0.50
```

- Method (paper-verified, arXiv:2603.22447 SkillClone): flat TF-IDF cosine + word-overlap
  (|intersection| / min lens). Stdlib-only (no sklearn/numpy).
- Over-flag bias: default cosine threshold 0.30 and word-overlap threshold 0.50 (both
  configurable; a false positive = one wasted read; a false negative = a missed group,
  worse). Flag if cosine >= threshold OR overlap >= overlap-threshold.
- Output: candidates (a, b, cosine, word_overlap, flagged_by) + `suggested_groups`
  (connected components) — a SUGGESTION for M3 scope, not a decision.
- GROUPING RULE (v3.1): suggested_groups are built from STRONG pairs ONLY — both
  signals must agree (cosine AND overlap). Single-signal pairs, even high-cosine,
  share vocabulary not function (e.g. caveman-commit vs ce-commit at 0.68 are
  generator vs executor — a council-decided split) and never bridge groups.
  `--max-group-size` (default 8) caps groups; oversized components are reported in
  `oversized_groups` for manual review, never treated as clean merge groups.
- Pilot: 211 skills → 22,155 pairs → 89 candidates → 7 clean groups (v3.1; the
  v3.0 24-member mega-group chaining ce-*/design-*/ios-*/qa is eliminated).

### M3 — Council review (per group)

For each suggested group: 5 advisors → 5 anonymous peer reviews → chairman synthesis.
MANDATORY — never skippable (see Embedded Council Procedure). Every line of every source
read. Output = RECOMMENDATION + provenance table + portability covenant. The council may
recategorize members (e.g. "generator vs executor") before any merge. Oversized group
handling (R9 — `oversized_groups` in a detection report): a group over `--max-group-size`
(default 8) means the recall net over-bridged families sharing vocabulary but not function.
DO NOT council an oversized group — the every-line guarantee degrades past
~6-8 members. Action: (1) re-run with a LOWER threshold; raise the cap only for one genuine
oversized family (rare). (2) Split along single-signal seams — cosine-only or overlap-only
links to the core are likely another family (verified: security trio stayed apart ≤0.44/≤0.37).
(3) Only clean ≤max sub-groups go to council; never promote oversized as-is, never drop
members silently. Same failure class as v3.0's 24-member mega-group (see pilot note).

### M3.5 — Golden-output gate

For generated-output skills (formatters, generators, style systems): feed 2-3 fixed
inputs through each source, then through ONE candidate master contract, and verify the
single parameterized contract reproduces every source output byte-for-byte (modulo
whitespace). 6/6 pairs = ABSORPTION AUTHORIZED. This converts the council's
shared-core premise from assertion to evidence. Pilot: commit-family 6/6 match.

### M4 — Master build (staged)

Delegate synthesis to a sub-agent; stage the draft OUTSIDE the live root in a REAL
top-level directory (never a junction target — verify `os.path.islink()` first).
- G0 (name==dir, desc ≤1024, no XML brackets, <500 lines), G1 security scan, G3 version
  discipline (QUOTED SemVer + `merged-from:` provenance list). Portability covenant:
  no AskUserQuestion, no `/ce-*`, no `$GSTACK_BIN`, no telemetry.
  NOTE: G0's name==dir check is against the INSTALLED directory. The published repo
  (skills-catalog-governance) passes; a dev copy under a differently-named folder
  (e.g. skill_gov) fails the check until renamed — that is expected and documented.

### M5 — Live benchmark (G2)

Head-to-head vs EACH source: master must win or tie every cell AND beat the best source
overall. ≥3 runs per cell (LLM nondeterminism); include a no-skill baseline. Judge =
format conformance + content completeness. Record `benchmark.json` with run counts.
Single-pass is indicative, NOT proof — the ≥3-run confirmation is the standing gate.
Pilot: 36/36 cells PASS, master strict superset of both sources.

**G2 JUDGE LIMITATION (loud, binding):** the G2 judge is typically the SAME base model
family that GENERATED the outputs (correlated judge — e.g. DeepSeek-V4-Pro judging
DeepSeek-V4-Pro output). This tests instruction-set coverage and format conformance,
NOT model-independent quality; a correlated judge can systematically favor the output
style it was prompted to produce. Any benchmark.json or G2 evidence MUST carry the
honesty note from `references/g2-judge-rubric.md` (verbatim or pointer); a benchmark
without it is not a governed G2 artifact. A truly independent validation requires a
DIFFERENT provider/model as judge (rubric + cross-model procedure in that file).

### M6 — Promotion

git init the governing repo (or explicit no-VCS snapshot+sha256 fallback); snapshot →
promote → archive my-store sources → commit, each with literal output. Post-promotion
re-audit: re-verify the LIVE file hash matches the draft, frontmatter parses,
detect-skills still passes over the whole catalog. External/vendored sources are NEVER
edited — absorb content in, leave the parent tree whole.

## Phase 1 Hardening Toolkit (authoritative execution contracts)

Full execution contracts moved to `references/hardening-toolkit.md` (progressive
disclosure). Bindings kept here — these are the hard boundaries:

- All validation commands are read-only; no catalog move occurs unless a plan has passed
  completely and the operator supplies both `--apply --yes`.
- Campaign states: `PREFLIGHT → COUNCIL/DRAFT → LOSS_CHECK → APPROVAL → PROMOTION →
  ARCHIVE → POST_AUDIT`. A failed or stuck state is never treated as complete.
- `apply-moves` refuses collisions, symlinks/junctions, missing `SKILL.md`, and unexpected
  state changes; it never deletes or overwrites. Partial runs resume from the journal.
  A pre-existing lock is never silently removed; retry with `--recover-stale-lock` only after
  verifying its recorded PID is no longer alive.
- **`[CHANGED]` verify-approval is bound to MECHANICAL STATE, not prose:** a supplied
  `--loss-report` makes it RE-RUN the loss-check live against draft + every source and
  refuses (`FAIL`) unless loss-check is `PASS`, every recorded draft hash equals the bound
  approval hash, no source changed since loss-check, and the live re-check reproduces the
  recorded missing-heading/command sets exactly. A dropped defect class can no longer hide
  behind a stale or edited brief (closes the 6-of-5 handoff leak + 71-vs-72 drift class).
  Use it on every approval.
- Verification record: command lines, outputs, exit codes, timestamps, hashes, and JSON
  reports all live under `run-record/`. A prose claim without its evidence artifact is not
  a verified claim.

## When to Use

- Executing a skills-catalog cleanup plan (`.audit_plan.md` + `.audit_manifest.json` style artifacts).
- Planning or running a duplicate-skill merge, unused-skill archive, or nested-dup removal.
- Any task that moves skill dirs out of the active skills root or merges SKILL.md content.

## Catalog Types (audit model differs — know which one you are in)

| | **Hermes profile catalog** | **External-consumer clone catalog** (e.g. `.agent-skills`) |
|---|---|---|
| Consumers | Hermes prompt (scans `skills/`) | OpenCode / Claude Code / Codex / Gemini (each globs `skills/` explicitly) |
| Usage data | `.usage.json` per-skill counts | NONE — deadness must be INFERRED from wiring/references |
| Archive target | sibling `skills-archive/` | sibling OUTSIDE the repo, e.g. `.agent-skills-archive/` (zero git noise + removed from all consumers' views) |
| Git safety | n/a (profile, no git) | moving UNTRACKED dirs = zero git impact; moving TRACKED = `D` status (recoverable `git checkout`); NEVER commit unless asked |
| Merge appetite | 10 merges in Phase 1 run | **NO merges** — merging tracked+untracked mixes dirties tracked skills (upstream-pull conflicts); dense cross-ref webs have no umbrella |
| Bias | aggressive (144→72) | CONSERVATIVE — the user already curates clones by hand (deletes/adds); only archive what is PROVABLY dead |
| Resume evidence source | `[CHANGED]` no git → checkpoint file (see Session-Resume Discipline) | `git log` / `git status` (repo exists) |

**Deadness inference for a clone (no usage data):** case-insensitive cross-reference scan of the
WHOLE repo (including user-modified AGENTS.md/CLAUDE.md/README.md — they are WIRING, not
boilerplate!) plus all home configs (`~/.claude`, `~/.config/opencode` incl. legacy, `~/.codex`,
`~/.gemini`, `~/.agents`). A skill is ACTIVE if referenced in any command file
(`.claude/commands/*.md`, `.gemini/commands/*.toml`), hook, agent profile, plugin manifest,
opencode.json `skills.paths`, or the global AGENTS.md. Verify consumer wiring per-consumer
before choosing the archive location — never assume a hidden-dir exclusion exists (OpenCode
globs the path explicitly; `.claude-plugin/plugin.json` sets `"skills": "./skills"`).

## Non-Negotiable Rules (binding)

1. **NON-DESTRUCTIVE ONLY**: every catalog removal is a MOVE into `skills-archive/` (sibling
   of the skills root). Never `rm -rf` a skill dir. Catalog content writes are limited to
   survivor `SKILL.md` files (merges), shared-skill files (append only), and archive moves.
   Governance evidence writes are allowed only under the campaign's `run-record/` plus its
   lock/journal artifacts; `/tmp` backups remain allowed for safety. The evidence and lock
   files must never be inside the active catalog root.
2. **Survivors keep identity**: dir, frontmatter `name:`, and position in the active root.
   Merge sources move to archive ONLY after their content is absorbed.
3. **PATH VALUES, never keys**: use the manifest's absolute PATH VALUES for archive moves.
   Known aliases: `audiocraft-audio-generation` → `mlops/models/audiocraft`,
   `segment-anything-model` → `mlops/models/segment-anything`,
   `creative-ideation` → `creative/creative-ideation` (dir name ≠ frontmatter name ≠ manifest key).
4. **Any move preflight error — STOP before mutation.** Never force-overwrite an existing
   archive path, continue after a missing source, or treat a `SKIP` line as harmless. Use
   `scripts/catalog_governance.py preflight-moves`; it fails closed and creates no
   destination directories until the complete plan passes.
5. **Shared skills are ADDITIVE ONLY**: append a new section at the END; never touch the
   frontmatter, never reorder/reword/delete existing content. The additive-only rule wins over
   the description-extension rule for shared files.
6. **`[NEW]` Dangling references are FLAG-ONLY, never auto-fixed**: when a command file, hook,
   or `AGENTS.md`/`CLAUDE.md` still names a skill you just archived, report it in the MANIFEST
   and stop. Never edit the referencing file and never restore the skill without the user's
   explicit call — the referencing file is user-owned wiring, not the agent's to rewrite.

## Timeout & Escalation Discipline (binding, cross-cutting) `[NEW]`

Applies to every step that can hang without a defined exit: council advisor/chairman calls,
G2 empirical A/B runs, sub-agent Writer/Repair dispatch, any external-review query (Claude
Desktop, NotebookLM, etc.).

- Every dispatched call gets an explicit timeout before it is sent. No open-ended "wait
  until it answers."
- Poll on a fixed cadence; log each poll. Silence past 2× the expected duration with no
  error surfaced is itself a signal — stop polling silently, tell the user status is stuck,
  offer to keep waiting or abandon/retry.
- Repair-loop cap: **max 3 rounds** per defect list (ties to Repair Dispatch, Step 5 below).
  Round 3 still failing → escalate to user with the outstanding defect list; do not start a
  4th round automatically.
- A stuck step never silently becomes a skipped step — report it as stuck, not as done.

## Council Per-Group Merge Governance (BINDING for duplicate-family merges)

User-mandated model for reducing merged families (debug/tdd/commit/review etc.):
ONE merged master skill per group, produced by the `llm-council` methodology,
staged OUTSIDE the live root, loss-checked, and promoted only on user approval.
This is the governing pipeline for ANY merge that consolidates 2+ skill dirs
into one survivor — the legacy 4-Phase Workflow (`references/4-phase-workflow.md`)
covers manifest-driven archive-only runs; do NOT use it to merge duplicate families.

Pipeline (each stage gated by the orchestrator, never the writer):
1. **Scope**: ONE group at a time. Brief must pin the group by dir name and
   EXPLICITLY forbid re-counciling settled scope (OMP once counciled the whole
   reduction plan — a hard delegation-scope trap).
2. **Council** → verdict: 5 advisors → 5 anonymous peer reviews → chairman. **MANDATORY
   — quality gate, never skippable.** A merge without a council is not a governed merge.
   Implementation: prefer the `llm-council` skill if the harness has it (richer transcript/
   report machinery); otherwise run the council directly from the embedded procedure
   (`references/embedded-council-procedure.md`). Either way A council runs — the
   embedded copy is the guaranteed fallback so the council is always possible and always
   executed, never traded away for "convenience." Output = RECOMMENDATION + provenance
   table (section → source) + portability covenant (no AskUserQuestion, /ce-*, $GSTACK_BIN,
   telemetry). **`[NEW]` Timeout**: apply the per-step timeout above; a hung advisor call
   is a stuck council, not a skipped one — surface it, don't silently drop the step.
3. **Writer** (delegate the synthesis to ANY appropriate available sub-agent harness —
   OMP, opencode, codex, a Hermes sub-agent, etc.; choose what is healthy/appropriate at the
   time, do NOT hardcode one vendor) produces the staged draft in
   `skills-merge-drafts/<survivor>.SKILL.md`. NEVER write to the live master before user
   approval. **Staging-path safety (junction-back risk):** the drafts dir MUST be a real
   top-level directory that no harness globs and that no junction points at — a draft
   accidentally staged inside a junction target (e.g. `.claude/skills` → master) leaks
   WIP to every harness that mirrors it. Verify `os.path.islink()` (or reparse-point flag)
   on the drafts dir before writing; if it resolves somewhere harnesses read, use the
   documented flat drafts dir instead.
4. **Loss-check** (orchestrator runs the FULL comparison — never delegate): a SINGLE
   accountable pass by the lead, not a cluster — delegating the verify to a sub-agent makes
   it both the reviewer and the judge, so you end up re-verifying the verifier. Read EVERY
   original in full, diff against the draft, enumerate defect classes as a numbered list.
   Multiple agents do NOT improve trust here; one accountable pass does. (Full content is
   read in Step 1 for Step 2's council, and re-read here for the loss-check — same matter,
   two jobs.) **Pair the manual read with a SECOND, mechanically-different check** (external
   review finding): an   automated word-overlap / section-heading diff between each original
   and the draft, so a fatigued or rushed single pass is not the only net. Run the
   authoritative helper and save `run-record/loss-check.json`; it records hashes, overlap,
   missing headings, and missing fenced commands. The two methods disagree → investigate;
   agree-clean → high confidence. Manual remains authoritative; the mechanical check exists
   because a single pass was once wrong despite being accountable

   (6 classes found, 5 dispatched).
5. **Repair dispatch — CLOSURE DISCIPLINE (the gap that leaked a real defect)**: the
   repair brief MUST carry the COMPLETE numbered defect list, verbatim, every
   item. Never summarize, never drop the low-severity-looking ones. Loss-check
   found 6 classes, brief carried 5, and the 6th (ce-debug's parallel
   investigation option) shipped missing — the exact failure this rule closes.
   After repair, re-verify EVERY item in the original list, not just the ones
   the writer claims to have fixed. Repair may go to ANY agent harness (same
   choice rule as Step 3); the closure re-verify is done by the lead regardless.
   **`[NEW]` Cap at 3 repair rounds** (see Timeout & Escalation Discipline) — unresolved
   after round 3 escalates to the user instead of looping indefinitely.
6. **Promotion gates** (see `references/promotion-gate-merge-to-live-2026-08.md`):
   Gate A description trigger superset (whitespace-normalized bag-of-words +
   pluralization false-positive tolerance) and Gate B the 3 black-box scenarios
   (non-reproducible taxonomy, wrong-prediction symptom-risk, 3-failed-fix
   architecture STOP) — then snapshot → promote (sha256 match) → archive →
   git commit, each with literal output. **`[CHANGED]`** Gate A's trigger-superset must
   not push the survivor's `description:` past ~800 chars in practice — see the G2
   description-budget note in `references/hardening-gates.md`; the 1024-char G0 ceiling is a hard fail, not a target.
7. **Post-promotion re-audit** (the 6/5 leak was caught here): after commit,
   re-run the FULL loss-check defect list against the LIVE file, plus the
   snapshot-vs-archived hash comparisons. Defects found == defects dispatched
   == defects verified, all three numbers, or the promotion is not closed.
   **`[NEW]`** Also run the G3.5 dangling-reference scrub (see `references/hardening-gates.md`) here.

Manager decision (binding): delegate the MERGE/synthesis to a sub-agent;
NEVER delegate the verify gates, the loss-check, the promotion surgery, or the
post-promotion re-audit — those are evidence territory the lead runs itself.

## Embedded Council Procedure (MANDATORY fallback — guarantees the council always runs)

Full procedure moved to `references/embedded-council-procedure.md`: 5 advisors, 5 anonymous
peer reviews, 1 chairman, verdict structure, and the honesty note (the advisors are LENSES
on one correlated base model, not five independent models — do not claim "independent model
diversity"). Binding rules retained here:

- The council is a non-negotiable quality gate (Step 2) and is NEVER skipped for
  convenience. Prefer `llm-council` if the harness has it; else run this inline.
- Output = RECOMMENDATION + provenance table (section → source) + portability covenant,
  saved as `skills-merge-drafts/<group>-council-verdict.md` (the artifact the writer
  consumes and the loss-check checks against).

## Hardening Gates G0-G3 (BINDING, external benchmark 2026-08)

Adopted after benchmarking against the real ecosystem (full evidence:
`references/external-benchmark-gates-2026-08.md`). Every
merge-group pipeline runs G0+G1+G3 on every staged draft; G2 is the post-merge
battle-tested probe (prototype first, then standing gate). `[NEW]` G1b, G3.5, and G4
below are proposed additions — same enforcement intent, no live-incident proof yet.

**Gate → source mapping** (each gate's provenance, so "benchmarked" is evidence, not a claim):

| Gate | Adopted from | Notes |
|---|---|---|
| G0 name==dir, ≤64ch, refs depth | agentskills.io spec (24K★ official standard) | spec is the canonical file-format authority |
| G0 desc ≤1024, no XML `<>` | agentskills.io spec + Claude Code frontmatter rules | XML-angle-bracket rule = prompt-injection surface |
| G1 security patterns | tech-leads-club/agent-skills (registry vetting) + Snyk audit + arXiv:2605.11418 | anchor stats verified; scanner is our own regex first-pass |
| G1b `[NEW]` semantic/adversarial framing check | NotebookLM review 2026-08-10 (arXiv semantic-hijack: 86% retrieval win, 77.6% selection bias, 36.5-100% evasion) | proposed — no live run yet, LLM-judged, costs a call |
| G1 `[NEW]` lockfile cross-check | NotebookLM review 2026-08-10 (~30% skills w/ outdated pkg; 40% silent failures = transitive deps) | proposed — check declared deps against actual lockfile |
| G2 with/without A/B | darkrishabh/agent-skills-eval + agentskills evaluation loops | judge-graded; ≥3 runs/cell per evals literature |
| G2 dedup bands (0.95/0.90/0.75) | NVIDIA SkillEvaluator tier-2 | cosine similarity classification, optional |
| G3 SemVer + provenance | agentskills #415 (version field) — our merged-from addition | tied to git-versioned master |
| G3.5 `[NEW]` dangling-reference scrub | NotebookLM review 2026-08-10 + own pitfall precedent ("dangling refs = flag-only") | proposed — codifies an existing pitfall as a standing gate |
| G4 `[NEW]` promotion rollback | gap analysis 2026-08-10 (no rollback procedure existed) | proposed — reuses material G3 already produces (snapshot+hash) |
| snapshot→promote→archive→commit | skill-compact backup/restore | the non-destructive ordering |

Gate G0/G1/G3 are ours-in-the-small (the *scan rules/scripts* are our own), sourced from
the standards — the mapping above shows which standard each constraint derives from.

Full gate bodies (G0 spec-conformance, G1 security scan, G1b semantic framing, G2 empirical
A/B, G3 version discipline + non-git fallback, G3.5 dangling-reference scrub, G4 revert
promotion) live in `references/hardening-gates.md`. Load it before running any gate. Key
standing facts: G2 VALIDATED to standing 2026-08-09 (with_skill 15/15 vs without 9/15, serial
single-model to avoid the gateway's parallel wedge — a single-pass per-cell score is
indicative, not proof; repeat ≥3 runs/cell for rigor); G0 PROVEN (caught a 1,342-char
description → trimmed to 936). `[NEW]` additions G1b/G3.5/G4 remain PROPOSED until each has
a real run with literal output.

## The 4-Phase Workflow (legacy manifest-driven archive-only path)

Legacy path moved to `references/4-phase-workflow.md`. Use it ONLY for manifest-driven
archive-only runs (finding → manifest → archive → verify); do NOT use it to merge duplicate
families — that is Council Per-Group Governance only. Core discipline: Phase 0 pre-flight
gates abort the whole run on any mismatch; Phase 2 archive uses the fail-closed helper
(`preflight-moves` → reviewed `apply-moves --apply --yes`, journal-backed); Phase 3
post-flight verification re-measures the end-state independently; the G3.5 dangling-reference
scrub runs as the final step.

## Pitfalls & Operational Details

Real incident catalog (every pitfall hit in production) + junction-back/Windows execution
detail moved to reference files for progressive disclosure:
- `references/pitfalls.md` — every real pitfall (rogue post-final subagent, truncated
  verification output, fuzzy-patch text loss, junction-link moves, phantom refs, etc.)
- `references/operational-details.md` — cross-harness consolidation + Windows/git-bash
  execution notes
Load the relevant reference when the situation matches; do not read them by default.

## Session-Resume Discipline (multi-session campaigns)

A catalog campaign routinely spans sessions. When a user resumes and asks "where did we
leave off", do NOT treat the last handoff prompt as ground truth — handoffs go stale and
may describe commits that never landed. Before continuing ANY in-flight step:

**If the governing tree is a git repo** (external clone catalogs — see Catalog Types):
1. `git log --oneline -8` on the governing repo + `git log -1 --format="%h %ci %s"` — the
   real last commit and its time, not the narrative.
2. `git status --short` scoped to the skill dir — confirms committed vs pending for THIS
   skill specifically (the profile repo shows constant noise across the whole `skills/`
   tree; judge against the target dir, not the aggregate).
3. Timestamp/hash the live SKILL.md and any staging bundle vs the last commit — verifies the
   file the user will consume is current, not stale from before the last merge.

**`[NEW]` If it is not a git repo** (Hermes profile catalog — table above says "n/a, no
git"): the 3 git-based checks above have no equivalent — do not skip resume verification
just because git isn't available.
1. Check `.audit_manifest.json` mtime + content against the last handoff's claimed state —
   a manifest newer than the handoff means work happened the handoff doesn't know about.
2. Hash (sha256) the live survivor SKILL.md(s) named in the handoff; compare against any
   hash recorded in a prior snapshot/checkpoint (G3's snapshot step, if a promotion already
   ran) or against `/tmp/<survivor>-premerge.md` backups still on disk.
3. If neither manifest mtime nor a snapshot hash gives a clear signal, treat the handoff as
   UNVERIFIED and re-run Phase 0 pre-flight counts fresh rather than trusting the narrative.

Then map the handoff's open items to facts (DONE vs mid-flight) and present the user only
the genuinely-unfinished threads with a clear decision frame. Never re-do completed gates.

## External Review Delivery — bundle + manual paste over GUI-driving

For an out-of-harness expert review (e.g. Claude Desktop, or a research notebook like
NotebookLM — both validated as delivery channels, the latter as of 2026-08-10):
- BUILD a self-contained bundle file (`<name>-review-bundle.txt`) containing: the review
  brief, the FULL current SKILL.md text, and the numbered review questions — so the whole
  review can be handed off in one paste with zero external context.
- CONFIRM the bundle's on-disk state is current (hash-diff against the committed SKILL.md)
  BEFORE offering it — a stale bundle silently reviews an old draft.
- Offer the USER a short framing line (role: expert critic; verdict SHIP / SHIP-WITH-FIXES /
  DON'T-SHIP; single strongest improvement) to paste first, then the bundle contents. Many
  users prefer running the manual paste themselves over the agent driving the desktop GUI
  (Win32) — present both and let them choose. When they pick manual, hand them the file path
  + exact framing line and stop; do not drive the GUI unprompted. If a notebook/agent
  connector can query the review target directly (as here), that's a third valid path —
  still apply the same staleness check before trusting its answer.

## Cross-Harness Consolidation & Operational Details

Deep operational detail (junction-back consolidation across harness stores, Windows/git-bash
execution notes, verification discipline) moved to `references/operational-details.md` for
progressive disclosure. Core rules: junction-aware moves, `cmd /c rmdir` for links, unset
PYTHONHOME, native C:/ paths, python-heredoc move scripts.

## Verification Discipline

Every claim backed by literal command + literal output: head -5 + byte deltas per merge,
diff excerpt for appends, full move-script output, all post-flight counts. If you cannot
produce a literal output for a claim, do not state the claim as fact. **`[NEW]`** This
applies to this skill's OWN content too: any `[NEW]`/`[PROPOSED]` item above stays tagged
as such — carrying no literal-output history yet — until it has been run for real at least
once with output captured. Do not silently drop the tag to make a section read as more
settled than it is.

## Package Contents

A complete install must include this file plus `scripts/`, `schemas/`, and every file listed
below. `check-package` is the authoritative completeness check. The current draft is not
promoted while any listed reference is absent.

## References

All supporting evidence and historical analysis documents are stored in the `references/` directory:

- `references/agent-self-audit-catalog-2026-08.md` — Querying consuming coding agents for active skill usage.
- `references/agent-skills-clone-cleanup-2026-08.md` — External-consumer clone catalog cleanup details.
- `references/coder-ceo-cleanup-2026-08.md` — Concrete executor run details.
- `references/context-cost-of-skill-catalog-2026-08.md` — Cost analysis of large skills catalog in active context.
- `references/council-merge-loss-check-2026-08.md` — Full walkthrough of council-merge loss-checks.
- `references/delegated-full-read-comparison-2026-08.md` — Full-read subagent comparison pattern and verdicts.
- `references/embedded-council-procedure.md` — 5-advisor → peer-review → chairman council (inline fallback procedure).
- `references/external-benchmark-gates-2026-08.md` — Hardening gates (G0-G3) external benchmarking analysis.
- `references/g2-judge-rubric.md` — G2 judge scoring criteria + correlated-model honesty note (MANDATORY in every benchmark artifact).
- `references/hardening-gates.md` — Full G0-G4 gate bodies + process (consulted at every promotion).
- `references/hardening-toolkit.md` — Phase 1 authoritative execution contracts (preflight/plan/apply/loss-check/approval).
- `references/4-phase-workflow.md` — Legacy manifest-driven archive-only workflow.
- `references/methodology-wrapper-assessment-2026-08.md` — Evaluation of methodology-wrapper skills (keep-all verdicts).
- `references/operational-details.md` — Cross-harness consolidation and Windows/git-bash execution notes.
- `references/phantom-skill-resolution-2026-08.md` — Resolving missing config skill references.
- `references/pitfalls.md` — Real incident catalog of production failures.
- `references/promotion-gate-merge-to-live-2026-08.md` — Phase 6 promotion gates (Gate A/B specifications).
- `references/reliability-reproducibility.md` — Determinism, hash discipline, evidence-vs-narrative rules.
- `references/restore-vs-rewrite-followup-2026-08.md` — Rationale for restoring vs rewriting deleted core skills.
- `references/rogue-post-final-subagent-2026-08.md` — Forensic log analysis of rogue subagent writes.
- `references/skill-consolidation-junctions-2026-08.md` — Cross-harness consolidation via Windows junctions.
- `references/skill-dedup-manifest-2026-08.md` — Planning sheet for duplicate-family merges.
- `references/skill-evaluation-orphan-detection-2026-08.md` — Multi-layered scan for true orphan skills.
- `references/skill-merge-manifest-omp-2026-08.md` — Execution manifest for the merge phase.

**v3.0 pilot evidence (docs/):**
- `docs/PROJECT.md` — Project spine: decisions D1-D6, milestones M1-M7, status.
- `docs/defect-report-m1-20260810.md` — M1 discovery defects D1-D6 (closed/reclassified).
- `docs/spec-m2-grouping-20260810.md` — M2 grouping method spec (paper-verified).
- `docs/council-brief-commit-family-20260810.md` — M3 framed question + full sources.
- `docs/council-verdict-commit-family-20260810.md` — M3 council transcript (5 advisors, 5 reviews, chairman).
- `docs/golden-output-experiment-brief-20260810.md` / `-results.md` — M3.5 gate (6/6 match).
- `docs/m4-build-brief-20260810.md` — M4 staged-draft brief.
- `docs/benchmark-m5-20260810.md` + `docs/benchmark.json` + `docs/benchmark-g2-d1..d3.json` — M5 G2 evidence (36/36 cells).
- `docs/g2-confirmation-brief-20260810.md` — M5b confirmation-run brief.
- `skills-merge-drafts/` — staged drafts (never promoted until gates clear).

**`[NEW]`** No dedicated reference doc exists yet for G1b, G3.5, G4, or the Timeout &
Escalation Discipline — argued inline above from the NotebookLM review + this gap analysis,
not from a captured production incident. The hardening-gates body itself moved to
`references/hardening-gates.md` while its `[NEW]` items are still PROPOSED; write a
dedicated run-doc once each has a real run to document.
