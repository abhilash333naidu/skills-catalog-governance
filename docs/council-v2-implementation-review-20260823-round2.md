# V2.0 Implementation Council Review — Round 2

**Date:** 2026-08-23  
**Artifact reviewed:** V2.0 implementation after the round-one recovery fix  
**Previous review:** `docs/council-v2-implementation-review-20260823-round1.md`  
**Decision requested:** Final release approval.

## Independence Notice

This review follows the repository's five-advisor plus peer-review procedure as five
adversarial lenses applied by one underlying model in this environment. The lenses are
not five independent model providers. Findings are structured review signals, not
statistically independent consensus.

## Round-One Fixes Verified

- Activation tracks the published target and exact published hash.
- A post-publication failure removes the target only when its content still matches the
  hash published by the current invocation.
- A changed external target is left untouched and reported as cleanup blocked.
- A newly written active record is removed on failed activation.
- `ACTIVATION_FAILED` is a distinct machine-readable status with exit code 1.
- A failure artifact is written under `run-record/` when possible.
- The proposal remains quarantined; no `ACTIVE` success is emitted on failure.
- Regression test forces archive creation failure after publication and confirms no
  orphaned active skill or active record remains.

## Verification Evidence

Fresh repository gates after the fix:

- `python3 -m pytest tests/ --cov=scripts --cov-report=term --cov-fail-under=20`
  -> 172 passed, coverage 20.23%, exit code 0.
- `ruff check scripts/ tests/` -> All checks passed, exit code 0.
- `python3 scripts/catalog_governance.py check-package --root .`
  -> `status: PASS`, exit code 0.

## Framed Question

After the post-publication recovery fix, does the implemented V2.0 create-only,
one-active-root lifecycle satisfy the approved specification, the five binding council
constraints, and the round-one release correction? Identify any remaining blocker.

## Advisor Responses

### The Contrarian

The critical orphan risk is addressed correctly. The cleanup is ownership-bound to the
published hash, which prevents deleting an externally modified target. The remaining
risks are bounded: snapshot metadata does not copy a nonexistent CREATE target, which is
consistent with the create-only invariant; the failure artifact and journal preserve the
attempt. The implementation still has broad command surface in one large file, but that
is maintainability debt rather than a V2 release blocker. Approve with the documented
limitation that V2.0 does not provide crash-atomic multi-file transactions.

### The First Principles Thinker

The implementation now aligns with the product invariant. Intake is separate from
activation, evidence is hash-bound, policy cannot enable autonomy, and activation failure
returns the system to a quarantined/no-active-target state when cleanup ownership can be
proven. The state journal is not a full transaction log, but the command contract does
not promise crash recovery beyond recorded failure. Approve the vertical slice and keep
future update/replacement work out of this release.

### The Expansionist

This is a sound foundation for future adapters. The failure record and preserved
quarantine make the governance history useful beyond Hermes. The product has enough
operator evidence to support a real pilot. Do not add more scope before observing real
proposal traffic. Approve.

### The Outsider

The implementation is now understandable through the command names and reports. One
minor usability gap remains: users need a quickstart showing the exact V2 command order,
but the absence of that guide does not make the lifecycle unsafe or incorrect. The
reports clearly distinguish `QUARANTINED`, `EVALUATED`, `APPROVED`, `ACTIVE`,
`RESTORED`, and `ACTIVATION_FAILED`. Approve the code; add usage documentation in the
next documentation pass.

### The Executor

The regression test proves the previously broken path: publication occurs, a later
failure is forced, cleanup removes the target, the active record is absent, the failure
record exists, and the command returns nonzero. Full tests, coverage, lint, and package
checks pass. The implementation is ready for the approved V2.0 slice. Do not expand to
update or retirement until this path is used against a real Hermes proposal fixture.

## Anonymous Peer Review

### Review A

**Strongest:** Executor, because it ties the safety claim to a reproducible regression test.  
**Biggest blind spot:** Expansionist does not discuss crash interruption between cleanup
and journal write.  
**All responses missed:** The release notes should state that crash-atomic recovery for
cross-file operations is not claimed.

### Review B

**Strongest:** Contrarian, because it keeps the remaining limitations explicit.  
**Biggest blind spot:** Outsider treats command ergonomics as secondary without checking
whether the current docs expose the new commands.  
**All responses missed:** The implementation plan/task checklist should be updated to
reflect completed tasks and the council gate result.

### Review C

**Strongest:** First Principles, because it evaluates the invariant rather than the size
of the diff.  
**Biggest blind spot:** Executor does not address the broad static scanner limitation.  
**All responses missed:** Capability detection remains heuristic and must stay labeled in
operator output and product documentation.

### Review D

**Strongest:** Executor, due to direct evidence of the fixed failure mode.  
**Biggest blind spot:** Contrarian's crash caveat is not a blocker for the documented
single-process failure path.  
**All responses missed:** The active record should not be interpreted as a cryptographic
signature; it is hash-bound local evidence.

### Review E

**Strongest:** First Principles, because it confirms the scope remains create-only and
prevents approval from drifting into a broader claim.  
**Biggest blind spot:** Outsider underestimates the importance of testing on real Windows
junctions.  
**All responses missed:** A real Hermes adapter fixture remains necessary before claiming
Hermes production integration, even though the proposal contract itself is ready.

## Chairman Synthesis

### Where the Council Agrees

1. The round-one release blocker is fixed and regression-tested.
2. The current V2.0 implementation satisfies the approved create-only, one-active-root
   lifecycle and its five binding constraints.
3. Activation failure now fails closed with ownership-bound cleanup and machine-readable
   evidence.
4. The implementation should not expand scope into update, replacement, retirement,
   autonomous activation, or native Hermes hooks in this release.
5. The remaining limitations are documentation, real-Hermes fixture validation,
   platform-specific coverage, heuristic scanning limits, and crash-atomicity scope;
   none invalidate the approved vertical slice when stated explicitly.

### Where the Council Clashes

- The Contrarian emphasizes crash interruption between filesystem cleanup and journal
  persistence; the Executor treats it as outside the current single-process failure
  contract. Resolution: record it as a documented limitation and future hardening item,
  not a release blocker.
- The Outsider wants a V2 quickstart before release; the other lenses classify it as
  documentation debt. Resolution: approve code now, add the quickstart before public
  product announcement or Hermes integration claim.

### Blind Spots the Council Caught

- V2.0 must not claim crash-atomic recovery across all filesystem operations.
- The implementation is a proposal-contract pilot, not proof of a native Hermes hook.
- Heuristic capability scans and active records are evidence, not complete security or
  cryptographic guarantees.
- Real Windows junction and real Hermes adapter fixtures remain required follow-on proof.
- The task checklist must be updated to accurately reflect the completed gates.

### Recommendation

**APPROVE V2.0 IMPLEMENTATION FOR THE DEFINED VERTICAL SLICE.**

The implementation meets the approved release scope after the post-publication cleanup
fix. Before making a broader public integration claim, add a concise V2 quickstart,
validate a real Hermes-side adapter fixture, and run Windows junction-specific tests.
Those are follow-on evidence tasks, not reasons to block this local CLI slice.

### The One Thing to Do First

Update the implementation checklist and release notes to state exactly what V2.0 proves
and what it does not claim, especially native Hermes interception and crash-atomicity.

## Round-Two Verdict

**GO — V2.0 IMPLEMENTATION APPROVED FOR THE DEFINED CREATE-ONLY VERTICAL SLICE.**
