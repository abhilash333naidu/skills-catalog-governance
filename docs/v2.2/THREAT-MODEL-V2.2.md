# Threat Model: Skills Catalog Governance V2.2

**Status:** Council-informed draft (2026-08-25). Sources: council transcript
(`council-transcript-v2p2p4-plan-review.md`), `tasks/plan.md`.
**Scope:** V2.2 changes only — decide gate, grade-skill, golden fixtures, doc relabeling.
**Standing invariants:** stdlib only; skill content never executed; fail closed;
SHA-256-bound artifacts; human approval for activation.

## Assets & trust boundaries

| Asset | Boundary crossed |
|---|---|
| Skill bytes (untrusted input) | author → catalog → agent runtime |
| Evaluation/scan records | tool output → decision state |
| Decision records (APPROVE) | maintainer judgment → activated skills |

## Threats

### T1 — Maintainer as attack vector
**Threat:** A compromised or careless maintainer approves a malicious skill; or a
maintainer's local environment silently alters bytes between review and approval.
**Likelihood:** Medium. **Impact:** Critical (activated malicious skill).
**Mitigations:** Hash-bound records make every approval point to exact bytes;
append-only-style decision logging (adopted future Task F); human queue discipline
documented per council flag. The decide re-evaluation gate (REQ-A2) removes the
"edit after scan" shortcut even for an inside job that isn't fully colluding.
**Residual risk:** A fully colluding maintainer can still approve anything — the
system raises cost and leaves evidence; it cannot stop authorized humans. Stated
honestly.

### T2 — Fixture gaming by authors
**Threat:** Skill authors craft SKILL.md content to pass byte-match fixtures without
being good skills ("teaching to the test"). Prompts are non-deterministic, so
byte-matching is theater against adaptive authors (First Principles advisor).
**Mitigations:** Grader is explicitly scoped to structural checks with loud labeling
(REQ-B5): "structural grading only; behavioral claims advisory". Explicit FAIL
reasons surface gaming patterns rather than hiding them. GO verdicts never assert
behavioral correctness.
**Residual risk:** Authors can still optimize for fixtures. Accepted by design —
the grader certifies structure, not intent.

### T3 — Regex bypass via obfuscation/encoding
**Threat:** Malicious content evades SEC-001..007 via unicode homoglyphs, base64
blobs, HTML entities, zero-width characters, or split instructions across lines.
**Likelihood:** High for a determined adversary. **Impact:** HIGH findings missed →
skill reaches human review looking clean.
**Mitigations:** All docs and reports label findings **"tripwire, not boundary"**
(REQ-D1). HIGH remains a hard block because false-positive cost is cheap human
review, but absence of findings is never claimed to mean safety. 7 regexes are not
OWASP-aligned; we do not pretend otherwise.
**Residual risk:** Real. The scanner is a tripwire that catches lazy adversaries,
nothing more. Human review remains the actual control.

### T4 — Path traversal / symlink risks
**Threat:** Crafted skill archives or fixture paths escaping the catalog root;
symlinked files inflating or swapping hashed content; Windows case-collision tricks.
Council flagged canonical file-selection (symlinks/.gitignore/case collisions) as
undefined → garbage-in for any tree hash.
**Mitigations:** Windows-safe paths are a binding constraint; hashes bind raw file
bytes individually (no tree-hash ambiguity in V2.2 scope since IR is deferred).
Fixture loading SHOULD resolve paths within the declared root and reject escapes.
**Residual risk:** Until a canonical file-selection rule exists (reserved for
lockfile design), consumers MUST NOT treat multi-file aggregates as hash-covered.

### T5 — TOCTOU between evaluate-proposal and decide
**Threat:** Bytes change between evaluation/scanning and approval — accidentally
(editor autosave) or adversarially — so the approval references evidence that no
longer describes reality. This was a live hole pre-V2.2: editing blocked content
could clear a HIGH block without re-scanning (Contrarian advisor).
**Mitigations:** REQ-A1/A2 close it: `evaluated_skill_sha256` recorded at evaluation;
decide recomputes at decision time; drift fails closed requiring fresh evaluate +
scan; REQ-A3 makes HIGH block unconditional even post-fresh-evaluation.
**Residual risk:** TOCTOU between the fresh re-evaluation and the subsequent decide
window still exists but is now narrow and detectable (drift check repeats each
decide). Fully closing it would require locking, out of scope.

## Risk register summary

| ID | Severity | Status |
|---|---|---|
| T1 | Critical impact / medium likelihood | Partially mitigated, documented |
| T2 | Medium | Mitigated by labeling/scope |
| T3 | High likelihood | Mitigated by honest tripwire framing |
| T4 | Medium | Partially mitigated; rule reserved |
| T5 | High | Designed closed by REQ-A2/A3; pending regression test `test_a2_drift_blocks_approve_requires_reeval` |
