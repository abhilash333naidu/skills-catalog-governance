# Specification: Skills Catalog Governance V2.2

**Status:** Draft for implementation (council-amended, GO WITH CHANGES, 2026-08-25)
**Scope:** Tasks A–E of `tasks/plan.md`. V2.0 lifecycle and V2.1 scanner commands remain unchanged except where Tasks A–E specify (notably: the REQ-A2 re-evaluation gate changes `decide`'s current behavior).

## Conventions

- MUST / SHOULD / MAY per RFC 2119.
- "Fail closed" means any error, drift, or missing evidence results in refusal of the privileged action.
- All hashes are SHA-256 over raw bytes. Deterministic ordering everywhere. Windows-safe paths required.
- Stdlib only. Skill content is never executed.

---

## A. decide re-evaluation gate (Task A)

### REQ-A1 — evaluated hash recording
`evaluate-proposal` MUST record `evaluated_skill_sha256` in its evaluation record, bound to the exact skill bytes evaluated.

*Acceptance:* after `evaluate-proposal`, the record contains a 64-hex-char `evaluated_skill_sha256` equal to `sha256(skill bytes)`; verified by unit test.

### REQ-A2 — drift forces re-evaluation
`decide --approve` MUST recompute the current skill-bytes SHA-256 at decision time. If it differs from `evaluated_skill_sha256`, `decide` MUST fail closed with an explicit drift error naming both hashes. The ONLY remediation is a fresh `evaluate-proposal` AND fresh `scan-security` run against the current bytes. Hash matching alone MUST never clear an existing HIGH security block.

*Acceptance:* regression test proves that modifying the skill bytes of a blocked proposal cannot yield APPROVE without a fresh evaluation; exit code non-zero and message names old/new hashes.

### REQ-A3 — HIGH blocks APPROVE unconditionally
If `scan-security` reports ≥1 HIGH finding on the current bytes, `decide --approve` MUST refuse regardless of any other state, including a passing fresh evaluation.

*Acceptance:* test with HIGH finding present → APPROVE refused even when hashes match and evaluation passed.

### REQ-A4 — non-approve decisions
`decide --decision REJECT` and `decide --decision BLOCK` (and MAY `--decision REQUIRES_REVIEW`) SHOULD succeed on drifted hashes (drift is not itself disqualifying for rejection), but MUST log both `evaluated_skill_sha256` and the recomputed current hash in the decision record. Quarantine remains an intake-stage status (`skills-catalog-intake-1`), not a decide decision, and is out of scope for this requirement.

*Acceptance:* reject/block on drifted bytes succeeds; record contains both hashes.

---

## B. grade-skill command (Tasks C+D)

### REQ-B1 — fixture schema
Fixtures conform to `schemas/skill-fixture.schema.json` with fields:

| Field | Type | Req | Notes |
|---|---|---|---|
| `fixture_id` | string | MUST | unique within fixture set |
| `input` | object | MUST | prompt + invocation context |
| `expect_exact_output` | string | MUST if `expected_tools` absent | compared per REQ-B3 |
| `expected_tools` | array[string] | MUST if `expect_exact_output` absent | exactly one comparison mode |
| `case_sensitive` | bool | SHOULD default true | applies to exact-output comparison |

Exactly one of `expect_exact_output` / `expected_tools` MUST be present. Schema violations are FAIL, never skip.

*Acceptance:* schema validation tests cover valid minimal fixtures, both-mode rejection, missing-field rejection, case_sensitive default.

### REQ-B2 — normalization rule
Byte comparison MUST apply exactly this normalization before comparing: strip trailing whitespace per line; normalize CRLF→LF; compare exact otherwise. No other transformations (no case folding unless `case_sensitive:false`; no trimming of leading whitespace or blank interior lines).

*Acceptance:* CRLF/LF and trailing-whitespace equivalence cases pass; substantive differences still FAIL.

### REQ-B3 — fenced-block extraction grammar
Output extraction follows this written grammar:
1. Only ``` and ~~~ fence markers are recognized.
2. An output block is a fence whose info string contains the token `output`.
3. First matching block wins; later matches ignored.
4. Unclosed fences are an explicit FAIL (reason: `unclosed_fence`), not a skip.
5. Nested fences are an explicit FAIL (reason: `nested_fence`).
6. No matching output block is an explicit FAIL (reason: `no_output_block`).

*Acceptance:* unclosed/nested/no-match cases each produce the named FAIL reason via pytest.

### REQ-B4 — expected_tools semantics
`expected_tools` requires a NON-EMPTY intersection between expected and declared/observed tools AND every listed tool present. Skills declaring no allowed-tools MUST FAIL tool-based fixtures explicitly (reason: `no_tools_declared`) — vacuous zero-tool passes are impossible.

*Acceptance:* zero-tool skill fails tool fixture; empty-intersection fails; superset passes only when all listed tools present.

### REQ-B5 — GO/NO-GO report shape
`grade-skill` emits a deterministic JSON report:

```
{
  "schema": "skills-catalog-grade-1",
  "skill_sha256": "...",
  "verdict": "GO" | "NO-GO",
  "fixtures": [{"fixture_id": "...", "result": "pass"|"fail", "reason": null|"..."}],
  "summary": {"passed": N, "failed": M},
  "labeling": {
    "scope": "structural grading only",
    "behavioral_claims": "advisory"
  }
}
```

Verdict is GO iff all fixtures pass. Report MUST carry the structural-only labeling on every emission.

*Acceptance:* golden-report test asserts full shape, determinism across two runs, and presence of both label fields.

### REQ-B6 — determinism
Grading MUST be deterministic: same inputs → byte-identical reports. No timestamps, no environment leakage.

*Acceptance:* run twice, assert byte equality.

---

## C. Golden fixture for detect-skills (Task B)

### REQ-C1 — capture-before-refactor
A byte-identical legacy output fixture for `detect-skills` MUST be captured and locked into tests BEFORE any refactor of that code path touches the tree.

*Acceptance:* test compares live `detect-skills` output to the stored golden file byte-for-byte. Process note (not machine-tested): the fixture commit MUST precede any refactor of the detect-skills path; verified by review at PR time and recorded in the PR description.

### REQ-C2 — fixture currency
Golden fixture MUST be regenerated deliberately (documented command) whenever detect-skills output intentionally changes; accidental diffs fail CI.

---

## D. Documentation relabeling (Task E)

### REQ-D1 — tripwire labeling
README and every scan-security report MUST label regex findings as "tripwire, not boundary". No claim that regex scanning constitutes a security boundary.

*Acceptance:* grep-based doc test asserts the phrase exists in README and report template.

### REQ-D2 — deferred-scope honesty
Docs MUST state: SKILL.md-only ingestion; exporter deferred until a named consumer commits; grader makes no behavioral claims about LLM execution.

*Acceptance:* automated grep-based test asserts each of the exact phrases `SKILL.md-only ingestion`, `deferred until a named consumer commits`, and `no behavioral claims` appear in README (or docs/v2.2/PRD-V2.2.md until README is updated in Task E); same verification style as REQ-D1.

---

## Verification Commands

```bash
python -m pytest tests/ -q
ruff check scripts/ tests/
python scripts/catalog_governance.py check-package --root .
```
