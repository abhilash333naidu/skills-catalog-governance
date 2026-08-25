# Spec: Skills Catalog Governance V2.0

**Status:** REVISED DRAFT — round-one council NO-GO resolved; implementation remains blocked until round-two approval  
**Date:** 2026-08-23  
**Target user:** Individual power users running Hermes or a similar local agent harness  
**Product mode:** Offline, local CLI; no hosted service, telemetry, or runtime network dependency

## 1. Objective

Evolve `skills-catalog-governance` from a merge-centric catalog cleanup tool into a
Hermes-first governance layer for automatically generated skills.

The product must answer:

> Can this generated skill be safely admitted and activated, and can the user restore
> the exact previous state if the decision was wrong?

The complete V2.0 vertical slice is:

```text
intake -> quarantine -> evaluate -> approve/reject -> activate -> verify -> rollback
```

V2.0 implements the `CREATE` action for one proposal and one explicitly configured
active root. Update, replacement, retirement, automatic approval, and background drift
repair are deferred until the create-and-rollback loop is verified.

The product does not generate skills, execute agent tasks, intercept undocumented Hermes
internals, or invoke an LLM. Hermes remains responsible for generation and execution.
Governance owns proposal intake, evidence, policy decisions, activation, provenance,
and restoration. It may record a review artifact supplied by a user or another tool,
but that artifact is not independent proof.

### Product promise

**Conservative, evidence-backed skill lifecycle management with reversible activation.**

The product must not claim that an LLM review, similarity score, or user-supplied
benchmark independently proves semantic safety. Evidence sources must remain visibly
separated in reports.

## 2. Capability Map

V2.0 contains six independently testable capabilities. The dependency direction is
one-way and the build order is explicit. The first implementation milestone is one
vertical slice: `proposal-intake` -> `quarantine-lifecycle` -> `risk-policy` ->
`activation-rollback`, with `impact-analysis` and `evidence-record` supplying the
required read-only reports.

| Module ID | Responsibility | Depends on |
|---|---|---|
| `proposal-intake` | Accept and validate generated skill proposals and provenance | Existing package/frontmatter checks |
| `quarantine-lifecycle` | Store proposals outside the active catalog and manage state transitions | `proposal-intake` |
| `risk-policy` | Classify capabilities and apply explicit activation policy | `proposal-intake` |
| `impact-analysis` | Detect duplicates, conflicts, references, and harness wiring affected by a change | `proposal-intake`, `quarantine-lifecycle` |
| `activation-rollback` | Snapshot, activate, verify, archive, and restore catalog state | `quarantine-lifecycle`, `impact-analysis`, `risk-policy` |
| `evidence-record` | Produce deterministic, hash-bound, replayable lifecycle artifacts | All modules |

**Build order:** `proposal-intake` -> `quarantine-lifecycle` -> `risk-policy` ->
`impact-analysis` -> `activation-rollback` -> `evidence-record` integration.

## 3. V2.0 Scope

### Included

- Hermes-first local proposal intake through a documented filesystem/CLI contract
- Quarantine as the default initial state for every generated proposal
- Provenance capture for generator, source task/session identifier, timestamps, and hashes
- Package/frontmatter validation and static security checks
- Capability and risk classification
- Advisory duplicate and conflict analysis
- Reference and harness-wiring impact analysis
- Explicit policy-controlled approval, rejection, and activation for `CREATE`
- Human approval for every activation in the V2.0 implementation
- Snapshot-bound activation and post-activation verification
- First-class, tested rollback to the previous active state
- Read-only drift reporting for governed active skills, without automatic repair
- Machine-readable lifecycle records suitable for replay and audit
- Reuse of existing SHA-256, schema, fail-closed, non-destructive move, and journal patterns

### Explicitly excluded

- Automatic skill generation
- Automatic semantic merging of two or more skills
- Automatic replacement of an active skill based only on similarity
- Update, replacement, and retirement mutation paths in the first vertical slice
- Automatic low-risk approval or activation in the V2.0 implementation
- Background daemon or filesystem watcher
- Native coupling to private or undocumented Hermes APIs
- Cross-harness support as a first-release requirement
- Network calls, hosted dashboards, telemetry, or remote model execution
- Invoking an LLM as part of the offline CLI
- Claiming that static scanning detects all malicious skills or prompt injection
- Fully autonomous activation of any skill
- Editing user-owned commands, hooks, configs, or agent instructions automatically

## 4. Hermes Proposal/Adapter Contract

