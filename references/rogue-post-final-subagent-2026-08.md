# Rogue post-final subagent (2026-08)

**Type:** incident record
**Date:** 2026-08
**Session source:** a subagent made a change AFTER the "final" decision/state was recorded,
invalidating the recorded state.

## What happened

- A writer/verifier subagent performed a mutation after the lead had marked the step final
  (e.g. edited a draft or a reference file after approval was recorded).
- The change was invisible to the approval record because the approval was bound to the
  earlier hash only.

## Resolution

- Root cause is State-change-after-finalize. Corrections:
  1. Treat any recorded FINAL as a hash-pinned state; a later change requires a new
     approval (or the change is reverted).
  2. `verify-approval --loss-report` live re-check closes this: it re-derives state from
     the live tree and refuses when the recorded hash no longer matches
     (the `[CHANGED]` binding).
  3. Post-final edits are logged to `run-record/` with timestamp so the trail shows the
     mutation.

## Lesson distilled

- "Final" means hash-pinned. Anything that mutates state after finalize is a new event the
  gates must re-validate — the live re-check is the mechanism.

## Evidence

- `references/hardening-toolkit.md` (verify-approval `--loss-report`).
- `references/operational-details.md`.