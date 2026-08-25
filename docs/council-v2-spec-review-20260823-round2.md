# V2.0 Specification Council Review — Round 2

**Date:** 2026-08-23  
**Artifact reviewed:** `docs/spec-v2.0-20260823.md`  
**Previous review:** `docs/council-v2-spec-review-20260823-round1.md`  
**Decision requested:** Final approval for implementation planning and implementation.

## Independence Notice

This review follows the repository's five-advisor plus peer-review procedure as five
adversarial lenses applied by one underlying model in this environment. The lenses are
not five independent model providers. Findings are structured review signals, not
statistically independent consensus.

## Changes Verified From Round One

- First implementation scope narrowed to `CREATE` for one proposal and one explicit
  active root.
- Native Hermes interception removed from the promise; the filesystem/CLI proposal
  adapter is the supported boundary.
- Update, replacement, retirement mutation, automatic approval, multi-root operation,
  and automatic drift repair explicitly deferred.
- Every V2.0 activation requires an explicit human decision.
- Proposal target identity, active-root binding, actor, decision, policy, proposal, and
  evidence hash requirements added.
- State transition and invalid-transition rules added.
- Capability detection described as heuristic signal detection, not runtime proof.
- Supplied LLM reviews are recorded only; the offline CLI does not invoke models.
- Rollback refuses drift and has no force-recovery mode in V2.0.
- Lifecycle schemas/artifacts and a concrete CLI intake path added.

## Framed Question

After the round-one revisions, is the V2.0 specification coherent, bounded, safe, and
implementable enough to authorize implementation of the create-only, one-active-root
Hermes proposal-adapter lifecycle? Identify any remaining release-blocking defect.

## Advisor Responses

### The Contrarian

The revision is substantially safer, but one serious ambiguity remains: it says the
first vertical slice is create-only while the capability map and CLI still mention
archive, drift, and broad impact analysis. That is acceptable only if the implementation
contract clearly distinguishes read-only reporting from mutation. The activation snapshot
also says "affected path and governance metadata" while rollback says exact prior bytes;
the snapshot schema must define the boundary before code. The policy example still
contains auto-approval fields, which could be misread by implementers unless the schema
rejects or ignores them in V2.0. I would approve the specification for implementation
planning, conditional on making these three details explicit in the plan and tests.

### The First Principles Thinker

The revised spec now has a coherent invariant: one immutable proposal, one active root,
one explicit human decision, one hash-bound activation, and one recoverable rollback.
The adapter is correctly separated from Hermes internals. The remaining question is not
whether the design is valid but whether the implementation should preserve the existing
single-file CLI. The spec does not require that architecture, which is good. Keep the
record schemas stable and permit internal modules. Do not add update semantics until the
create loop proves the state model. Approve.

### The Expansionist

This is now a credible foundation for a broader skill supply chain. The proposal envelope,
policy hash, lifecycle journal, and supplied-review artifact boundary create future
extension points without forcing future autonomy now. The main opportunity is to make
adapter metadata extensible and to preserve unknown fields, which the revision does.
Do not weaken the one-root rule for convenience. Approve implementation, but require the
first release to emit useful operator-facing records so the product feels like a
lifecycle controller rather than a collection of hidden files.

### The Outsider

The happy path is clearer, but a user still needs one explicit setup command or documented
configuration for the active root and governance root. The spec now says `--active-root`
is required, which is good. It should also say that intake alone cannot activate anything,
and that the proposal remains quarantined after intake. The words "policy-controlled"
could still suggest autonomy; the human approval rule should be repeated in the command
flow. With those implementation-level checks, the specification is understandable and
safe enough to approve.

### The Executor

This is implementable if the first plan starts with schemas and a vertical integration
fixture, not broad filesystem scanning. The existing CLI can be extended incrementally,
but the implementation must not claim to support commands before they exist. The first
slice needs exact acceptance fixtures: valid create, malformed provenance, changed hash,
collision, decision tamper, activation failure, rollback drift, and idempotent intake.
The spec is ready for implementation planning and code, with snapshot scope and policy
field behavior treated as explicit acceptance tests.

## Anonymous Peer Review

### Review A

**Strongest:** Executor, because it translates the revised scope into concrete tests and
prevents the team from implementing the entire capability map at once.  
**Biggest blind spot:** Expansionist does not address how policy fields are rejected or
frozen in V2.0.  
**All responses missed:** The spec should require that an intake result never returns an
activation-ready state; quarantine is a durable state, not just a directory location.