V2.0 defines a versioned proposal contract and a filesystem/CLI adapter boundary. It
does not claim that Hermes currently exposes a native admission hook. Native Hermes
interception is unverified and out of scope. Hermes or a future adapter may integrate
by either method below; both produce the same governed proposal.

### Method A: Filesystem drop

Hermes or a local adapter writes a complete proposal directory into a configured inbox:

```text
<governance-root>/inbox/<proposal-id>/
  SKILL.md
  proposal.json
  payload/                 optional supporting files
```

The governance CLI consumes the proposal only after validating that the inbox path is
not inside an active skill store and is not a symlink/junction.

### Method B: Captured Hermes adapter submission

The V2 CLI can build a proposal from a captured Hermes skill directory, its `.usage.json`
record, and a separately captured Hermes identity record:

```bash
python scripts/catalog_governance.py capture-hermes \
  --skill-dir /path/to/hermes/skills/<skill-name> \
  --usage /path/to/hermes/skills/.usage.json \
  --metadata /path/to/hermes-capture.json \
  --active-root /explicit/path/to/skills \
  --output /path/to/capture-bundle
```

The adapter requires `created_by: agent` or `agent_created: true`, records an
`ASSERTED_FROM_USAGE` provenance status, and emits a hash-bound receipt. It refuses
non-empty supporting payloads in the create-only V2 path. It does not claim that the
usage record cryptographically proves authorship.

### Method C: Manual CLI submission

A Hermes adapter or a user invokes:

```bash
python scripts/catalog_governance.py intake \
  --skill ./generated/SKILL.md \
  --provenance ./generated/proposal.json \
  --root ./skill-governance \
  --active-root /explicit/path/to/skills
```

The command copies the proposal into a new quarantine record and never writes directly
to the active store.

### Contract stability rules

- Hermes writes a proposal; governance decides whether it becomes active.
- The proposal format is versioned independently from Hermes internals.
- The adapter contract is the supported integration surface; native Hermes hooks are not
  assumed or required for V2.0.
- Unknown fields are preserved in the provenance record but do not change policy.
- Missing required provenance is a validation failure, not an inferred value.
- An intake operation is idempotent for the same proposal ID and content hash.
- A proposal ID collision with different content is a hard failure.
- The active Hermes skill directory is never used as the intake inbox.
- Every operation names exactly one `--active-root`; multi-root activation is forbidden.

## 5. Proposal Format

Each proposal consists of a `SKILL.md` and `proposal.json`.

### Required `proposal.json` fields

```json
{
  "schema": "skill-proposal-1",
  "proposal_id": "uuid-or-unique-local-id",
  "generated_by": "hermes",
  "generator_version": "recorded-or-unknown",
  "generated_at_utc": "2026-08-23T12:00:00Z",
  "source_session": "local-session-id",
  "source_task": "human-readable-task-id-or-empty",
  "skill_sha256": "sha256-of-exact-SKILL.md-bytes",
  "declared_capabilities": ["read_repository"],
  "requested_action": "CREATE",
  "target": {
    "kind": "new_skill",
    "name": "example-skill",
    "active_root": "/explicit/path/to/skills"
  }
}
```

For the V2.0 vertical slice, `requested_action` must be `CREATE`. The schema may reserve
`UPDATE` and `RETIRE_REPLACEMENT` for a later version, but the V2.0 CLI must reject them.
A `CREATE` target must identify `kind: new_skill`, the proposed skill name, and exactly
one `active_root`. The target path must not already exist at activation time.

### Provenance rules

- `skill_sha256` must match the exact bytes received by intake.
- `generated_by` is an attribution field, not a trust guarantee.
- Unknown or missing generator version is recorded explicitly as `unknown` only when
  the field is present with that value; omission fails validation.
- `source_session` is required and may be a local opaque identifier. `source_task` is
  structurally required but may be empty when no kanban task or workflow is bound; neither
  field may be silently replaced with personal data or filesystem guesses.
- The raw proposal and provenance are immutable after intake. A changed proposal is a
  new proposal ID or a new version with a new hash.
- A proposal hash binds the exact `SKILL.md` bytes; a target hash is absent for `CREATE`.
- The active root is an explicit path value, canonicalized and recorded in the intake
  record; path aliases are not treated as separate roots.

## 6. Quarantine Layout and State Machine

The governance root is separate from every active skill store:

