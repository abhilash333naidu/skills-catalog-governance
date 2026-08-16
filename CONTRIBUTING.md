# Contributing to Skills Catalog Governance

Thank you for considering a contribution. This project turns skill sprawl into a
governed catalog, and we keep the guardrails tight on purpose. Please read this
guide before opening an issue or a pull request.

## Guiding principles

The project runs on four non-negotiable invariants. Any contribution that violates
one of them will be sent back, no matter how clever it is.

1. **Stdlib-only runtime.** `catalog_governance.py` ships with zero runtime
   dependencies. New features must not add PyPI/pip dependencies to the runtime
   path. Dev-only tooling (pytest, ruff) lives in `requirements-dev.txt`.
2. **Deterministic and reproducible.** Commands must produce stable output. Try to
   keep ordering, hashing, and decision logic independent of filesystem enumeration
   order and wall-clock time.
3. **Non-destructive by default.** Promotion archives and moves skills; it never
   deletes user content. Preserve that guarantee.
4. **Verifiable claims.** Every claim in code and docs must be backed by a literal
   command and its literal output. Refer to the `Evidence` sections in the README.

## Repository layout

```
scripts/     Execution logic (catalog_governance.py and helpers)
tests/       Test suites and fixtures
schemas/     JSON schemas for governance artifacts
references/  Skill-package references format shipped in installs
docs/        Design docs, pilot evidence, benchmark data
assets/      Brand, diagrams, demo media
artifacts/   Raw pilot transcripts and evidence
.github/     CI, templates
```

The package layout is load-bearing: `check-package --root .` verifies that
`scripts/`, `schemas/`, `references/`, and `SKILL.md` are all present. Do not
reorganise the package-critical files (everything `references/` references) without
re-running `check-package`.

## Getting started

```bash
# Runtime requires nothing beyond Python 3.10+.
python --version  # must be >= 3.10

# Dev tooling
python -m pip install -r requirements-dev.txt
```

## Running checks (must all pass)

```bash
# 1. Test suite
python -m pytest tests/ --cov=scripts --cov-report=term --cov-fail-under=20

# 2. Lint (ruff)
ruff check scripts/ tests/

# 3. Package integrity
python scripts/catalog_governance.py check-package --root .
```

These three commands mirror the CI workflow exactly. If CI fails, run them locally
to reproduce before opening the PR.

## Reporting bugs

Use the **Bug report** issue template. Include:

- Expected vs. actual behaviour (paste literal CLI output)
- Steps to reproduce with exact commands
- Environment: OS + `python --version`
- Lifecycle phase (M1–M6) affected

## Proposing features

Use the **Feature request** issue template. State the problem, the proposed
solution, the lifecycle phase it touches, and explicitly call out any trade-off
against the four guiding principles (e.g. "this adds a runtime dependency").

## Submitting a pull request

1. Fork the repo and create a feature branch from `main`.
2. Make focused commits with clear messages.
3. Run the full suite (tests, ruff, check-package) locally.
4. Open a PR using the template. Reference the issue it fixes.
5. The CI matrix (`py3.10`–`py3.13` × Ubuntu/macOS/Windows) must pass.
6. A maintainer reviews and merges after approval.

### PR checklist

- [ ] No new runtime dependencies
- [ ] Deterministic output preserved
- [ ] Non-destructive guarantees preserved
- [ ] Tests cover the change; coverage did not regress
- [ ] `ruff check` clean
- [ ] `check-package` passes
- [ ] Docs updated where behaviour changed

## Code style

- **Linting:** [ruff](https://docs.astral.sh/ruff/) with the default rule set.
- **Formatting:** keep lines readable; follow the surrounding style.
- **Testing:** `unittest` compatible — the existing suite runs under both
  `unittest` and `pytest` (pytest is used in CI for coverage).