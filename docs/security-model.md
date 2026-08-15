# Governance-Driven Safety and Integrity

## Scope

Skills Catalog Governance includes security and integrity controls as part of its governance pipeline. These controls protect against **accidental** data loss, tampering, and unsafe operations during skill consolidation.

**This is not a comprehensive security scanner for malicious or poisoned skills.** The project's G1 static scan is a first-pass regex check — it catches obvious credential exposures and code-execution patterns but cannot reliably detect intentional attacks, semantic prompt injections, or obfuscated payloads.

## What Is Implemented

### SHA-256 Tree Integrity

Every move operation computes a SHA-256 digest of the entire source directory tree (filenames, symlink targets, and file contents). The digest is recorded in the preflight plan and re-verified before any move executes. Cross-device copies are verified mid-transfer and after staging.

### Hash-Bound Approval

Approval documents are cryptographically bound to the exact draft content they approve (`draft_sha256`). The `verify-approval` command re-checks the live draft hash against the approval — a mismatch blocks promotion.

### Tamper Detection

If a source skill is modified between preflight planning and execution, `apply-moves` detects the hash change and refuses to proceed. If a source changes between loss-check and approval re-verification, the gate fails.

### Non-Destructive Archival

The tool never deletes. Skills targeted for removal are moved to a timestamped archive directory. Both `--apply` and `--yes` flags are required to execute any move — a single flag alone is refused.

### Hardened Runner Execution

The golden gate runner has multiple safety layers:
- Runners are **disabled by default** — explicit opt-in required
- Shell metacharacters (`;&|`$()<>*?[]{}!`) are refused in runner arguments
- Inline-code executor arguments (`-c`, `-e`, `--eval`, etc.) are refused
- NUL bytes are refused
- Runners execute with a configurable timeout (max 120s)

### Fail-Closed Promotion Gates

Every promotion gate (`check-master`, `golden-gate`, `benchmark`, `verify-approval`) produces a structured PASS/FAIL result. A FAIL result blocks the next phase — no best-effort partial success.

### Provenance Tracking

Consolidated skills carry a `merged-from:` provenance list recording every source they were built from. Council verdicts record survivors, absorbed skills, and recategorizations. Move operations produce a journal of every file moved with its destination hash.

### Multi-Stage Verification

Before any skill is promoted, it passes through:
1. Loss-check (content coverage against every source)
2. Golden-gate (output reproduction, where applicable)
3. G2 benchmark (head-to-head against every source)
4. Approval verification (hash-bound, live re-checked)
5. Lock-based concurrency protection

## What Is NOT Implemented

- Semantic/adversarial framing detection (G1b — proposed)
- Dependency lockfile verification (proposed)
- Cryptographic signing of skill provenance
- External-source trust tiering or signature verification
- Runtime agent monitoring or drift detection
- Cross-skill interaction analysis
- CVE/vulnerability database integration

These are acknowledged gaps that would strengthen the system in future iterations.