```text
skill-governance/
  inbox/                  unprocessed proposals
  quarantine/<id>/        immutable received proposal and evaluation inputs
  decisions/<id>/         approval, rejection, or escalation decision
  snapshots/<id>/         pre-activation catalog snapshot
  archive/<id>/           rejected proposals and future retired versions
  active-records/<id>/    hashes and lifecycle metadata for active skills
  run-record/<id>/        deterministic command outputs and reports
  policy.json             explicit local policy
  lifecycle.jsonl         append-only state transition journal
```

State transitions are fail-closed and append-only in the lifecycle journal:

```text
RECEIVED
  -> QUARANTINED
  -> EVALUATING
  -> REQUIRES_REVIEW
  -> APPROVED | REJECTED | BLOCKED
  -> ACTIVATING
  -> ACTIVE

ACTIVE -> ROLLBACK_PENDING -> RESTORED

Invalid transitions fail closed. `REQUIRES_REVIEW` cannot activate; `REJECTED` and
`BLOCKED` require a new decision record; `ACTIVE` is the only state eligible for
rollback. `DRIFTED`, retirement, and replacement transitions are deferred and
read-only in V2.0.
```

Rules:

- Every proposal starts in `RECEIVED` and must pass through `QUARANTINED`.
- `REQUIRES_REVIEW` is not approval and cannot activate.
- `BLOCKED` means policy or validation prevents activation; it is not a recoverable
  approval state without a new decision.
- A failed activation must leave the active store unchanged or restore it from the
  pre-activation snapshot before reporting failure.
- A proposal is never deleted by governance. Rejected and superseded material is
  retained in the archive according to the configured local retention policy.
- State records include UTC timestamps, actor, command, exit status, input hashes, and
  output artifact paths.
- UTC timestamps are audit metadata and are not used for deterministic identity or
  ordering. Records are ordered by append sequence and carry a monotonically increasing
  local event number.
- Every decision names an explicit local `actor`, decision ID, proposal hash, policy hash,
  and the evidence artifact hashes it reviewed. A file containing `APPROVED` without
  these bindings is invalid.

## 7. Risk and Capability Taxonomy

Classification is conservative and heuristic. Declared capabilities are evidence, not
permission. The static scan detects known textual signals; it cannot prove what a
Markdown skill will do at runtime. The static scan and impact analysis may raise the
effective risk level but may not establish complete behavioral coverage.

| Risk | Capability examples | Default activation |
|---|---|---|
| `LOW` | Formatting, response style, read-only transformation | Quarantine plus explicit human approval in V2.0 |
| `MEDIUM` | Repository reading, planning, code generation, broad context changes | Quarantine plus reproducible evaluation and user review |
| `HIGH` | Filesystem mutation, Git mutation, subprocess execution, network access | Quarantine plus explicit human approval and impact review |
| `CRITICAL` | Credentials, hooks, policy/config mutation, skill-store mutation, activation control | Block automatic activation; explicit human decision plus elevated evidence |

Minimum capability labels:

```text
read_repository
write_filesystem
mutate_git
execute_process
access_network
access_credentials
modify_harness_config
modify_skill_catalog
invoke_other_skills
```

Classification requirements:

- The classifier must emit `declared`, `detected`, and `effective` capabilities.
- A detected capability not declared by the proposal is a provenance discrepancy and
  raises the risk at least one tier.
- A capability scanner is a first-pass control, not a malicious-code proof.
- LLM review may recommend a higher risk level but may not lower a mechanically
  detected risk level.

## 8. Evaluation Model

Evaluation produces separate evidence channels. Reports must not collapse them into one
undifferentiated `PASS`.

| Evidence channel | What it can establish | What it cannot establish |
|---|---|---|
| Package/frontmatter validation | File/package conformance | Behavioral usefulness or safety |
| SHA-256 and snapshot checks | Exact-content and state integrity | Semantic correctness |
| Static capability/security scan | Known patterns and declared/detected behavior | Absence of obfuscation or prompt injection |
| Reference/wiring analysis | Known local consumers that may be affected | Consumers hidden outside scanned roots |
| Similarity/conflict analysis | Candidate overlap or competing scope | Functional equivalence |
| Golden/regression tests | Reproduction for supplied test cases | General correctness outside the cases |
| Supplied LLM council/reviewer artifact | Recorded semantic review and risks | Independent proof, model diversity, or exhaustive coverage |
| Human approval | User accepts the recorded evidence and risk | Truth of claims not actually tested |

