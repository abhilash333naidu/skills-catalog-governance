# Hardening Gates G0–G4 (detail bodies)

> Part of the `skills-catalog-governance` package. `SKILL.md` (Hardening Gates section) keeps
> the intro paragraph and the gate→source mapping table; the full gate bodies and their
> process detail live here. These gates are BINDING and are re-checked at every promotion.

## G0. Catalog hygiene

Self-check on the root catalog. Violations (line length 121–400, description >1024, or
`name != directory` mismatch) earn a `[SCRATCH]` scratch-scratch marker and 2-minute
dedicated cleaning before the campaign starts. All hygiene checks are read-only.

### Check

```bash
python3 scripts/catalog_governance.py check-package --root . --output run-record/package.json
```

Rules:

- `description` must be `<=1024` characters.
- Any line of `SKILL.md` 121–400 characters long earns a `[SCRATCH]` scratch-scratch marker
  and dedicated cleaning.
- `name` in frontmatter must equal the directory name.

### Note (live)

This package currently violates G0's `name == directory` rule (frontmatter `name:
skills-catalog-governance`, directory `skill_gov`). A mismatch exists at the package root
itself. Fix = rename the directory to `skills-catalog-governance` (or flip the
frontmatter `name`). Chosen pending: rename the frontmatter `name` to match the
directory is simplest, but this package lives at `skill_gov/` with the skill acting on
`skills/` — root-level naming is cosmetic until the promotion gate runs; the gate makes
it real.

## G1. Loss-check

Also called "the 6-of-5 loss-check" (six input sources, five expected loss areas).
Mechanical definition: `catalog_governance.py loss-check` compares draft to sources,
reporting word overlap, missing headings, missing fenced commands, and draft/source
hashes. `PASS` = mechanical checks cleared (still `manual_review_required: true`).
`REVIEW` = lead must investigate and document. On PASS, the lead also manually verifies
and records hashes. Approval text must echo the loss-check result, not summarize it.

## G1b. Post-merge parity

Required at every merge/rework to prevent the "merged but subtly lost it" failure class:
after the merge, the lead re-runs the loss-check; mechanical losses must stay at exactly
0; then a NEW (complete, standalone) session verifies EVERY command from EVERY source
against the merged file; a fully working copy lives in drafts. Process: for each merged
skill, run `loss-check --draft <merged> --source <each-source>` (each run: zero missing
headings, zero missing commands); run a fresh-session `plan` read of every command; fix,
don't defer; on first improvement to a merged skill, place a fully working copy under
`skills-merge-drafts/` (or a fully working copy of that skill goes live).

## G2. Post-move revalidation

Required at every move. Fail-closed revalidation at destination. `check-package --root .`
against the FULL target package (packaging, rules, self-check); `validate-manifest` against
the updated manifest; `check-package --root <target>/skills` to re-check the catalog.
Retry only after the earlier block fully explains the later block's failures (a retry that
re-checks everything and passes all 3 stages is acceptable). Confirm the move is complete
before recording the event: the manifest was updated, the tree hash was recorded, and the
event hit the provenance log. If destination already contains an equal `SKILL.md`, the move
is a no-op (idempotent), not an error.

## G3. Dangling-reference scrub

Required at every promotion. Any backticked `references/X.md` in `SKILL.md` must resolve
to an existing file. All reference files live under `references/`. Relative paths to
`scripts/`, `schemas/`, or other artifacts may remain plain backticks and are covered by
G0/check-package instead. Sanity: the references list in `SKILL.md` and the reference
files on disk must MATCH. Renaming or deleting a reference file is a failure unless
`SKILL.md` is updated in the same change. Verification: `check-package --root .` reports
missing files in `missing_references`; or `for f in $(echo references/*.md); do echo
$f; done` for the on-disk list.

## G3.5. Distribution-evidence parity (SKILL.md package section ↔ references/*)

The `Distribution: SKILL.md + references/* + scripts + schemas` claim must hold in BOTH
directions: (a) every file under `references/` that is REQUIRED by the package contract
appears in the `SKILL.md` References section — file not listed in `SKILL.md` → added, and
(b) every reference listed in the `SKILL.md` References section must exist on disk (G3).
Implement by making check-package's required-file set derive from SKILL.md, and reconcile
the References section against the on-disk file list in the same scrub pass.

## G4. Traceability audit (council source-attribution)

The audit validates that verifiable claims reference a real source. Claims supported by
run-record evidence, earlier counsel files, or council-verdict files are "explicitly
cited"; audit flags any claim that does not trace to a source. Evidence, files, and
provenance logs must be present or the claim is unflagged-but-unverified. Concrete rule:
claims like "package passed its own gates at promotion" must reference a concrete file
(e.g. `run-record/package.json`, `council-verdict-*.md`) that exists. The default source
of truth for the audit is the skill's own narrative; the full artifact trail is in
`references/`. If a source citation fails at promotion time, the audit is FAIL and the
promotion is refused, giving a clear, non-blocking path to fix and re-verify. Gate status
remains FAIL until every citation is added. The final audit is done with FRESH context
(fresh session, plan-mode, full artifact scan) — "bias to the artifact, not the memory."