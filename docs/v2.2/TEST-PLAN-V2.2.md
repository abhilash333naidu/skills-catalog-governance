# Test Plan: Skills Catalog Governance V2.2

Maps every REQ id in `SPEC-V2.2.md` to concrete pytest cases. All cases live under
`tests/`, run with `python -m pytest tests/ -q`. Evidence-first: each case asserts
observable CLI/report output, never internal calls.

## A. Decide re-evaluation gate

| REQ | Test | Assertion |
|---|---|---|
| REQ-A1 | `test_a1_evaluated_hash_recorded` | After `evaluate-proposal`, record contains `evaluated_skill_sha256` == sha256 of skill bytes |
| REQ-A2 | `test_a2_drift_blocks_approve_requires_reeval` | **Key regression.** Evaluate a blocked proposal, modify skill bytes, run `decide --approve` → non-zero exit, error names both old and new hashes, no APPROVE record written. Fresh `evaluate-proposal` + `scan-security` then permits decide (modulo REQ-A3) |
| REQ-A3 | `test_a3_high_finding_blocks_approve_unconditionally` | HIGH finding on current matching bytes → APPROVE refused even though hashes match and evaluation passed |
| REQ-A4 | `test_a4_reject_block_allowed_on_drift` | `decide --decision REJECT` and `--decision BLOCK` on drifted bytes exit 0/succeed; written decision record contains both old and new hashes |

## B. Grade-skill

Schema:
- `test_b1_schema_minimal_valid_exact_output`
- `test_b1_schema_rejects_both_modes` — expect_exact_output AND expected_tools → FAIL
- `test_b1_schema_rejects_missing_fields` — missing fixture_id / input / comparison mode
- `test_b1_case_sensitive_defaults_true`

Normalization (per REQ-B2):
- `test_b2_crlf_matches_lf` — CRLF fixture vs LF actual passes
- `test_b2_trailing_whitespace_stripped_per_line`
- `test_b2_interior_difference_still_fails` — substantive change FAILs despite normalization
- `test_b2_case_sensitive_false_allows_case_fold` and true forbids it

Fenced-block grammar (per REQ-B3):
- `test_b3_backtick_output_block_extracted`; `test_b3_tilde_output_block_extracted`
- `test_b3_info_string_contains_output_token_wins` (e.g. ```text output)
- `test_b3_first_matching_block_wins` — later output blocks ignored
- `test_b3_unclosed_fence_explicit_fail` — reason `unclosed_fence`
- `test_b3_nested_fence_explicit_fail` — reason `nested_fence`
- `test_b3_no_output_block_fail` — reason `no_output_block`

expected_tools (per REQ-B4):
- `test_b4_zero_declared_tools_fails_explicitly` — reason `no_tools_declared` (**vacuous-pass prevention**)
- `test_b4_empty_intersection_fails`
- `test_b4_superset_passes_only_when_all_expected_present`
- `test_b4_nonempty_intersection_and_full_presence_passes`

Report:
- `test_b5_report_shape_golden` — full GO report JSON matches expected shape incl. `labeling.scope` = structural-only and `behavioral_claims` advisory; NO-GO path asserts failed fixture reasons
- `test_b6_grader_deterministic` — two runs byte-identical (no timestamps/env leakage)

## C. Golden detect-skills fixture

- `test_c1_detect_skills_byte_identical_golden` — live output equals stored golden bytes (captured pre-refactor)
- `test_c2_golden_regeneration_documented` — regeneration command documented and produces the committed fixture

## D. Docs relabeling

- `test_d1_tripwire_label_present` — README and scan-security report template contain "tripwire, not boundary"
- `test_d2_deferred_scope_stated` — README states SKILL.md-only ingestion, exporter deferral, no behavioral grading claims

## Windows-specific cases

- `test_win_crlf_skill_bytes_hash_stable` — SHA-256 computed over raw CRLF bytes unchanged across read modes (binary reads only)
- `test_win_path_traversal_rejected` — fixture paths using `..\\` and drive-absolute forms rejected within root (supports T4)
- `test_win_case_collision_paths_distinct` — `Skill.md` vs `skill.md` treated distinctly where filesystem allows; documented behavior otherwise
- `test_win_long_paths_and_spaces` — grading works under `%LOCALAPPDATA%`-style spaced paths

## Exit criteria

Full suite green; ruff clean; `python scripts/catalog_governance.py check-package --root .` green; grader deterministic; decide hole proven closed by `test_a2_*`.
