# Pitfalls

**Type:** reference / operating knowledge
**Date:** maintained with the package

The recurring failure classes this package exists to catch. If a run smells like one of
these, stop and apply the corresponding gate.

## 1. "Merged but subtly lost it" — the dominant class

A merge passes the visual read yet drops a fenced command or a heading. Counter: mechanical
loss-check (G1) PLUS post-merge parity (G1b): zero mechanical losses, fresh-session
verification of EVERY command from EVERY source, working copy in drafts.

## 2. Stale approval / edited brief (the 6-of-5 handoff leak)

The approval text no longer matches the draft, or the brief was edited after approval so a
dropped defect class is hidden. Counter: `verify-approval --loss-report` RE-RUNS the
loss-check live and refuses unless recorded hashes match the live tree (the `[CHANGED]`
binding in `SKILL.md` / `references/hardening-toolkit.md`).

## 3. One-session curse of knowledge

Verification done in the same session that wrote the draft inherits its blind spots.
Counter: fresh-context readers (G1b, G4, `references/delegated-full-read-comparison-2026-08.md`).

## 4. Unverified vibes claims

"Smaller", "better", "passed its gates" with no artifact. Counter: G4 — every claim maps to
a concrete file (run-record, council verdict, package.json). Evidence, not adjectives.

## 5. Phantom references

A `references/X.md` link with no file, or a file never linked (G3.5's two directions).
Counter: check-package scrub at every promotion (G3).

## 6. Misreading correlation as independence

Council's five advisors are one model, five lenses — correlated, not independent. Counter:
`references/embedded-council-procedure.md` honesty note; external benchmarks only where
genuine independence is claimed (`references/external-benchmark-gates-2026-08.md`).

## 7. Archive idempotency breaks

A re-run that errors because an earlier move already happened. Counter: apply-moves logs to
`moves.jsonl`; an equal destination is a no-op, not an error (G2).

## 8. Treating a failed/stuck state as complete

A campaign in a FAIL or stuck state is never "done." Counter: state machine
`PREFLIGHT → COUNCIL/DRAFT → LOSS_CHECK → APPROVAL → PROMOTION → ARCHIVE → POST_AUDIT`;
a failed state stays failed until resolved (G0–G4 reopen on any step).