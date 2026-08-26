# LLM Council Transcript — V2.1/V2.2 Phases 2-4 Plan Review

**Timestamp:** 2026-08-25 ~16:38 AEST
**Subject:** Council review of tasks/plan.md (Phases 2–4) before build authorization.

## Framed Question

Should skills-catalog-governance proceed with planned Phases 2–4 (ingestion adapters + IR, static fixture grader, ARD exporter) as specified or amended?

## Advisor Responses (full)

### The Contrarian
Weakest decision: hand-rolled YAML subset parser — security liability; anchors/multi-line/quoting/duplicate-key edge cases either reject valid files (fail-broken) or mis-parse hostile ones. Spec grammar in writing, fuzz it, define ambiguity behavior, else cut ASPM.
Phase 3 underspecified: normalization rules undefined (CRLF/LF on Windows, trailing newlines, nested fences); expected_tools subset passing on zero usage is vacuous — need minimum-match semantics. Scanner integration hole: "decide refuses APPROVE while hashes match" means editing content clears a HIGH block without forced re-evaluation — fail-closed must mean re-evaluation required.
7 regexes ≠ OWASP alignment; theater risk; label as tripwire.
IR tree_sha256 needs canonical file-selection rule (symlinks/.gitignore/case collisions) for cross-platform reproducibility; capabilities extraction undefined → garbage-in.
Missing: IR schema versioning/migration; rollback semantics when Phase-3 blocks an already-active skill; lockfile content spec (hashes only? ordering? exporter version?).
Verdict: ship SKILL.md-only Phase 2 + Phase 4 first; block on ASPM and the scanner-in-decide hole.

### The First Principles Thinker
Core risk: malicious/degrading installed skills. Everything else is scaffolding around intake gating + hash-bound human approval + rollback (V2.0 core). Yardstick: every phase must amplify that or get cut.
Phase 2 IR premature — three formats are all markdown+frontmatter; hand-rolled YAML serves no downstream consumer; parse per-format at point of use; add IR when a fourth consumer appears.
Phase 3 byte-matching is theater — prompts non-deterministic; fixture-aware authors game it; honest skills fail spuriously; grade structure statically and say so loudly.
Regex scanning honest if labeled tripwire; keep HIGH hard-block (false positive costs cheap human review).
Phase 4: build nothing until a consumer exists; unread catalog is liability surface.
Phase 3 half-fails yardstick; Phase 4 fails entirely.

### The Expansionist
Pivot to public trust infrastructure ("npm audit / SLSA / Let's Encrypt of agent skills"):
1. Make catalog-lock.json the product: canonical JSON (sorted keys), schema version, top-level content hash, optional externally-signed payload verification; ship standalone verify-catalog script (~200 lines, zero internal imports).
2. Position grader as certifier: deterministic hash-pinned reports, badge tiers, certify-skill CLI entry → CI badges/README shields/PR gates = free distribution.
3. Invert Phase 2: publish catalogs back to skills.sh/clawhub/npx-skills; engage maintainers before finalizing adapters.
Cheapest tweak: hash-linked append-only log on every decision (~50 lines).

### The Outsider
Name sounds like enterprise compliance software; undersells. Value prop almost clear but jargon-buried. For markdown files, byte-match + SHA-256 feels like overkill unless malicious-skill security story leads in plain language. Most useful phase: grader. Least useful: exporter (no known consumer; discovery by whom?). Assume readers don't know OpenClaw/ASPM/Goose. Suggest pain-first framing.

### The Executor
Inspected repo: cmd_detect_skills ~50 lines pure function ending in single emit(); refactor fear overblown; capture byte-identical golden detect-skills fixture BEFORE refactoring.
Fixes:
1. Task 4.1 mis-sized/under-specified (two artifacts + refuse-on-drift = M-to-L); ARD/lock schemas missing; split into 4.1a/4.1b.
2. "Byte-for-byte with normalized whitespace" contradictory — pick precise rule (strip trailing WS per line, normalize CRLF→LF, exact otherwise); state fenced-block extraction grammar (markers, nesting, unclosed, multiple output: blocks).
3. YAML-subset parser negative-test list enumerated NOW: anchors/aliases, block scalars | >, flow {} [], quoted keys, tabs, BOM, duplicate keys, CRLF input — required tests.
4. Ordering gap: confirm scan-security emits per-finding SHA-256 bindings needed by 3.3, else include in estimate.
Checkpoints shippable; approve with four amendments.

## Peer Reviews

(Conducted by fresh-context reviewer agent — see council-report file for verdict.)

## Chairman Verdict

See companion report: council-report-v2p2p4-plan.md
