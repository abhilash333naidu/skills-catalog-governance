# Phase 1 Hardening Toolkit (authoritative execution contracts)

> Part of the `skills-catalog-governance` package. `SKILL.md` points here for the fail-closed
> execution contracts. This coverage governs package/manifest preflight, fail-closed archive
> plan+apply, mechanical loss-check and approval (including the `[CHANGED]` `--loss-report`
> binding), and the verification record.

The prose in `SKILL.md` defines intent; these standard-library-only commands enforce the
high-risk boundaries. All validation commands are read-only. No catalog move occurs
unless a plan has passed completely and the operator explicitly supplies both
`--apply --yes`.

## Required evidence artifacts

- `schemas/manifest.schema.json` — manifest shape and path-field contract.
- `schemas/loss-check.schema.json` — mechanical comparison output.
- `schemas/approval.schema.json` — written approval bound to the exact draft hash.
- `schemas/provenance.schema.json` — promotion/archive/revert evidence record.
- `scripts/catalog_governance.py` — package, manifest, move, loss-check, and approval checks.

The schemas are package contracts; the CLI enforces the fields needed by each command and
fails closed on malformed or inconsistent values. Full JSON-Schema execution is not a
runtime dependency of this standard-library-only toolkit.

## State and stop conditions

A campaign follows: `PREFLIGHT → COUNCIL/DRAFT → LOSS_CHECK → APPROVAL → PROMOTION →
ARCHIVE → POST_AUDIT`. A failed or stuck state is never treated as complete. A move
preflight failure, destination collision, manifest hash change, source-tree hash change,
symlink/junction source, or post-move hash mismatch is a hard stop. The move command
creates a lock and append-only JSONL journal; a partial run is resumed or investigated
from that journal, never inferred from a truncated console output.

## Package and manifest preflight

```bash
python3 scripts/catalog_governance.py check-package --root . --output run-record/package.json
python3 scripts/catalog_governance.py validate-manifest \
  --root <skills> --manifest <skills>/.audit_manifest.json \
  --output run-record/manifest.json
```

Both commands must report `"status": "PASS"` before a campaign proceeds. The validator
rejects missing required keys, duplicate paths, relative archive PATH VALUES, and paths
that escape the catalog root.

## Fail-closed archive plan and apply

First create and inspect a complete plan. It must report `"status": "PLANNED"` and must
contain zero errors; no destination directory is created during preflight.

```bash
python3 scripts/catalog_governance.py preflight-moves \
  --root <skills> --archive <skills-archive> \
  --manifest <skills>/.audit_manifest.json \
  --plan run-record/move-plan.json

# Only after reviewing the plan and obtaining explicit approval:
python3 scripts/catalog_governance.py apply-moves \
  --plan run-record/move-plan.json \
  --apply --yes --journal run-record/moves.jsonl
```

`apply-moves` rechecks the manifest hash, every source tree hash, every destination,
and the lock before each mutation. It refuses collisions, symlinks/junctions, missing
`SKILL.md` files, and unexpected state changes. It records source, destination, and
post-move tree hash for every successful move. It never deletes or overwrites.

## Mechanical loss-check and approval

The lead still performs the authoritative full manual comparison. The mechanical check
is a second, different signal and never replaces that review:

```bash
python3 scripts/catalog_governance.py loss-check \
  --draft skills-merge-drafts/<survivor>.SKILL.md \
  --source <source-a>/SKILL.md --source <source-b>/SKILL.md \
  --output run-record/loss-check.json

python3 scripts/catalog_governance.py verify-approval \
  --draft skills-merge-drafts/<survivor>.SKILL.md \
  --approval run-record/approval.json \
  --loss-report run-record/loss-check.json
```

The loss-check records source/draft hashes, word overlap, missing headings, and missing fenced
commands. `PASS` means the mechanical checks cleared; `REVIEW` means the lead
must investigate and document the discrepancy. Every result still has
`manual_review_required: true`. Approval must say `APPROVE`, identify the reviewer, carry
non-empty written approval text, and contain the exact current draft SHA-256.

**`[CHANGED]` Approval is bound to mechanical state, not prose (closes the 6-of-5 handoff leak and
the 71-vs-72 drift class):** `verify-approval` accepts `--loss-report <run-record/loss-check.json>`.
When given, the validator RE-RUNS the loss-check LIVE against the draft and every source on disk and
refuses (`FAIL`) unless: the loss report's overall status is `PASS`, every recorded check is `PASS`,
every recorded `draft_sha256` equals the bound approval hash, no source changed since loss-check
(`source_sha256` mismatch), and the live re-check exactly reproduces the recorded missing-heading/
missing-command sets. A dropped defect class can no longer be hidden by a stale or edited brief — the
gate re-derives the condition set from the live tree. This is the mechanical closure rule; use it on
every approval. (Existing two-hash binding — draft hash + approval text — remains, now plus the live
re-check.)

## Verification record

Store command lines, stdout, stderr, exit codes, timestamps, manifest/draft hashes, and
all JSON reports under `run-record/`. A prose claim without its corresponding evidence
artifact is not a verified claim. This toolkit intentionally does not perform catalog
moves in tests or audits unless the operator explicitly invokes `apply-moves --apply --yes`.