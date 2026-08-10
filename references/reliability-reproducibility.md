# Reliability / reproducibility note (package-wide)

**Type:** reference
**Date:** maintained with the package

Cross-cutting note on keeping catalog-governance runs deterministic and verifiable.

## Reproducibility

- All gates are read-only Python (stdlib only) with JSON outputs; the same command on the
  same tree returns the same verdict (no randomness, ordered traversal).
- `check-package` derives its required-file set from `SKILL.md`'s backticked reference
  paths, so the contract and the check are generated from the same source of truth (G3.5).
- `validate-manifest` rejects duplicate/relative/escaping paths deterministically.

## Hash discipline

- Draft hashes, source hashes, and tree hashes are recorded at each loss-check and move;
  `verify-approval --loss-report` re-derives them from the live tree and refuses on
  mismatch (the `[CHANGED]` binding).
- A moved file's post-move tree hash is recorded per move; destination equality is a no-op,
  not an error (G2 idempotency).

## Evidence vs narrative

- Every claim maps to an artifact under `run-record/`, `skills-merge-drafts/`, or
  `references/` (G4). Statements without a file are "unverified", not "true".

## Evidence

- `references/operational-details.md`.
- `references/hardening-toolkit.md`.