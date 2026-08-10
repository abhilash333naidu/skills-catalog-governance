# M2 SPEC — Grouping / Similarity Net (2026-08-10)

## Goal

Add a new subcommand `detect-groups` to scripts/catalog_governance.py that takes
the M1 inventory and flags CANDIDATE similar-skill pairs — never a merge decision.

## Method (paper-verified, arXiv:2603.22447 SkillClone)

Flat TF-IDF cosine similarity (precision .897 / recall .867 / F1 .881 on
SkillClone-Bench) + word-overlap as a second signal. Pure stdlib ONLY (no
sklearn, no numpy — this repo is stdlib-only, fail-closed).

## Input

- `--inventory <path>`: JSON file produced by `detect-skills` (list of
  {store, path, name, description, sha256}).
- `--threshold <float>`: cosine threshold, default 0.30 (over-flag bias: false
  positives cost a wasted read; false negatives miss a group entirely — worse).
- `--output <path>`: optional JSON output path (else stdout via emit()).

## Algorithm (pure stdlib)

1. Build corpus: one document per skill = `name + " " + description` normalized
   (lowercase, tokenize on non-alphanumerics, drop stopwords, drop single
   chars). NOTE: normalize whitespace in description (split + rejoin) BEFORE
   tokenizing — multi-line `|` block scalars must not corrupt tokens.
2. Compute term frequencies per doc; IDF = log((N+1)/(df+1)) + 1 (smooth).
3. TF-IDF weight per term per doc; cosine similarity between all pairs (O(n^2)
   — n=211 → 22k pairs, trivial).
4. ALSO compute word-overlap: |intersection| / |min(len_a, len_b)| on the same
   normalized token sets (this catches near-identical skills that TF-IDF may
   underweight).
5. Flag a pair as candidate if cosine >= threshold OR word_overlap >= 0.50.
6. NEVER output a merge decision. Output pairs with both scores + the flags.

## Output schema (emit() report, status PASS)

```json
{
  "status": "PASS",
  "counts": {"skills": 211, "pairs": 22155, "candidates": N},
  "threshold": 0.30,
  "candidates": [
    {"a": "name-a", "b": "name-b", "path_a": "...", "path_b": "...",
     "cosine": 0.55, "word_overlap": 0.62, "flagged_by": ["cosine", "overlap"]}
  ],
  "suggested_groups": [["name-a", "name-b"]]
}
```

`suggested_groups` = connected components of the candidate graph (union-find
or BFS, stdlib). This is a SUGGESTION for M3 council scope, not a decision.

## Fail-closed

- Missing/unreadable inventory → status FAIL + error message.
- Empty inventory → PASS with counts 0 (not an error).
- Malformed inventory entry (missing name/path) → FAIL with details.
- No external deps; import only stdlib.

## Tests (add to tests/test_catalog_governance.py)

- T1: two identical descriptions → cosine ~1.0, flagged by both.
- T2: two completely different descriptions → cosine ~0, NOT flagged.
- T3: two near-identical with different wording → overlap >= 0.50 catches it.
- T4: connected components — A~B, B~C → suggested_groups [[A,B,C]].
- T5: empty inventory → PASS, counts 0.
- T6: multi-line description (`|` block scalar) does not break tokenization.
- T7: threshold 0.30 default vs 0.50 strict — stricter yields fewer candidates.

## Gate (orchestrator runs, never subagent)

- `python -m pytest tests/ -x -q` passes.
- `python scripts/catalog_governance.py detect-groups --inventory <real>
  --threshold 0.30` runs on the REAL 211-skill inventory; report candidates
  count + top 10 by cosine with literal output. Candidates must include the
  gstack family and caveman family (known near-duplicates) but the orchestrator
  does the final judgment.
