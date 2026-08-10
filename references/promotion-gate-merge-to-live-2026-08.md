# Promotion gate: merge to live (2026-08)

**Type:** policy / gate evidence
**Date:** 2026-08
**Session source:** the promotion gate definition for moving merged skills into the live
catalog.

## The promotion checklist

Before a merged skill goes live, ALL of the following must hold:

1. **Council verdict** on record (`skills-merge-drafts/<group>-council-verdict.md`).
2. **Loss-check PASS** (`run-record/loss-check.json`) + manual review completed
   (`manual_review_required: true` acknowledged) — G1.
3. **verify-approval** bound: approval `APPROVE` with reviewer, non-empty text, matching
   draft hash, and (with `--loss-report`) the live re-check reproducing the recorded
   condition set — the `[CHANGED]` closure rule.
4. **Post-merge parity (G1b)** for every command from every source, fresh session, working
   copy in drafts on first improvement.
5. **Post-move revalidation (G2):** `check-package` on the FULL target package,
   `validate-manifest` on the updated manifest, catalog re-check at destination, tree hash
   recorded, event logged.
6. **Dangling-reference scrub (G3) + distribution-evidence parity (G3.5):** required files
   exist; References section matches on-disk files.
7. **Traceability audit (G4):** every verifiable claim cites an existing artifact.

## Refusal

Any gate FAIL refuses the promotion. Fix + re-verify; the final audit is a fresh-context,
full-artifact-scan pass (bias to the artifact, not the memory).

## Evidence

- `references/hardening-gates.md` (all gate detail).
- `references/council-merge-loss-check-2026-08.md`.