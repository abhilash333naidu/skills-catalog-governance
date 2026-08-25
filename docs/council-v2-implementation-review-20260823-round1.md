# V2.0 Implementation Council Review — Round 1

**Date:** 2026-08-23  
**Artifact reviewed:** V2.0 implementation in `scripts/catalog_governance.py`, schemas, tests, and implementation plan  
**Specification approval:** `docs/council-v2-spec-review-20260823-round2.md`  
**Decision requested:** Approve the implemented create-only lifecycle slice for release, or identify required fixes.

## Independence Notice

This review follows the repository's five-advisor plus peer-review procedure as five
adversarial lenses applied by one underlying model in this environment. The lenses are
not five independent model providers. Findings are structured review signals, not
statistically independent consensus.

## Evidence Reviewed

- 171 repository tests passed before this review.
- Coverage gate passed at 20.55% against a 20% minimum.
- Ruff passed.
- `check-package --root .` passed.
- V2-focused tests covered intake, evaluation, impact reporting, decisions, activation,
  verification, rollback, drift refusal, root safety, stable exit codes, and journal order.
- The implementation remains stdlib-only and does not invoke an LLM or execute skill
  content.

## Framed Question

Does the implemented V2.0 create-only, one-active-root lifecycle satisfy the approved
specification and its five binding constraints, especially quarantine durability,
hash-bound human approval, explicit snapshot scope, payload handling, impact limits,
stable status/exit behavior, and rollback safety?

## Advisor Responses

### The Contrarian

Most of the happy path is sound, but the mutation failure path is not release-safe. The
activation command stages and publishes the target, then writes the active record and
archive. If either post-publication write fails, the broad exception handler emits FAIL
without removing the published target or restoring the previous state. That violates the
approved requirement that failed activation restore before reporting failure. A second
concern is that the snapshot is metadata-only for CREATE, which is acceptable only because
the target is required to be absent; the record should make that invariant explicit. Fix
post-publication cleanup and add a simulated archive/record failure test before approval.

### The First Principles Thinker

The implementation has the correct core invariant: proposal bytes are quarantined,
evaluation is read-only, approval is a separate hash-bound artifact, and activation is
one-root/create-only. The main conceptual issue is lifecycle semantics: evaluation appends
`QUARANTINED -> EVALUATING` but decision appends from `EVALUATING` regardless of whether
the proposal was actually evaluated or whether impact evidence is current. The evidence
hash prevents stale files but not an explicit state transition audit. This is a moderate
hardening issue, not a reason to reject the vertical slice if the final activation checks
remain fail-closed.

### The Expansionist

This is a credible foundation. The schemas and records make future adapter integrations
possible without trusting Hermes internals. The strongest product value is the readable
operator evidence: users can see quarantine, risk signals, impact roots, and active hashes.
Do not expand scope now. Add a failure-recovery record and preserve the current simple
contract. A well-proven create path is more valuable than adding update or retirement.

### The Outsider

The commands are understandable, but the implementation does not yet expose a single
end-to-end documented example with the exact command order and expected status values.
That is documentation debt, not a core safety defect. More importantly, the user-facing
promise says rollback restores the prior state, while for CREATE rollback removes the new
skill and archives a copy; the output should explain that this is the expected CREATE
rollback semantics. Approve after the failure-path fix and a concise usage example.

### The Executor

The implementation is close to shippable. The concrete blocker is easy to reproduce:
pre-create `governance/archive/<proposal-id>` so activation publishes the skill, then
archive creation fails. The command returns FAIL, but the active skill remains. Add a
single cleanup helper that removes the newly published target when no prior target
existed, records `ACTIVATION_FAILED`, and leaves the proposal quarantined. Add a test for
this exact scenario. Then rerun the full gates.

## Anonymous Peer Review

### Review A

**Strongest:** Contrarian, because it identifies a real mutation leak after the happy path.  
**Biggest blind spot:** First Principles underweights operator-visible recovery evidence.  
**All responses missed:** The failure record should include the published target hash when
cleanup succeeds or fails.

### Review B

**Strongest:** Executor, because it provides a deterministic fixture to prove the failure.  
**Biggest blind spot:** Outsider treats documentation as nearly equivalent to safety.  
**All responses missed:** Rollback and activation should reject an active-record status that
is already `RESTORED` or an activation already completed.

### Review C

**Strongest:** First Principles, because it checks the state machine rather than only files.  
**Biggest blind spot:** Expansionist does not identify the post-publication mutation window.  
**All responses missed:** Failure cleanup must not delete a target that appeared externally;
cleanup must be bound to the published proposal hash and target ownership.

### Review D

**Strongest:** Executor, due to the smallest practical fix and test.  
**Biggest blind spot:** Contrarian does not distinguish CREATE rollback from replacement rollback.  
**All responses missed:** The active record should record whether rollback is destructive to
an active target; for V2 CREATE it removes only the just-published target after drift check.

### Review E

**Strongest:** Contrarian, because the implementation can currently report failure while
leaving the system active and unrecorded.  
**Biggest blind spot:** Outsider's documentation concern is not release-blocking.  
**All responses missed:** The failure path needs a machine-readable status and exit code,
not merely a console message.

## Chairman Synthesis

### Where the Council Agrees

1. The implementation satisfies the broad V2.0 direction and most approved constraints.
2. The happy path is adequately covered by tests and repository gates.
3. The post-publication activation failure path is a release blocker.
4. CREATE rollback semantics should remove the newly published target after verifying no
   drift, while preserving an archive copy and governance evidence.
5. No scope expansion is needed; fix failure recovery, then rerun tests and council.

### Where the Council Clashes

- The First Principles lens considers the evaluation-to-decision state audit moderate,
  while the Contrarian sees the mutation leak as critical. The mutation leak wins because
  it can leave a skill active without an active record.
- The Outsider requests command documentation before approval; the other lenses treat it
  as non-blocking. Add a short usage section, but do not delay the safety fix for broad
  documentation.

### Blind Spots the Council Caught

- Activation failure after publication can leave an orphaned active skill.
- Failure cleanup must be ownership/hash-bound and must not remove an externally changed
  target.
- Failure results need a machine-readable `ACTIVATION_FAILED` distinction.
- CREATE rollback semantics should be explicit to operators.
- Repeated activation/rollback states need fail-closed guards.

### Recommendation

**NO-GO FOR RELEASE; IMPLEMENT ONE SAFETY FIX FIRST.**

Add an activation transaction-recovery helper:

1. Track whether this invocation published the target and its exact hash.
2. If any later activation step fails, remove the target only if it still exists as the
   exact published proposal hash; otherwise leave it untouched and report cleanup blocked.
3. Record `ACTIVATION_FAILED` plus cleanup outcome and target hash in a machine-readable
   artifact/journal event.
4. Leave the proposal quarantined and never emit `ACTIVE`.
5. Add a regression test that forces archive/active-record failure after publication.
6. Add a guard against activating an already `ACTIVE` or `RESTORED` record.

After implementing this fix, rerun the repository gates and conduct another council review.

### The One Thing to Do First

Make post-publication activation failure recoverable and hash-bound, then prove it with a
regression test.

## Round-One Verdict

**NO-GO FOR RELEASE — POST-PUBLICATION ACTIVATION RECOVERY REQUIRED.**