### Review B

**Strongest:** First Principles, because the one-proposal/one-root invariant is now clear.  
**Biggest blind spot:** Outsider assumes setup documentation is part of the spec rather
than an implementation-plan concern.  
**All responses missed:** The active-root path must be canonicalized without following a
skill child symlink or junction into another store.

### Review C

**Strongest:** Contrarian, because snapshot scope and policy ambiguity are the remaining
places an unsafe implementation could hide.  
**Biggest blind spot:** Executor risks making the first release too fixture-driven and
underbuilding real reference impact analysis.  
**All responses missed:** Reports should state scan roots and unscanned roots so users
can distinguish “no reference found” from “not searched.”

### Review D

**Strongest:** Outsider, because the product must communicate that intake is not approval
and approval is not activation.  
**Biggest blind spot:** First Principles underweights operator ergonomics and readable
records.  
**All responses missed:** The spec should define stable status/exit semantics for CLI
commands so automation can safely consume them.

### Review E

**Strongest:** Executor, because it identifies the smallest sequence that can be proved
with the existing repository conventions.  
**Biggest blind spot:** Contrarian treats policy fields as a blocker when the explicit
human approval rule can be enforced by schema and tests.  
**All responses missed:** A generated proposal may contain supporting payload files;
V2.0 must hash and preserve them or explicitly reject non-empty payloads in the first
slice.

## Chairman Synthesis

### Where the Council Agrees

1. The round-one revision corrected the blocking conceptual defects.
2. The create-only, one-active-root lifecycle is a coherent and valuable first release.
3. The proposal/adapter contract is technically defensible without undocumented Hermes
   internals.
4. Quarantine, explicit human approval, hash binding, non-overwriting activation, and
   drift-refusing rollback are the correct safety defaults.
5. V2.0 should be implemented as a vertical slice with schemas and fixtures before broad
   extension of the existing CLI.
6. Supplied LLM review records must remain optional, labeled, and non-authoritative.

### Where the Council Clashes

- The Contrarian wants policy auto-approval fields removed entirely; the Executor and
  First Principles lenses accept reserved fields if the implementation rejects any
  attempt to use them. The safer and more forward-compatible resolution is to retain
  them only as schema-reserved fields, explicitly reject activation when they are true,
  and test that behavior.
- The Expansionist wants broad impact analysis early; the Executor wants a fixture-first
  implementation. The resolution is to implement real read-only scan roots and explicit
  `UNSCANNED_ROOT` reporting in the first slice, while deferring multi-harness adapters.
- The Outsider asks for setup ergonomics in the specification; the Executor places it in
  the implementation plan. The resolution is to make the command contract and exit
  semantics part of implementation acceptance, without expanding the product scope.

### Blind Spots the Council Caught

- Intake must durably remain `QUARANTINED`; it must never emit an activation-ready state.
- Active-root canonicalization must not follow child links/junctions into another store.
- Impact reports must include searched and unscanned roots.
- CLI status and exit-code semantics must be stable for automation.
- Supporting payload files require an explicit hash/preservation rule.

### Recommendation

**APPROVE FOR IMPLEMENTATION, with five mandatory implementation constraints:**

1. Treat policy auto-approval fields as reserved and reject any true value or attempted
   autonomous activation in V2.0.
2. Define snapshot scope as the target skill path plus governance metadata and record all
   hashes; never imply an undocumented whole-catalog transaction.
3. Preserve or reject proposal payload files explicitly. The first slice may reject
   non-empty payloads, but it must not silently ignore them.
4. Implement impact reports with searched-root and unscanned-root fields, and keep
   intake durably quarantined until a separate human decision and activation command.
5. Define stable JSON status values and exit codes in the implementation plan and tests;
   mutation commands must fail closed on every binding mismatch.

These are implementation constraints, not a reason to reopen the product scope. The
specification is approved for implementation planning and code under the existing
release gates V2-G0 through V2-G12.

### The One Thing to Do First

Create the implementation plan and schemas for the one-proposal, one-active-root
create-and-rollback vertical slice, including the five constraints above as tests.

## Round-Two Verdict

**GO — SPECIFICATION APPROVED FOR IMPLEMENTATION.**

Approval is conditional on the five constraints in the recommendation and does not claim
that the current repository implementation already satisfies any V2.0 gate.
