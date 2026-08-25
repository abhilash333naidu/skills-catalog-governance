# Validation Report: docs/v2.2 — Skills Catalog Governance V2.2

**Validator:** validation agent (adversarial pass)
**Date:** 2026-08-25
**Inputs:** SPEC-V2.2.md, PRD-V2.2.md, THREAT-MODEL-V2.2.md, TEST-PLAN-V2.2.md
**Ground truth:** `scripts/catalog_governance.py` (HEAD), `tasks/plan.md`, `schemas/`

## Verdict: CHANGES REQUIRED

Counts: **1 blocker · 2 majors · 3 minors**

---

## Findings

| # | Doc | Severity | Location | Finding |
|---|---|---|---|---|
| 1 | SPEC + TEST-PLAN | **Blocker** | SPEC §A REQ-A4; TEST-PLAN §A row REQ-A4 | `decide` has no `--reject` or `--quarantine` flag. Code reality: `decide` takes a single required `--decision {APPROVE,REJECT,BLOCK,REQUIRES_REVIEW}` (catalog_governance.py ~L2483, L2986-2992). QUARANTINED is an *intake* status (`skills-catalog-intake-1`), not a decide outcome. REQ-A4 and its test as written are unimplementable against the real CLI. Corrected text below. |
| 2 | SPEC | Major | REQ-D2 | Acceptance criterion "README sections present; reviewed in docs check" is a vague MUST with no concrete verification path (unlike REQ-D1's grep-based test). Specify the exact phrases and make it an automated assertion like D1. |
| 3 | SPEC | Major | REQ-C1 | "fixture committed prior to refactor commit (verifiable in git history order)" is not machine-verifiable by pytest and mixes process with acceptance. Keep the byte-equality assertion as the testable criterion; move git-ordering to a process note, or define a concrete check (e.g., fixture file mtime/commit precedes refactor commit verified manually and recorded). |
| 4 | SPEC | Minor | Header "Scope" | "Supersedes no shipped behavior" contradicts Task A itself: the re-evaluation gate changes `decide`'s shipped behavior (currently `cmd_decide` performs no drift/HIGH checks at all). Reword to "V2.0 lifecycle and V2.1 scanner commands remain unchanged except where Tasks A–E specify." |
| 5 | SPEC | Minor | REQ-B5 report shape | Report uses `"schema_version": 1` while every existing report in the codebase uses `"schema": "<named-schema-id>"` convention (e.g. `skills-catalog-security-audit-1`). Recommend `"schema": "skills-catalog-grade-1"` for ecosystem consistency. |
| 6 | THREAT-MODEL | Minor | T5 / Risk register | Risk register marks T5 "Closed … regression-tested" before any code exists; pre-implementation this should read "Designed closed, pending test_a2_*" to avoid claiming evidence that doesn't yet exist. |

### Blocker #1 corrected text

SPEC REQ-A4, replace:

> `decide --reject` and `--quarantine` SHOULD succeed on drifted hashes …

with:

> ### REQ-A4 — non-approve decisions
> `decide --decision REJECT` and `decide --decision BLOCK` (and MAY `--decision REQUIRES_REVIEW`) SHOULD succeed on drifted hashes (drift is not itself disqualifying for rejection), but MUST log both `evaluated_skill_sha256` and the recomputed current hash in the decision record. Quarantine remains an intake-stage status (`skills-catalog-intake-1`), not a decide decision, and is out of scope for this requirement.

TEST-PLAN REQ-A4 row, replace test/assertion with:

> `test_a4_reject_block_allowed_on_drift` — `decide --decision REJECT` and `--decision BLOCK` on drifted bytes exit 0/succeed; written decision record contains both old and new hashes.

---

## Verified-consistent items (spot-check results)

- Council amendments all faithfully reflected: decide re-evaluation on hash drift (REQ-A1/A2); HIGH unconditional block (REQ-A3); SKILL.md-only ingestion + exporter deferral (PRD non-goals, REQ-D2); normalization rule matches amendment **exactly** (trailing-whitespace-per-line strip, CRLF→LF, exact otherwise — REQ-B2); fenced grammar matches exactly (``` /~~~ only, info string contains `output`, first match wins, unclosed/nested = FAIL — REQ-B3); tripwire labeling (REQ-D1); golden detect-skills fixture captured pre-refactor (REQ-C1).
- Real-code claims checked: SEC-001..SEC-007 exist with severities high×3 / medium×3 / low×1 (PRD's "7 regexes" is accurate); `skills-catalog-security-audit-1` schema string correct; `evaluate-proposal`, `scan-security --path --fail-on`, `detect-skills`, `check-package --root` all exist as documented; verification commands are runnable; PRD's V2.0/V2.1 ship claims match code (intake, decide+activation+rollback, scanner).
- Requirement IDs unique across A/B/C/D namespaces; TEST-PLAN covers every REQ id (A1–A4, B1–B6, C1–C2, D1–D2).
- No fabricated statistics or citations found; council transcript references resolve to existing files.
- Non-goals explicit and not contradicted by any promise elsewhere (grader labeling consistent across SPEC-B5/PRD/THREAT-MODEL).

## Final checklist

- [x] All four documents present (poll completed; writer finished during wait)
- [x] Cross-checked against scripts/catalog_governance.py — 1 blocker found
- [x] Consistent with tasks/plan.md council amendments — yes
- [x] Internal consistency of each doc — issues #4, #6
- [x] Unique REQ ids + testable acceptance criteria — issues #2, #3
- [x] TEST-PLAN covers every REQ id — yes (after #1 fix)
- [x] No fabricated stats/citations — confirmed
- [x] Re-validation after blocker fix — applied 2026-08-25: all 6 findings (1 blocker, 2 majors, 3 minors) fixed in-place by orchestrator; corrected text adopted verbatim from this report where provided.