A proposal can be approved only when all mandatory evidence for its effective risk tier
is present and passing. V2.0 activation always requires an explicit human decision.
The CLI may record a supplied council/reviewer artifact labeled `LLM_REVIEWED`, but it
never invokes a model, treats the artifact as independent evidence, or lowers a
mechanically detected risk level.

### Required evaluation outputs

- `proposal.json` — immutable intake envelope
- `policy.json` — validated policy snapshot and hash
- `validation.json`
- `capabilities.json`
- `impact.json`
- `similarity.json` when an active catalog is available
- `review.json` when a user supplies an LLM review or human review record
- `decision.json` — human decision bound to proposal, policy, and evidence hashes
- `lifecycle.jsonl` — append-only state transitions
- `active-record.json` — post-activation content and reference hashes

All outputs must carry the proposal ID and relevant input hashes.

## 9. Impact Analysis

Before approval of the V2.0 `CREATE` activation, the CLI must produce a read-only
impact report for the configured active root. Update, replacement, retirement, and
archive-impact mutation rules are deferred.

The report scans configured roots for:

- Skill names and paths in commands, hooks, manifests, and agent profiles
- `AGENTS.md`, `CLAUDE.md`, README files, and harness configuration
- References from the skill body to other governed files
- Active versions, duplicate candidates, and conflicting capability classes
- Symlinks/junctions and canonical paths
- Usage data when the harness provides it

Impact findings are classified as:

```text
NONE
REFERENCE_FOUND
ACTIVE_CONSUMER_FOUND
PATH_COLLISION
CAPABILITY_CONFLICT
UNSCANNED_ROOT
```

Rules:

- Governance never rewrites user-owned wiring automatically.
- A known active consumer must block silent retirement or replacement.
- An unscanned root produces a loud limitation in the report and prevents a claim of
  complete impact analysis.
- Similarity is advisory and must not trigger automatic merge or archive.

## 10. Policy and Autonomy

`policy.json` is explicit, local, versioned, and included in every decision hash.
Defaults are conservative:

```json
{
  "schema": "skill-policy-1",
  "default_state": "QUARANTINED",
  "allow_low_risk_auto_approval": false,
  "require_human_for_low_risk": true,
  "require_human_for_medium_risk": true,
  "require_human_for_high_risk": true,
  "block_auto_activation_for_critical": true,
  "require_snapshot_before_activation": true,
  "require_rollback_test": true,
  "allow_automatic_merge": false
}
```

Policy rules:

- No automatic approval or activation is implemented in V2.0, even if a future policy
  schema contains an auto-approval field. Every V2.0 activation requires a human decision
  artifact recording the exact policy hash.
- Policy can make approval stricter, never weaker than the minimum risk rules.
- A policy change does not retroactively activate quarantined proposals.
- `allow_automatic_merge` is reserved and must remain false in V2.0.
- If policy is missing, malformed, or changed during evaluation, activation is blocked.

## 11. CLI Surface

The command names below are the proposed V2.0 public interface. Existing commands remain
available unless explicitly deprecated in a later approved spec.

| Command | Purpose | Mutation |
|---|---|---|
| `capture-hermes` | Derive a proposal and receipt from captured Hermes evidence | Writes a new capture bundle |
| `intake` | Validate and copy a proposal into quarantine | Writes governance records only |
| `inspect-proposal` | Show hashes, provenance, capabilities, and validation | Read-only |
| `evaluate-proposal` | Run deterministic checks and advisory analysis | Writes evidence only |
| `impact-report` | Scan references, wiring, conflicts, and consumers | Read-only except report |
| `decide` | Record approve, reject, block, or review-required decision for `CREATE` | Writes decision record |
| `activate` | Snapshot and publish an approved `CREATE` proposal to one active root | Mutates active store; explicit confirmation |
| `verify-active` | Re-hash and audit governed active skills | Read-only |
| `rollback` | Restore a named pre-activation snapshot | Mutates active store; explicit confirmation |
| `retire` | Reserved; rejected in V2.0 | No V2.0 mutation |
| `show-record` | Render the complete lifecycle evidence for a proposal | Read-only |
| `check-policy` | Validate policy schema and effective defaults | Read-only |

Mutation commands must require one explicit active-root path, a plan/decision reference,
proposal and policy hash matches, and explicit confirmation flags. The CLI must never
infer approval from a successful evaluation command. One invocation may mutate only one
active root and one proposal.

## 12. Activation and Rollback Contract

Activation is a transaction-like sequence:

