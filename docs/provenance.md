# Provenance

## Overview

Provenance tracking ensures that every consolidated skill in the catalog can be traced back to its sources. This is maintained through several mechanisms operating at different points in the lifecycle.

## Source Tracking

| Artifact | What it records |
|---|---|
| Council verdict | Survivors, absorbed skills, recategorizations, gates passed |
| G3 frontmatter | `merged-from:` list of source paths |
| Move plan journal | Every file moved with pre-move and post-move SHA-256 |
| Package check | SHA-256 of the installed SKILL.md |

## Council Verdict Schema

```yaml
verdict: MERGE
survivors:
  - canonical-commit-message
recategorizations:
  - ce-commit            # executor, not generator
absorbed:
  - writing-commit-messages
  - git-commit-formatter
gates_passed:
  - G0
  - G1
  - G3
```

## G3 Version Discipline

Every consolidated master must declare:
- A **quoted semver version** (prevents YAML float truncation)
- A **`merged-from:`** list recording every skill directory absorbed
- A **name** matching the installation directory

## Package Integrity

Installation is verified via `check-package`, which validates:
- All required files present (SKILL.md, scripts/, schemas/, references/)
- Referenced schema files are valid JSON (content-checked, not just presence-checked)
- SKILL.md SHA-256 is recorded

## Limitations

- External/vendored skill trees have no provenance integration — content is absorbed, but the vendor source is not tracked beyond a `read_only: true` tag in discovery
- No cryptographic signing of provenance records
- No end-to-end trace ID linking M1 discovery through M6 promotion for unmerged skills