## What does this PR do?

Briefly describe the change and which lifecycle phase (M1–M6) it touches, if any.

## Related issue(s)

Fixes #<!-- issue number --> · Relates to #<!-- issue number -->

## Type of change

- [ ] New feature
- [ ] Bug fix
- [ ] Docs / README
- [ ] Refactor / cleanup
- [ ] CI / tooling

## How was this tested?

- [ ] `python -m pytest tests/`
- [ ] `ruff check scripts/ tests/`
- [ ] `python scripts/catalog_governance.py check-package --root .`
- [ ] Manual: <!-- describe commands run and observed output -->

## Checklist

- [ ] Stdlib-only runtime preserved (no new runtime dependencies) unless explicitly approved
- [ ] Changes remain deterministic / reproducible
- [ ] Non-destructive archival guarantees preserved
- [ ] Docs updated where behaviour changed
- [ ] Test coverage did not regress

<!--
For behavioural changes, paste the literal command(s) and literal output in the test section
so reviewers can verify claims directly.
-->