# Lifecycle Pipeline (M1–M6)

The governance pipeline is divided into six numbered phases, each producing a deterministic artifact. Phases must run in order — each phase gates the next.

```
 M1     →   M2    →   M3    →  M3.5*  →   M4    →   M5    →   M6
Discovery → Grouping → Council → Golden  → Master → Benchmark → Promotion
                                  Gate*    Build
                                  
* M3.5 is required only for generated-output skills (formatters, generators).
```

## M1 — Discovery

**Command:** `detect-skills`

Scans configured skill stores and produces a tagged inventory with:

- Store label (hermes, claude, opencode, codex, external, etc.)
- Absolute path (canonical — deduplicated across symlinks/junctions)
- Name from frontmatter (directory-name fallback)
- Description (empty-string fallback)
- SHA-256 of raw SKILL.md bytes
- Usage count (where `.usage.json` is available)

Fail-closed: unreadable/malformed files produce error entries, never guesses.

## M2 — Grouping

**Command:** `detect-groups`

All-pairs similarity over the M1 inventory using two signals:

1. **TF-IDF Cosine** (flat, no ML training) — measures term-frequency overlap
2. **Word Overlap** — |intersection| ÷ min(|A|,|B|)

Candidates are flagged when either signal exceeds threshold. Strong pairs (both signals agree) form connected groups; single-signal pairs are recorded but never bridge groups (prevents the mega-group chaining problem).

Over-flag bias: default thresholds favour false positives (cost: one wasted read) over false negatives (cost: a missed group).

## M3 — Council Review

Human-supervised LLM council: five thinking-lens advisors, five anonymous peer reviews, one chairman synthesis.

**Mandatory:** cannot be skipped. Output is a structured verdict with provenance table.

**Group size cap:** maximum 8 skills per group. Larger groups require split analysis.

## M3.5 — Golden Gate

**Command:** `golden-gate`

For generated-output skills: feed fixed inputs through each source, then through a single parameterized master contract. Verify the master reproduces every source output byte-for-byte (modulo whitespace).

**N/N match = absorption authorized.**

Runner execution is **disabled by default** — manifest must explicitly opt in with `"allow_runners": true`. Runners are argv lists only (no shell, no `-c`/`-e`), with timeout protection.

## M4 — Master Build

**Command:** `check-master` (G0 + G1 + G3 gates)

Stages the merged draft outside the live root. Deterministic gates run before promotion is allowed:

- **G0** — name matches directory, ≤64 chars, description ≤1024 chars, no XML angle brackets, <500 lines, refs one level deep
- **G1** — static security scan blocks credential-exfil patterns, flags exec patterns and unpinned deps
- **G3** — version is a quoted semver string, `merged-from:` provenance list required

## M5 — Benchmark

**Command:** `benchmark` (G2 gate)

Head-to-head comparison: master vs each source, plus a no-skill baseline. ≥3 runs per cell. Master must win or tie every cell AND beat the best source overall.

**Verdict:** GO (promotion authorized) or NO-GO (promotion blocked).

## M6 — Promotion

Snapshot → promote to live → archive sources → commit (if git repo). Post-promotion audit re-verifies:

1. Live file hash matches the draft
2. Frontmatter parses correctly
3. `detect-skills` still passes over the entire catalog

External/vendored sources are NEVER edited — content is absorbed into the master, the parent tree is left intact.