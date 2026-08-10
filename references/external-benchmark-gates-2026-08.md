# External benchmark gates (2026-08)

**Type:** policy / gate evidence
**Date:** 2026-08
**Session source:** promotion-gate discussion defining when an external benchmark replaces
or supplements the internal council/loss-check gates.

## The rule

- Internal gates (council, loss-check, verify-approval, post-move revalidation) are the
  default promotion path.
- An EXTERNAL benchmark (a genuinely independent model/harness run on a fixed harness —
  not the same model re-prompted) is REQUIRED when: the change alters behavior the internal
  gates cannot observe (e.g. cross-harness portability, model-diversity claims), or a
  promotion makes a claim that demands independence (`references/embedded-council-procedure.md`
  honesty note: the council's 5 advisors are one model, correlated).
- A "benchmark" claim needs a reproducible harness + recorded results artifact; without it,
  the claim is unverified (G4).

## Hard constraints from this session

- Gateway wedge risk on parallel multi-model calls is a hard constraint; do not
  paper over it — the external benchmark is exactly where genuine diversity, if ever
  claimed, must be demonstrated with separate providers/models and recorded output.

## Evidence

- `references/embedded-council-procedure.md` (honesty note on independence).
- `references/promotion-gate-merge-to-live-2026-08.md`.