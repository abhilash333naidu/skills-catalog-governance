## Peer Reviews (Anonymous, A–E)

**A (on CONTRARIAN):** Strongest response. It's the only advisor that identifies a genuine fail-closed violation: hash-matching in `decide` letting content edits clear HIGH blocks without re-evaluation — that's a real security hole, not style. The YAML-parser critique is concrete (anchors, duplicate keys) and the "tripwire not boundary" relabeling is honest. Blind spot: it never questions whether the IR is needed at all — it improves the parser spec instead of deleting the component; also assumes fuzzing capacity this solo project may lack.

**B (on FIRST PRINCIPLES):** Best strategic filter. The yardstick test (does each phase amplify gating/approval/rollback?) is the only evaluation framework anyone applied, and "IR when the fourth consumer appears" is correct YAGNI discipline. Calling Phase 3 byte-matching "theater" is half-right and overstated — deterministic grading of *extracted* output has value even if prompts are non-deterministic. Blind spot: offers no sequencing or amendment detail; "cut Phase 4" without saying what ships first leaves the plan gutted rather than amended.

**C (on EXPANSIONIST):** Most ambitious, least grounded. The verify-catalog-as-vendored-script idea and hash-linked decision log are genuinely cheap, good amendments. But it proposes pivoting to public trust infrastructure with zero evidence of demand — exactly the "no consumer exists" problem B flags, at larger scale. Talking to skills.sh/clawhub maintainers *before* finalizing adapters is its one saving gate. Blind spot: never engages the security mechanics (parser, decide hole); distribution enthusiasm substitutes for threat modeling.

**D (on OUTSIDER):** Valuable as the only reader-proxy: "assume readers don't know OpenClaw/ASPM" applies to the project's own docs, not just marketing. Correctly spots the exporter's missing-consumer problem independently of B. But it critiques framing while ignoring substance entirely — no position on the parser, the fail-closed hole, or phase ordering. Blind spot: "byte-match feels like overkill" contradicts the project's core threat model; it evaluates cost without evaluating attack surface.

**E (on EXECUTOR):** Only advisor that opened the repo, which earns weight: golden-fixture-before-refactor and splitting undersized Task 4.1 are actionable today. The precise normalization rule (trailing whitespace + CRLF→LF, exact otherwise) resolves the contradiction others merely noticed. Blind spot: source omission aside, it operates purely at task granularity — it approves-with-amendments without testing whether any phase should exist at all. Its four amendments polish a plan whose foundations A and B are challenging.

**What ALL missed:** No one addressed operational ownership — who reviews the human-approval queue, on what SLA, and what happens when the maintainer is the attack vector (skills written by the same person who runs the pipeline). Nobody proposed a single end-to-end adversarial test fixture (a deliberately malicious skill) to validate the whole chain. And none quantified false-positive rates for Phase 3 against even a small honest corpus.

---

## Where the Council Agrees

The hand-rolled YAML subset parser is the weakest link and must not ship as-is — either fully specified grammar plus fuzzing, or cut ASPM/IR now (A, B agree on cut; A alone would tolerate spec-first). The exporter (Phase 4 as specified) lacks any consumer and shouldn't be built until one exists (B, D, and C implicitly, since C would *create* consumers first). Regex scanning must be labeled a tripwire, never a boundary (A, B). The grader is the highest-value phase (D, E, partially C). Normalization rules need a byte-precise definition before anything byte-compares (A, E).

## Where the Council Clashes

**Phase 4's fate:** B says delete until a consumer exists; C says invert it into publishing normalized catalogs outward after talking to maintainers. C's version isn't wrong so much as unpriced — it converts a liability question into a go-to-market bet the other four never audited.

**Byte-matching's worth:** B calls Phase 3 "theater" because LLM outputs are non-deterministic; D calls the grader the most useful phase. Both are right about different halves: prompt-level matching is fragile, but structural/deterministic grading of extracted artifacts is sound. The clash dissolves if Phase 3 grades structure loudly and treats behavioral claims as advisory.

**Scope posture:** E wants to proceed with amendments inside the existing plan; A wants to block on two security holes; B wants to shrink the plan. This is amend-and-proceed versus amend-and-defer.

## Blind Spots Caught

A caught the decisive one: `decide`'s hash-match-only refusal means editing skill content silently clears a HIGH block — fail-closed fails open under the most obvious adversary action. B caught premature abstraction (IR with no consumer). D caught communication failure (jargon, assumed ecosystem knowledge). E caught planning failure (Task 4.1 mis-sizing). All caught by only one reviewer each — which is itself the argument for the panel.

## The Recommendation

Proceed **in amended form**, reordered:

1. **Fix the decide hole before anything else.** Hash mismatch during decide must force re-evaluation (re-run scan/grade), never fall through to approve. Fail-closed must survive content edits.
2. **Cut ASPM and the hand-rolled YAML parser from Phase 2.** Parse frontmatter per-format at point of use; revisit an IR only when a fourth consumer appears. Ship SKILL.md-only support.
3. **Resequence: Phase 3 (grader) next, with E's normalization rule adopted verbatim** — strip trailing whitespace per line, CRLF→LF, exact otherwise — plus a written fenced-block extraction grammar. Label regex findings as tripwires; keep the HIGH hard-block.
4. **Split 4.1 into 4.1a/4.1b** per E; capture golden fixtures before the 2.2 refactor.
5. **Defer the exporter** until a named external consumer commits — if the maintainers C proposes actually respond, Phase 4 returns as their spec, not ours.

Adopt C's two cheap items regardless: schema-versioned lockfile and the ~50-line hash-linked decision log.

## The One Thing to Do First

Write and merge the forced re-evaluation fix in `decide`, with a regression test proving that modifying a blocked skill's bytes cannot yield APPROVE without a fresh scan.

COUNCIL VERDICT: GO WITH CHANGES — required changes: (1) decide forces re-evaluation on hash drift, (2) cut YAML-subset parser/ASPM from Phase 2, ship SKILL.md-only, (3) adopt explicit normalization rule + fenced-block grammar before any byte-comparison ships, (4) split Task 4.1, capture golden fixtures pre-refactor, (5) defer exporter pending a committed external consumer.