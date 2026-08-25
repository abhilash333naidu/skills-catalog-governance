# V2.0 Specification Council Review — Round 1

**Date:** 2026-08-23  
**Artifact reviewed:** `docs/spec-v2.0-20260823.md`  
**Decision requested:** Approve the specification for implementation, or identify required changes first.

## Independence Notice

This review follows the repository's five-advisor plus peer-review procedure as five
adversarial lenses applied by one underlying model in this environment. The lenses are
not five independent model providers. Findings are therefore structured review signals,
not statistically independent consensus.

## Framed Question

Is the V2.0 specification sufficiently coherent, bounded, technically implementable,
and safe to approve for implementation as a Hermes-first, quarantine-first local skill
lifecycle controller? Identify blocking defects, required changes, and whether the
specification should proceed to implementation.

## Advisor Responses

### The Contrarian

The document is directionally strong but not approval-ready. Its largest risk is that it
promises a complete lifecycle while leaving the hardest boundaries unresolved: what
Hermes actually emits, which active store is governed, how an update identifies its
replacement target, and how rollback handles user changes after activation. The proposal
format requires provenance fields that may not exist in real Hermes output, while the
integration section calls the filesystem drop a contract without evidence that Hermes can
write to it. The state machine also has an ambiguity: low-risk policy-controlled approval
has no explicit transition, yet evaluation only leads to `REQUIRES_REVIEW`. Finally,
"snapshot exact previous state" is too broad unless the snapshot scope and platform
metadata rules are defined. Reject for implementation until these are narrowed.

### The First Principles Thinker

The core product is not "Hermes integration" yet; it is a local admission controller with
a stable proposal envelope. The spec should distinguish the invariant from the adapter:
Governance receives an immutable artifact, evaluates it, and controls activation. Hermes
is only one producer. Starting from that invariant exposes unnecessary V2.0 promises:
full retirement, drift monitoring, multi-action replacement, and automatic approval can
be staged after the first complete create-and-rollback loop. The minimum coherent product
is intake, quarantine, inspect, decide, activate one new skill, verify, and rollback.
Deduplication and impact analysis should remain read-only evidence. The spec needs an
explicit single-active-root boundary and a declaration that native Hermes hooks are not
validated by this repository.

### The Expansionist

The opportunity is larger than cleanup: a governed skill registry can become an audit
trail for agent-generated behavior. But that future is endangered by overloading V2.0.
A strong foundation would make the proposal envelope extensible, preserve unknown fields,
include adapter metadata, and define a durable lifecycle journal. It should also make
review evidence pluggable: deterministic checks, human decisions, and optional LLM
reviews should be separate typed artifacts. Do not build a watcher or autonomous merge.
Invest in the contract and records first, because those enable future Hermes, Claude,
OpenCode, or Codex adapters without changing the safety core.

### The Outsider

A new user cannot tell what to run first, where the active skill directory is, or whether
this tool actually intercepts Hermes-generated skills. The phrase "Hermes-first" implies
an existing integration that the document does not prove. The commands are proposed but
there is no concrete one-command happy path with required roots and expected states. The
risk labels sound precise even though a static scan of Markdown cannot prove that a skill
will perform network or filesystem actions. The spec should state what the tool knows,
what it infers, and what it cannot see. It should also remove ambiguous action names such
as `RETIRE_REPLACEMENT` or define their target fields.

### The Executor

The spec can be implemented, but not at the current breadth without turning the first
release into a large rewrite of a 2,059-line single-file CLI. Define a vertical slice:
`intake -> quarantine -> evaluate -> decide -> activate -> verify -> rollback` for one
skill and one explicitly configured active root. Add schemas and tests before adding
retirement, update semantics, broad wiring scans, or auto-approval. Every mutation needs
an explicit root, proposal ID, decision hash, snapshot ID, and confirmation flag. The
current repository already has hash-checked moves and package validation, but it does not
have lifecycle records, proposal schemas, or rollback commands. Treat those as new work,
not as existing capabilities.

## Anonymous Peer Review

### Review A

**Strongest:** First Principles, because it separates the stable governance invariant from
an unproven Hermes adapter and gives a smaller coherent product boundary.  
**Biggest blind spot:** Expansionist underestimates the migration complexity of adding a
new record system to a single-file CLI.  
**All responses missed:** The spec needs a precise definition of the active root and must
forbid activation across multiple roots in one operation.

### Review B

**Strongest:** Executor, because it maps the review into a buildable vertical slice and
identifies the missing implementation artifacts.  
**Biggest blind spot:** Outsider focuses on user confusion but does not distinguish a
proposal contract from a native Hermes hook.  
**All responses missed:** The approval authority and actor model are unspecified; a
machine-readable `APPROVED` file must not be accepted without an explicit local actor and
input hash binding.

