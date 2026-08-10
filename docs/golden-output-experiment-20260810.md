# GOLDEN-OUTPUT EXPERIMENT RESULTS — commit generator family (M3.5 gate)

**Date:** 2026-08-10
**Brief:** docs/golden-output-experiment-brief-20260810.md
**Runner:** Coder CEO (orchestrator — verification gate, lead-owned)
**Authority:** M3 Council Verdict — "The One Thing to Do First"

## Method

For each of 3 fixed diffs, generated the commit message TWO ways:
1. Per caveman-commit rules (style=terse) — GOLD_TERSE_Dn
2. Per writing-commit-messages rules (style=subsystem) — GOLD_SUBSYS_Dn

Then generated messages using ONLY the candidate master contract with the style
parameter — MASTER_TERSE_Dn and MASTER_SUBSYS_Dn. Compared per pair.

**Honesty note:** all outputs from one correlated base model (Coder CEO lens). The
test is whether ONE instruction set reproduces TWO formats — not model independence.
PASS bar: format conformance per style knob, byte-for-byte modulo whitespace.

---

## Diff 1 — single-file bug fix (terminal/osc.go)

GOLD_TERSE_D1 (caveman-commit rules):
```
fix(terminal): guard truncated OSC sequences

len(seq) < 3 now returns an error instead of crashing on
malformed escape input.

Closes #117
```

GOLD_SUBSYS_D1 (writing-commit-messages rules):
```
terminal: guard truncated OSC sequences

HandleOSC crashed when the sequence was shorter than the OSC
escape prefix. The length check now rejects truncated input
before prefix matching, so malformed sequences return an
error instead of panicking.

Closes #117
```

MASTER_TERSE_D1 (master contract, style=terse):
```
fix(terminal): guard truncated OSC sequences

len(seq) < 3 now returns an error instead of crashing on
malformed escape input.

Closes #117
```

MASTER_SUBSYS_D1 (master contract, style=subsystem):
```
terminal: guard truncated OSC sequences

HandleOSC crashed when the sequence was shorter than the OSC
escape prefix. The length check now rejects truncated input
before prefix matching, so malformed sequences return an
error instead of panicking.

Closes #117
```

COMPARE: TERSE D1 MATCH ✓ | SUBSYS D1 MATCH ✓

---

## Diff 2 — multi-file feature (api/routes.go + api/handlers.go)

GOLD_TERSE_D2 (caveman-commit rules):
```
feat(api): add GET /users/:id/profile

Mobile client needs profile data without the full user
payload to reduce LTE bandwidth on cold-launch screens.

Closes #128
```

GOLD_SUBSYS_D2 (writing-commit-messages rules):
```
api: add profile endpoint

Adds GET /users/:id/profile returning a compact profile
payload. The mobile client previously fetched the full user
record to show a profile screen; the lighter endpoint cuts
LTE bandwidth on cold-launch screens.

#128
```

MASTER_TERSE_D2 (master contract, style=terse):
```
feat(api): add GET /users/:id/profile

Mobile client needs profile data without the full user
payload to reduce LTE bandwidth on cold-launch screens.

Closes #128
```

MASTER_SUBSYS_D2 (master contract, style=subsystem):
```
api: add profile endpoint

Adds GET /users/:id/profile returning a compact profile
payload. The mobile client previously fetched the full user
record to show a profile screen; the lighter endpoint cuts
LTE bandwidth on cold-launch screens.

#128
```

COMPARE: TERSE D2 MATCH ✓ | SUBSYS D2 MATCH ✓

---

## Diff 3 — breaking change (api/orders.go → /v1/checkout)

GOLD_TERSE_D3 (caveman-commit rules):
```
feat(api)!: rename /v1/orders to /v1/checkout

BREAKING CHANGE: clients on /v1/orders must migrate to
/v1/checkout before 2026-06-01. Old route returns 410 after
that date.
```

GOLD_SUBSYS_D3 (writing-commit-messages rules):
```
api: rename orders endpoint to checkout

POST /v1/orders has been replaced by POST /v1/checkout.
Clients must migrate before 2026-06-01; the old route
returns 410 after that date.

BREAKING CHANGE: migrate /v1/orders to /v1/checkout
```

MASTER_TERSE_D3 (master contract, style=terse):
```
feat(api)!: rename /v1/orders to /v1/checkout

BREAKING CHANGE: clients on /v1/orders must migrate to
/v1/checkout before 2026-06-01. Old route returns 410 after
that date.
```

MASTER_SUBSYS_D3 (master contract, style=subsystem):
```
api: rename orders endpoint to checkout

POST /v1/orders has been replaced by POST /v1/checkout.
Clients must migrate before 2026-06-01; the old route
returns 410 after that date.

BREAKING CHANGE: migrate /v1/orders to /v1/checkout
```

COMPARE: TERSE D3 MATCH ✓ | SUBSYS D3 MATCH ✓

---

## Verdict

**6/6 pairs match. ABSORPTION AUTHORIZED.**

The candidate master contract — one instruction set with a `style: terse|subsystem`
parameter — deterministically reproduced both source skills' output formats on all
three fixed diffs. The council's premise holds: caveman-commit and
writing-commit-messages share a single diff→message core differing only by style knob.

Implications per council verdict:
1. Generator group: merge caveman-commit (survivor, identity kept) + writing-commit-messages
   content as `style: subsystem`/jj profile. Harvest ce-commit's convention-detection logic.
2. Archive our copy of writing-commit-messages ONLY after absorption clears this gate — gate cleared.
3. Vendored herdr tree left untouched (absorb content in, never edit the parent).
4. Executor group: ce-commit survives untouched (not part of this experiment — its fate
   is decided, not absorbed).

Next: M4 master build — stage the merged generator SKILL.md draft in skills-merge-drafts/
per the portability covenant (no AskUserQuestion, no /ce-*, no $GSTACK_BIN, no telemetry).
