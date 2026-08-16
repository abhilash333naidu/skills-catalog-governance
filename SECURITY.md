# Security Policy

This project **governs skill consolidation**, and consolidating content that may
include third-party contributions carries a real security surface. This document
describes the controls in place and how to report a vulnerability.

## Reporting a vulnerability

Please **do not open a public issue** for suspected security vulnerabilities.
Report privately to the maintainer at:

- **GitHub Security Advisory:** use the repo's "Report a vulnerability" flow
  (a private disclosure channel) at
  <https://github.com/abhilash333naidu/skills-catalog-governance/security/advisories/new>

Include:

- A description of the issue and its potential impact
- Steps to reproduce, with literal commands and output
- The affected module/CLI command and lifecycle phase (M1–M6)
- Proposed fix, if you have one

You will receive a response within **7 days**. Please give us a reasonable window
(up to 90 days) to address the issue before public disclosure.

## Supported versions

| Version | Supported          |
|---------|--------------------|
| main    | Active development |
| Latest release | Security fixes | 

Only the current `main` branch and the latest tagged release receive security
patches.

## Security scope

This project includes **security and integrity controls** as part of its
governance pipeline, but it is **not a comprehensive security scanner** for
malicious or poisoned skills. Know the boundary.

### In scope

- **SHA-256 tree integrity** — verified before, during, after movement
- **Hash-bound approval** — approvals cryptographically bound to draft content
- **Drift detection** — source changes post-review block execution
- **Non-destructive archival** — the archive, never deletes
- **Hardened runner execution** — golden runners disabled by default; shell
  metacharacters refused
- **G1 static scan** — first-pass regex check for obvious credential exposures
  and code-execution patterns

### Out of scope (known limitations)

- No semantic prompt-injection analysis (XML tag check in description only)
- No comprehensive dependency / CVE scanner (simple unpinned-range check)
- No cross-skill interaction / dynamic collision detection
- No cryptographic signing infrastructure (file hashes only)

A full, honest gap analysis lives in
[`docs/security-model.md`](docs/security-model.md).

## Reporting a suspected defect vs. vulnerability

- **General defect / crash:** use the **Bug report** issue template.
- **Security concern (possible credential exposure, injection, data-loss path):**
  use the private report above.

## Responsible disclosure

We aim to acknowledge receipt within **48 hours** of a private report and to
provide a fix for in-scope, confirmed issues in a security release as soon as
practically possible. We appreciate the community reporting responsibly and will
publicly credit reporter(s) upon resolution when requested.