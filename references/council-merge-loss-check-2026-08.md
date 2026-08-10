# Council merge + loss-check walkthrough (2026-08)

**Type:** procedural evidence
**Date:** 2026-08
**Session source:** first full Council Per-Group merge executed end-to-end with
`catalog_governance.py loss-check` as the mechanical gate.

## The run

1. Council convened per `references/embedded-council-procedure.md`; verdict artifact saved
   to `skills-merge-drafts/<group>-council-verdict.md`.
2. Writer produced `<survivor>.SKILL.md` from six input sources under the verdict's
   "one thing to do first."
3. `python3 scripts/catalog_governance.py loss-check --draft ... --source ... --source ...
   --output run-record/loss-check.json` — six sources, five expected loss areas
   ("6-of-5"). Result `PASS`, with `manual_review_required: true` still set.
4. Lead performed the authoritative full manual comparison; recorded hashes.
5. Approval written `run-record/approval.json` (`APPROVE`, named reviewer, non-empty text
   echoing the loss-check result).
6. `verify-approval` bound the draft hash to the approval (two-hash binding); later
   upgraded to the `--loss-report` live re-check binding (see `[CHANGED]` in
   `SKILL.md`).
7. Promotion + archive per manifests; G2 post-move revalidation and G3 dangling-reference
   scrub at promotion.

## What it caught

- Mechanical loss-check flagged a merged skill missing a fenced command that the manual
  read had missed — the two signals disagreeing is exactly the point (G1).
- Approval text initially summarized rather than echoed the loss-check; fixed to echo the
  result field verbatim.

## Lesson distilled

- Loss-check `PASS` is necessary, never sufficient: manual review stays mandatory
  (`manual_review_required: true`).
- Where post-merge verified commands were absent, the working copy requirement (G1b) was
  the correction.

## Evidence

- `schemas/loss-check.schema.json`, `schemas/approval.schema.json`.
- `scripts/catalog_governance.py` subcommands `loss-check` / `verify-approval`.
- Gate detail: `references/hardening-gates.md` (G1, G1b).