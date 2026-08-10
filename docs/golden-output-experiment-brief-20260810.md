# GOLDEN-OUTPUT EXPERIMENT — commit generator family (M3.5 gate)

**Date:** 2026-08-10
**Authority:** M3 Council Verdict (docs/council-verdict-commit-family-20260810.md), "The One Thing to Do First"
**Purpose:** Verify the council's central empirical premise — that caveman-commit and
writing-commit-messages share a single deterministic diff→message core, differing only
by a style parameter (terse vs subsystem). If a single parameterized instruction set
reproduces both output formats byte-for-byte on fixed diffs, absorption is authorized.
If not, the merge dies and we keep both + a routing table.

## Source skills (full rules)

- **caveman-commit** (style=terse): Conventional Commits `type(scope): imperative summary`,
  types feat/fix/refactor/perf/docs/test/chore/build/ci/style/revert, subject ≤50 chars
  (hard cap 72), no trailing period, body only for non-obvious why (bullets `-`, wrap 72,
  `Closes #42`/`Refs #17`), no AI attribution, no emoji. NEVER runs git commit — output
  only, code block, paste-ready.
- **writing-commit-messages** (style=subsystem): `subsystem: summary` prefix from file
  paths (e.g. terminal, vt, lib, config, font; nested terminal/osc), lowercase start,
  imperative, whole subject <60 chars, references on own lines (`#1234`) after blank
  line when present, long-form prose body (what changed / previous behavior / how it
  works now), wrap ~72, `jj` auto-detection if `.jj` exists.

## The candidate master contract (to test)

A single instruction set with ONE style parameter:
- `style: terse` → Conventional Commits `type(scope):` subject, bullets body, Closes/Refs trailers, subject ≤50
- `style: subsystem` → `subsystem:` subject (from diff paths), references section, prose body, subject <60
- Shared: imperative mood, no trailing period, wrap 72, why-over-what, never push, output-only (no git commit)
- Deterministic default: terse

## Fixed diffs (3 representative scenarios)

### Diff 1 — single-file bug fix (terminal)
```
diff --git a/terminal/osc.go b/terminal/osc.go
@@ -41,7 +41,7 @@ func HandleOSC(seq string) error {
-    if !strings.HasPrefix(seq, "\x1b]") {
+    if !strings.HasPrefix(seq, "\x1b]") || len(seq) < 3 {
         return errors.New("not an OSC sequence")
     }
```
Files: terminal/osc.go. Context: fix crashes on truncated OSC sequences.

### Diff 2 — multi-file feature (profile endpoint)
```
diff --git a/api/routes.go b/api/routes.go
@@ -120,6 +120,15 @@ func registerRoutes(r *mux.Router) {
+    r.HandleFunc("/users/{id}/profile", getProfile).Methods("GET")
```
```
diff --git a/api/handlers.go b/api/handlers.go
@@ -1,3 +1,6 @@
+func getProfile(w http.ResponseWriter, r *http.Request) {
+    // load profile, return JSON
+}
```
Files: api/routes.go, api/handlers.go. Context: mobile client needs profile without full user payload (bandwidth).

### Diff 3 — breaking change (checkout rename)
```
diff --git a/api/orders.go b/api/orders.go
@@ -88,7 +88,7 @@
-    r.HandleFunc("/v1/orders", createOrder).Methods("POST")
+    r.HandleFunc("/v1/checkout", createOrder).Methods("POST")
```
Files: api/orders.go. Context: breaking API rename, migration needed by 2026-06-01, old route returns 410 after.

## Experiment steps (run via opencode, build agent)

1. **Golden outputs per source skill:** For each diff, write the commit message as
   caveman-commit's rules demand (style=terse). Then write it as writing-commit-messages'
   rules demand (style=subsystem). 6 outputs total. Label them GOLD_TERSE_D1..D3,
   GOLD_SUBSYS_D1..D3.
2. **Master outputs:** Using ONLY the candidate master contract above, generate messages
   for each diff with style=terse (MASTER_TERSE_D1..D3) and style=subsystem
   (MASTER_SUBSYS_D1..D3). 6 outputs total.
3. **Compare:** MASTER_TERSE_Dn must equal GOLD_TERSE_Dn (modulo whitespace) and
   MASTER_SUBSYS_Dn must equal GOLD_SUBSYS_Dn. Report PASS/FAIL per pair with the diff.
4. **Verdict line:** "ABSORPTION AUTHORIZED" if 6/6 pairs match; "ABSORPTION DENIED —
   keep separate + routing table" if any pair fails.

## Output

Write the complete experiment results to docs/golden-output-experiment-20260810.md:
the fixed diffs, all 12 outputs, per-pair comparison, and the verdict line.

## Honesty note

All outputs come from the same correlated base model — this tests whether ONE
instruction set can reproduce two formats, not model independence. The PASS bar is
format conformance per style knob (byte-for-byte modulo whitespace), which is exactly
what the council specified.