```text
validate decision
-> re-hash proposal and confirm `CREATE` target identity
-> validate policy hash and human actor decision
-> create pre-activation snapshot of the one active root's affected path and governance metadata
-> stage proposal outside active store
-> publish without overwrite
-> verify published hash and frontmatter
-> write ACTIVE record
-> retain snapshot and journal
```

If any step fails:

1. Do not report activation success.
2. Restore the pre-activation active tree from the snapshot.
3. Verify the restored tree hash against the pre-activation hash.
4. Record `ACTIVATION_FAILED` and the restoration result.
5. Leave the proposal quarantined for investigation.

Rollback must:

- Require a named snapshot and explicit confirmation.
- Refuse if the affected active path or recorded governance metadata drifted since the
  snapshot. V2.0 has no force-recovery mode.
- Restore the exact prior bytes and paths for the affected `CREATE` activation; preserve
  supported symlink/junction metadata only where the platform snapshot contract covers it.
- Re-run package/frontmatter and catalog discovery checks after restoration.
- Produce a PASS only when the restored hashes match the snapshot.
- Record external edits as a rollback block, never silently overwrite them.

## 13. Drift Detection

For every active governed skill, `active-record.json` records:

- Active path and canonical path
- Skill content hash
- Referenced-file hashes
- Activation decision hash
- Policy hash
- Snapshot ID
- Last verification time

`verify-active` reports:

- `CLEAN` when all recorded hashes match
- `DRIFTED` when content, referenced files, or policy-bound state changes
- `MISSING` when the active path no longer exists
- `UNSCANNED` when a required root cannot be inspected

Drift is evidence requiring a new evaluation. It is not automatically repaired or
silently overwritten. In V2.0, drift reporting is read-only and does not add a repair
transition to the state machine.

## 14. Security and Trust Boundaries

V2.0 protects local state and decision integrity; it is not a complete malicious-skill
detector.

### Always do

- Treat generated skill content and provenance as untrusted input.
- Validate paths, hashes, schema, encoding, symlink/junction status, and collisions.
- Keep quarantine and evidence outside active skill stores.
- Fail closed on missing evidence, changed inputs, or malformed policy.
- Preserve rejected and superseded content non-destructively.
- Make capability escalation visible in the decision report.

### Ask first

- Any new runtime dependency
- Any change to the proposal or policy schema
- Any activation into a real user skill store
- Any automatic approval policy
- Any change to existing move/archive semantics
- Any Hermes-specific integration beyond the versioned filesystem/CLI adapter contract
- Any change from the one-root, create-only vertical slice

### Never do

- Execute generated skill content as part of validation by default.
- Invoke a remote or local LLM as an implicit part of the offline governance CLI.
- Treat supplied LLM output as cryptographic, independent, or exhaustive proof.
- Delete proposal, active, archive, or snapshot content automatically.
- Rewrite commands, hooks, or user configuration to hide impact findings.
- Activate a skill whose proposal or policy hash changed after approval.
- Use a watcher/daemon that can mutate the catalog without a visible command record.

## 15. Testing Strategy

The implementation must remain stdlib-only at runtime and use the repository's existing
Python test conventions.

### Unit tests

- Proposal schema and frontmatter parsing
- Hash binding and proposal ID idempotency
- Capability detection and risk escalation
- Policy defaults and stricter-policy behavior
- State transition validity
- Path traversal, symlink/junction, collision, and encoding rejection
- Evidence records and deterministic ordering

### Integration tests

- Hermes-style inbox proposal -> quarantine
- Quarantine -> evaluation -> decision
- Approved low-risk proposal -> snapshot -> activation -> post-audit
- Failed activation -> exact restoration
- Explicit rollback -> restored hashes match
- Drift detection after active skill modification
- `CREATE` activation with a known active-root reference report
- Rejection and quarantine preserve original bytes
- Cross-platform path behavior for Windows, macOS, and Linux conventions

### Acceptance test scenarios

1. A valid generated skill always lands in quarantine and never directly in the active store.
2. A proposal with a changed content hash is rejected before evaluation completes.
3. A proposal with undeclared filesystem or network behavior is escalated at least one risk tier.
4. A policy file containing any auto-approval setting cannot bypass the V2.0 human
   approval requirement for low-, medium-, high-, or critical-risk skills.
