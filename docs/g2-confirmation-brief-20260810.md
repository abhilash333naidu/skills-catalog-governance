# G2 CONFIRMATION RUN — commit generator benchmark (M5b)

**Authority:** PROJECT.md D4 + M5 indicative pass (docs/benchmark-m5-20260810.md)
**Method:** G2 standing gate — ≥3 runs per cell, generator + judge, lead-orchestrated

## Cell matrix (36 generations total)

3 diffs (D1, D2, D3 — below) x 4 conditions (master draft, caveman-commit,
writing-commit-messages, NO-SKILL baseline) x 3 runs each.

## The 3 fixed diffs

### D1 — terminal/osc.go bug fix
```
diff --git a/terminal/osc.go b/terminal/osc.go
@@ -41,7 +41,7 @@ func HandleOSC(seq string) error {
-    if !strings.HasPrefix(seq, "\x1b]") {
+    if !strings.HasPrefix(seq, "\x1b]") || len(seq) < 3 {
         return errors.New("not an OSC sequence")
     }
```
Files: terminal/osc.go. Context: fix crashes on truncated OSC sequences.

### D2 — multi-file feature (api profile endpoint)
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

### D3 — breaking change (checkout rename)
```
diff --git a/api/orders.go b/api/orders.go
@@ -88,7 +88,7 @@
-    r.HandleFunc("/v1/orders", createOrder).Methods("POST")
+    r.HandleFunc("/v1/checkout", createOrder).Methods("POST")
```
Files: api/orders.go. Context: breaking API rename, migration needed by 2026-06-01, old route returns 410 after.

## Skill rule sources (read from disk)

- MASTER DRAFT: C:\Users\abhil\Dev\skill_gov\skills-merge-drafts\caveman-commit.SKILL.md
  (use style: terse for D1-D3 — deterministic default)
- CAVEMAN-COMMIT: C:\Users\abhil\.agents\skills\caveman-commit\SKILL.md
- WRITING-COMMIT-MESSAGES: C:\Users\abhil\.agents\skills\herdr\vendor\libghostty-vt\.agents\skills\writing-commit-messages\SKILL.md
- NO-SKILL baseline: write a good conventional git commit message from the diff, no skill guidance.

## Runner instructions

For each cell (diff x condition), run the generation THREE times independently
(3 separate generations, do not reuse/copy the first). Output EXACTLY this JSON:

```json
{
  "cells": [
    {
      "diff": "D1", "condition": "master|caveman|wcm|noskill", "run": 1,
      "message": "<the generated commit message, verbatim>"
    }
  ]
}
```

36 cells total (3 diffs x 4 conditions x 3 runs). Every message verbatim.
Read each skill file fresh per condition. Judge later by orchestrator.

## Output

Write the full JSON to: C:\Users\abhil\Dev\skill_gov\docs\benchmark-g2-confirmation.json
