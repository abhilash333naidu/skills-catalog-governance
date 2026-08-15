# Governance Model

## Philosophy

Skills Catalog Governance treats AI-agent skill consolidation as an **engineering process** rather than a blind edit. Every operation that changes the skill catalog must pass through deterministic gates that produce evidence — not opinions — about whether the change is safe.

**Core tenet:** Similarity generates candidates. Evidence determines promotion.

## Gates Overview

| Gate | What it enforces | Type |
|---|---|---|
| G0 | Spec conformance (name, description, references) | Deterministic |
| G1 | Static security scan (credential patterns, exec) | Deterministic/regex |
| G2 | Benchmark comparison (master beats sources) | Deterministic/verification |
| G3 | Version discipline + provenance | Deterministic |

Additional proposed gates (G1b — semantic framing, G3.5 — dangling references, G4 — rollback) are documented but not yet implemented as CLI gates.

## Non-Negotiables

1. **Non-destructive** — every removal is a move to `skills-archive/`, never `rm -rf`
2. **Council is mandatory** — never skippable; embedded fallback procedure runs without external skills
3. **Verification discipline** — every claim backed by literal command + literal output
4. **Portability covenant** — masters never use harness-specific prompts, commands, or telemetry
5. **External/vendored skill trees are never edited** — content absorbed in, parent left whole

## States and Transitions

```
PREFLIGHT  ──→ COUNCIL/DRAFT ──→ LOSS_CHECK ──→ APPROVAL ──→ BENCHMARK ──→ PROMOTION
                                                                                │
                                                                                ▼
                                                                           ARCHIVE
                                                                                │
                                                                                ▼
                                                                           POST_AUDIT
```

A failed or stuck state is never treated as complete. Each state transition is recorded with hashes, timestamps, and exit codes.

## Integrity Model

Every operation captures cryptographic digests of the source state BEFORE making changes:

- **Preflight** captures `source_tree_sha256` for each directory
- **Apply** re-verifies digests before moving — refuses if state changed since preflight
- **Cross-device copy** re-verifies digest mid-transfer and after staging
- **Approval** binds `draft_sha256` to the approval document; `verify-approval` re-checks live
- **Journal** records every successful move with post-move digest

This means: tampering with a source after planning, or swapping files during a cross-device copy, is detected and blocks the operation.