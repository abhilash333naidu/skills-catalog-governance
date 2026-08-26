# V2.1 Security & Supply Chain Gate — Tasks

- [ ] Add `schemas/security-audit.schema.json` documenting the scan report shape.
- [ ] Implement OWASP-aligned pattern table + `scan-security` command in `scripts/catalog_governance.py`.
- [ ] Add unit/integration tests: clean PASS, each pattern class FAIL at expected severity, hash binding, threshold exit codes.
- [ ] Run full gates: pytest, ruff, check-package, live `scan-security` smoke run.

## V2.0 Completed Baseline (archived)

- [x] V2.0 lifecycle slice complete: 172 tests pass, coverage 20.23%, Ruff clean, council GO.
- [x] Follow-on evidence items pending separately (Hermes adapter fixture, Windows junction tests).