### Review C

**Strongest:** Contrarian, because it finds concrete contradictions in transitions,
provenance, action names, and rollback scope.  
**Biggest blind spot:** Executor assumes the current CLI architecture must be extended in
place; an internal module split or a new lifecycle module may be needed before feature
work.  
**All responses missed:** The spec needs deterministic timestamp and ordering rules so
records are replayable without pretending timestamps are deterministic.

### Review D

**Strongest:** Outsider, because the product promise currently overstates Hermes
integration and static risk detection.  
**Biggest blind spot:** First Principles cuts too much of the lifecycle and risks making
V2.0 merely an intake utility rather than a useful product.  
**All responses missed:** The rollback contract needs to state what happens when external
edits occur after activation and before rollback; fail-closed refusal should be the
normal behavior.

### Review E

**Strongest:** Executor, because it provides a safe sequence that can be verified with
fixtures and existing stdlib conventions.  
**Biggest blind spot:** Contrarian identifies problems but does not prioritize which ones
are release-blocking.  
**All responses missed:** Optional LLM review conflicts with the offline/no-remote-execution
position unless the spec explicitly says the governance CLI records supplied review
artifacts and never invokes a model in V2.0.

## Chairman Synthesis

### Where the Council Agrees

1. The product direction is valid: quarantine-first, hash-bound, reversible lifecycle
   governance is a stronger V2.0 than automatic merging.
2. The current spec is **not approved for implementation**.
3. The first release must have a smaller vertical slice centered on one explicitly
   configured active root and one proposal at a time.
4. The Hermes boundary must be described as a versioned proposal contract or adapter
   contract, not as a proven native Hermes admission hook.
5. Static capability analysis must be described as heuristic signal detection, not proof
   of runtime behavior.
6. Rollback must refuse by default when active state drifted after the snapshot.
7. LLM review must be optional, externally supplied evidence in the offline CLI; the CLI
   must not imply model independence or invoke a remote model as part of governance.

### Where the Council Clashes

- The Expansionist wants a broad, extensible registry foundation immediately; the Executor
  wants only the smallest create-and-rollback loop. The resolution is to design extensible
  record schemas but implement only the create path in the first vertical slice.
- The First Principles lens would defer update and retirement entirely; the Contrarian
  treats their ambiguous presence as a safety problem. The resolution is to mark update,
  replacement, and retirement as explicitly deferred until create activation and rollback
  are verified, rather than leaving partially specified behavior in the V2.0 contract.
- The current direction permits policy-controlled low-risk auto-approval; several lenses
  recommend no automatic activation until the lifecycle is empirically proven. The safer
  resolution is to keep policy extensibility in the schema but disable auto-approval in
  the V2.0 implementation and release gates.

### Blind Spots the Council Caught

- No single active-root boundary or multi-root activation rule.
- No exact target identity for update/replacement actions.
- No actor/approval authority contract.
- No distinction between deterministic record fields and wall-clock timestamps.
- No explicit behavior for post-activation external edits before rollback.
- The offline claim is ambiguous while LLM review is listed as an evaluation channel.
- The existing CLI has no lifecycle record or proposal-schema implementation despite the
  spec's implication that these are already nearby capabilities.

### Recommendation

**REVISE, DO NOT IMPLEMENT YET.** Make the following changes mandatory before a second
approval review:

1. Narrow V2.0 implementation scope to `CREATE` for one skill and one active root, with
   intake, quarantine, evaluation, explicit decision, activation, verification, and
   rollback. Mark update, replacement, retirement, drift repair, and auto-approval as
   deferred or read-only follow-on design.
2. Rename the Hermes integration claim to a versioned proposal/adapter contract and state
   that native Hermes interception is unverified and out of scope.
3. Add `--active-root` and exact target identity rules; prohibit multi-root operations.
4. Add proposal target fields and a clear action model; for the implemented create path,
   require no existing target and refuse collisions.
5. Define state transitions completely, including approved/rejected/blocked paths and
   invalid-transition failures.
6. Define actor, decision, policy hash, proposal hash, and snapshot hash binding.
7. Change capability detection language to heuristic signals with confidence and limits.
8. Clarify rollback drift refusal, snapshot scope, and cross-platform metadata limits.
9. State that V2.0 records externally supplied LLM review artifacts but does not invoke
   models or claim independent model evidence.
10. Add a concrete happy-path command sequence and map required new schemas/artifacts.

### The One Thing to Do First

Revise the specification into a narrow, executable create-and-rollback contract with one
active root, explicit hashes, complete state transitions, and no implied Hermes hook.

## Round-One Verdict

**NO-GO FOR IMPLEMENTATION — SPEC REVISION REQUIRED.**
