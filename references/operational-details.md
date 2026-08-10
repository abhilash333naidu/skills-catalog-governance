# Operational details

**Type:** reference / how-to
**Date:** maintained with the package

Point-of-operation details for running catalog-governance campaigns. Concise cheat-sheet;
the authoritative contracts live in `references/hardening-toolkit.md`.

## Command surface (all read-only unless noted)

```bash
# Preflight (must PASS before a campaign proceeds)
python3 scripts/catalog_governance.py check-package --root . --output run-record/package.json
python3 scripts/catalog_governance.py validate-manifest \
  --root <skills> --manifest <skills>/.audit_manifest.json \
  --output run-record/manifest.json

# Archive moves (plan first, then apply with explicit --apply --yes)
python3 scripts/catalog_governance.py preflight-moves \
  --root <skills> --archive <skills-archive> --manifest <skills>/.audit_manifest.json \
  --plan run-record/move-plan.json
python3 scripts/catalog_governance.py apply-moves \
  --plan run-record/move-plan.json --apply --yes --journal run-record/moves.jsonl

# Merge verification
python3 scripts/catalog_governance.py loss-check \
  --draft skills-merge-drafts/<survivor>.SKILL.md \
  --source <src-a>/SKILL.md --source <src-b>/SKILL.md \
  --output run-record/loss-check.json
python3 scripts/catalog_governance.py verify-approval \
  --draft skills-merge-drafts/<survivor>.SKILL.md \
  --approval run-record/approval.json \
  --loss-report run-record/loss-check.json   # [CHANGED] live re-check binding
```

## Operate conventions

- Keep every run-record JSON/JSONL + the approval with hashes on disk; a prose claim needs
  its evidence artifact (G4).
- `apply-moves` refuses collisions, symlinks/junctions, missing `SKILL.md`, manifest hash
  change, and unexpected tree state; it never deletes or overwrites.
- A partial `apply-moves` run is resumed from `moves.jsonl`; never inferred from console.
- Reference scrub: `check-package --root .` reports missing files in
  `missing_references` (G3).
- Verification record: command lines, stdout/stderr, exit codes, timestamps, hashes, JSON
  reports all under `run-record/`.