5. Similarity evidence never creates an automatic merge or archive decision.
6. A known active-root reference is reported for a `CREATE` proposal and appears in `impact.json`.
7. Activation creates a snapshot whose hash matches the pre-activation affected state.
8. A simulated publish failure restores the exact pre-activation bytes and reports failure.
9. Explicit rollback restores the snapshot and passes post-restore discovery checks.
10. Active drift is reported read-only and does not silently self-heal.
11. Re-running intake for the same proposal ID and identical hash is idempotent.
12. Reusing a proposal ID with a different hash fails closed.
13. Every PASS/FAIL/ESCALATE result contains proposal ID, input hashes, policy hash when
    relevant, command, timestamp, and artifact references.
14. A fresh clone can run the V2.0 tests and package-integrity checks without network access.

## 16. Evidence and Release Gates

No V2.0 implementation is complete until all gates below pass.

| Gate | Requirement | Evidence |
|---|---|---|
| V2-G0 | Proposal, policy, decision, lifecycle, and active-record schemas validate | Schema test output |
| V2-G1 | Quarantine is enforced for every intake path | Intake integration output |
| V2-G2 | Capability/risk policy is conservative and deterministic | Matrix tests across risk classes |
| V2-G3 | Impact analysis reports known active-root references for `CREATE` | Fixture-based reports |
| V2-G4 | Activation is hash-bound, one-root, create-only, and non-overwriting | Successful and collision test output |
| V2-G5 | Failed activation restores exact prior state | Snapshot/restore hashes |
| V2-G6 | Explicit rollback passes on all supported platforms | Rollback integration output |
| V2-G7 | Drift is detected read-only after content/reference changes | `verify-active` output |
| V2-G8 | LLM and mechanical evidence remain distinct | Artifact schema and report assertions |
| V2-G9 | No automatic merge exists in the V2.0 path | Negative test and CLI audit |
| V2-G10 | Proposal adapter works through the documented contract without private Hermes APIs | Real Hermes capture bundle and intake run |
| V2-G11 | Existing V1/V3 commands and safety guarantees regress-free | Full existing test suite |
| V2-G12 | Package integrity and documentation are complete | `check-package` and docs review |

A release claim must include literal commands, exit codes, hashes, and generated report
paths. Narrative-only claims do not close a gate.

## 17. Migration From Current Product

Existing functionality is retained and repositioned:

| Existing capability | V2.0 role |
|---|---|
| `detect-skills` | Catalog inventory and impact-analysis input |
| `detect-groups` | Advisory duplicate/conflict candidates only |
| `check-master` | Proposal package validation where applicable |
| `golden-gate` | Optional evidence for generator/formatter proposals |
| `benchmark` | Optional evaluation evidence; not automatic proof |
| `loss-check` | Advanced consolidation evidence, outside default intake |
| `verify-approval` | Pattern for hash-bound lifecycle decisions |
| `preflight-moves` / `apply-moves` | Safety foundation for archive and rollback operations |
| `install` | Package distribution; not the Hermes admission contract |

Existing merge workflows remain available as an advanced, manually initiated path. V2.0
must not silently reinterpret an existing merge command as automatic admission.

The V2.0 implementation deliberately defers update, replacement, retirement mutation,
automatic approval, multi-root operation, native Hermes hooks, and automatic drift repair.
Those are follow-on specifications, not hidden promises in the create-only release.

## 18. Open Questions Before Implementation

These questions do not block approval of the product direction, but must be answered in
the implementation plan:

1. What exact governance-root layout and active-root configuration should the first
   implementation expose, given that V2.0 permits one active root per invocation?
2. Which provenance fields are available from the real Hermes-side adapter, and which
   adapter-produced fields are mandatory before intake?
3. What is the minimum supported active-store layout for the first adapter fixture?
4. Which Windows junction metadata is in the supported snapshot contract, and which is
   explicitly unsupported?
5. Should the approved `CREATE` proposal be copied into the active store or atomically
   renamed when the filesystem permits it?
6. What retention policy preserves evidence without unbounded archive growth?
7. How should externally supplied LLM review artifacts be validated and labeled without
   claiming model independence?

## 19. Approval Gate

This document is a product and architecture specification only. No implementation should
begin until the user explicitly approves:

- The revised create-only vertical slice for one active root
- The V2.0 product promise and proposal/adapter boundary
- The quarantine-first default
- The risk taxonomy and human approval requirement
- The complete create lifecycle including rollback
- The exclusion of automatic merging, updates, retirement, and auto-approval from V2.0
- The filesystem/CLI proposal adapter contract as the initial Hermes boundary
- The acceptance and release gates in this document

After approval, the next artifact is an implementation plan with module-level tasks and
verification checkpoints. Changes to the scope above require updating this specification
before code is written.
