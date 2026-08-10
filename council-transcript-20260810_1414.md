# LLM Council Transcript — skills-catalog-governance full design review

- **Counciled:** 2026-08-10 14:14
- **Runtime:** 5 advisors → 5 anonymous peer reviews → 1 chairman (sub-agents)
- **Method:** LLM Council (Karpathy adaptation), 5 thinking-style lenses on one underlying model

## Original question (user)

"Full design review of skill_gov"

## Framed question

Counciled topic: full design review of "skills-catalog-governance" (skill_gov), a self-contained agent skill for maintaining coding-agent skill catalogs — governed pipeline (PREFLIGHT → COUNCIL/DRAFT → LOSS_CHECK → APPROVAL → PROMOTION → ARCHIVE → POST_AUDIT) backed by a stdlib-only fail-closed CLI (preflight-moves/apply-moves with --apply --yes, sha256 tree hashes, append-only JSONL journal, never deletes), 4 advisory JSON schemas, hardening gates G0-G4 (G0 = name==dir / ≤1024-char desc / <500-line body; G1 static security regex; G2 empirical A/B LLM-judged; G3 version/provenance; G1b/G3.5/G4 proposed). Incident history: 6 defect classes found, only 5 shipped; G0 caught 1,342-char description; 71-vs-72 rogue subagent write; G2 pilot 15/15 vs 9/15. Known state: v2.1.0-draft NOT PROMOTED; check-package fails (17 references/*.md missing); 680-line SKILL.md violates its own <500 rule; __pycache__ committed; single-model council/judge (correlated judgment admitted).

**Question for advisors:** Is this governance design genuinely trustworthy for moving/merging a user's skill directories, what is its single weakest point that must be fixed before relying on it, and does the raw trust hold given the incomplete package and self-violated rules — or is that all cosmetic?

## Advisor responses

### The Contrarian

Fatal flaw not mechanics — judgment monoculture. Loss-check, repair-brief, post-audit: same underlying model, shared blind spots. #6 shipped missing precisely because writer+checker+auditor think alike. Post-audit caught it — but post-audit runs on same model. Admission of correlated judgment is not mitigation. Every "thinking" step has one failure mode; mechanical gates can't catch semantic omission.

Second: self-violations not cosmetic. Package fails own check-package, violates own <500-line G0, ships __pycache__ — still packaged for use. Evidence gates aspirational, not enforced. "Fail-closed" claim, not observed behavior. Tool governing user skill dirs has broken own dir.

Third: "never deletes — moves only" legalistic comfort. Wrong move worse than delete — scatters skill across tree, journal happily records. G3.5 dangling-reference scrub PROPOSED only; own package has dangling references TODAY. Governs exact fragility it exhibits.

Weakest point, fix first: repair-brief closure loop. Make it mechanical. Loss-check emits per-defect numbered checklist; promotion blocked until every defect accepted 1:1. Never let prose summary close numbered list — that's exactly how #6 escaped. Then independent verifier (different model or human) on final re-audit.

Verdict: not trustworthy for user dirs yet. Mechanical core (hash, sha256, append-only journal) sound. Judgment layer monoculture + self-violated rules = governance theater. Fix closure loop, enforce own gates on itself, then re-judge.

### The First Principles Thinker

The wrong question first. "Trustworthy for moving directories?" — the moves are the safest part of this whole system. Hash-verified sources, append-only JSONL, no deletes, symlink refusal: that mechanical core is well-engineered. The actual trust question is the *quality gates* — and there the answer is no.

Single weakest point: one model in a costume. The 5-advisor council is 5 personas of the same weights. Anonymous peer review anonymizes the same model. Loss-check judge, G2 judge, same model. This isn't a correlation limitation — it's the load-bearing wall, and it's made of jelly. Any systematic under-detection (a defect class the model doesn't recognize) propagates unfiltered through every gate. The 6th defect class shipping missing isn't an anomaly; it's the system's fixed point. Mechanical gates bind humans to artifacts; semantic gates bind the model to itself. Self-reference yields zero independent confidence by construction.

Incomplete package, violated rules: not cosmetic — behavioral evidence. The system exists to catch name==dir, line limits, missing references. Then it shipped 680 lines, 17 missing files, __pycache__ committed. Either gates never ran on the shipping artifact, or they ran advisory. Both are fatal: governance you can walk around is fiction. The 71-vs-72 rogue write confirms it — a post-final subagent write bypassed the entire pipeline. You govern a moment, not a flow.

Fix before trust: gates must be executable, blocking, and runtime-enforced — fail-closed means the CLI refuses when G0 fails, not warns. And decouple judgment: one external anchor (human sign-off, different model, ground-truth fixtures) per semantic claim. Until then: use the mechanical moves, ignore the council.

### The Expansionist

The governance machinery is the product, not the skill. This is a certification layer for the emerging agent-skill economy — every org running Claude Code, opencode, or Codex is accumulating a skill/prompt/agent registry with zero audit discipline. That's a horizontal platform: skill governance, prompt governance, MCP-config governance, agent-memory governance. You're sitting on the compliance standard the whole market lacks.

The undervalued asset is the incident history. Real integrity failures — the 71-vs-72 count catching a rogue post-final subagent write, the 6th defect class found but never shipped — is empirical proof the thesis works. The tool caught its own violations. That isn't embarrassment; that's the demo reel.

So the "incomplete package" is mostly cosmetic for the move/merge trust question: the operations are mechanically bound by hashes, lockfiles, append-only journals, and fail-closed semantics — content completeness doesn't affect move safety. What it DOES affect is promotion readiness, and that's where the value lives. Nobody pays for a draft.

Weakest point to fix before relying on it: the single-model council/judge. Correlated judgment caps the certification claim — an auditor certified by its own auditor is folklore, not assurance. Fix: make the judge provider-swappable and require ≥2 independent models for loss-check and approval binding. That one change transforms this from a useful script into a defensible standard.

And the G2 stat — 15/15 vs 9/15, a 67% uplift — is your sales collateral. Dogfood it, promote v2.1.0, then license the pattern.

### The Outsider

Zero context, first read. This machine weighs its own meat.

A governance pipeline that fails its own check-package (17 missing files), violates its own <500-line rule (680), and ships a defect its own loss-check found — because the repair brief carried only 5 of 6 classes — is not governed. It's aspirational. That 5-of-6 incident isn't cosmetic; it's the threat model falsified from inside. The exact failure class this design exists to prevent (incomplete handoff) occurred inside the governance layer.

Trustworthy for user skill directories: no — yet. The mechanical bones are sound: moves-only, never deletes, per-source sha256 re-verify, append-only journal, symlink/junction refusal. Destructive risk is genuinely low. But the written-approval binding is only as strong as the human who transcribed the brief. Weakest point: approval is a paper handoff, not a mechanical closure. The 6th defect shipped because nothing forced the approval artifact to enumerate all six findings. Fix that: verify-approval must diff the approval record against the live set of detected conditions — not just the draft hash. A hash binds version; it binds nothing about completeness. The 71-vs-72 count discrepancy proves state mutates after "final" — so approve the state, not the draft.

Committed __pycache__ and self-violated rules aren't cosmetic either. Rules with no enforcement are documentation, and this tool's enforcement is advisory by design. Until it passes its own gates on its own repo, don't point it at anyone's live skills.

Trust the mechanics. Don't trust the paperwork.

### The Executor

Verdict: trust the *mechanics*, don't trust the *promotion claim*. The fail-closed apply path — re-verify manifest hash, per-tree sha256, destination lock, append-only journal, refuse symlinks, move-only, never delete — is the right architecture for moving user directories. The 71-vs-72 rogue-write incident is evidence the design catches exactly the failure it's built to catch. But that's "safe to apply," not "ready to promote." The broken package and self-violated rules are promotion blockers, not evidence the apply path is untrustworthy — provided the gates are hard-enforced.

Single weakest point: the repair-brief handoff. Loss-check surfaced 6 defect classes; the human brief carried 5; the 6th shipped. Every other link re-verifies mechanically at apply. The brief is the one unverified, uncounted, provenance-free handoff in the chain. Fix: machine-stamp loss-check output — class IDs plus count — into the journal, then make the pre-apply gate re-run loss-check and assert current class set equals the brief's recorded set. A dropped class then fails the gate instead of shipping. Cost: one afternoon. Until that lands, the weakest link is an untyped human copy-paste.

Cosmetic question: partially. Incomplete package is real but self-limiting — check-package fails, so promotion is blocked today. That's fail-closed working, not hypocrisy. But 680-line SKILL.md and committed __pycache__ are trust erosion you can fix in minutes: enforce the <500 rule as a hard G0 check or change the rule; delete the cache, add .gitignore.

Monday checklist: (1) confirm apply-moves refuses while check-package fails — if not, make it; (2) count-stamp loss-check classes into the brief and assert at apply; (3) fix the hygiene items. Done. Then rely on it.

## Anonymization mapping

For the peer-review round, advisor responses were labeled A–E at random (fixed-point shuffle to avoid positional bias).

- Response A = The First Principles Thinker
- Response B = The Executor
- Response C = The Contrarian
- Response D = The Outsider
- Response E = The Expansionist

## Peer reviews

### Review 1
1. **Strongest: D.** Most precise root-cause. "A hash binds version; it binds nothing about completeness" unifies both incidents — the 5-of-6 brief and the 71-vs-72 mutation — under one failure mode: approval binds a stale or incomplete artifact, not verified state. Concrete fix (diff approval against live detected-condition set), correctly scopes "safe for moves vs not ready to promote," and avoids the monoculture rabbit hole the others over-index on.
2. **Biggest blind spot: E.** E answers a market question, not the trust question. Calls the shipped 6th defect a "demo reel" — but that defect is the exact class the pipeline exists to prevent, failing *inside* the governance layer. That's falsification, not validation. Recommends promoting v2.1.0 while check-package fails: operationally wrong against known state.
3. **Missed by all:** Apply-path atomicity and recovery. Everyone trusts "append-only journal" as safety evidence; none asks whether a multi-tree apply is transactional, what happens on crash mid-apply, or whether the journal can *restore* a bad move. Append-only ≠ recoverable. Also: mechanical core trusted without a demonstrated test suite, and the lone empirical stat (G2 15/15) is self-judged by same model — methodology never interrogated.

### Review 2
1. **Strongest: A.** Separates mechanical core from semantic gates correctly. Names monoculture as root, not symptom. Reads self-violations as behavioral evidence gates are advisory — not hypocrisy. A states structural consequence precisely.
2. **Biggest blind spot: E.** Inverted the evidence. Incident history = "demo reel"; broken package = "mostly cosmetic"; advises promoting v2.1.0 and licensing. Ignored that self-violation proves advisory-only enforcement. E answered a market question, not the governance question.
3. **All five missed:** the *merge* half of "moving/merging." Every response analyzes move safety only. Merge demands conflict resolution, non-commutative outcomes, partial-batch crash states — append-only journal logs, it does not recover. Nobody asked for pre-apply snapshot or rollback of user's live dirs. Secondary: all assume a diligent human exists — but this is an agent skill, likely run unattended; every "paper handoff" fix presumes human attention that may never materialize.

### Review 3
1. **Strongest: D.** It isolates the most implementable failure: approval binds a draft *hash*, not *completeness* — "approve the state, not the draft." Reading the 71-vs-72 incident as proof state mutates post-final makes D's fix (diff approval record against live detected-condition set) concrete and derived from actual incident, not theory. A and C flag monoculture — structurally real — but harder, less imminent fix; D named the link that demonstrably shipped defect #6.
2. **Biggest blind spot: E.** E answered a different question — commercial "compliance standard / demo reel" framing — and called the broken package "mostly cosmetic." Wrong for the trust question: a governance layer that fails its own gates on its own repo cannot certify anyone else's.
3. **All five missed:** recovery and atomicity. Nobody asked what happens when apply fails mid-operation — partial move across trees, split state, no restore path. None proposed pre-apply backup or rollback verification. On win32: file locks, MAX_PATH, OneDrive sync are real blast-radius risks. Also absent: ground-truth fixtures to test the gates themselves.

### Review 4
1. **Strongest: C.** Most calibrated and complete. Only response that splits the evidence right: mechanical core sound; judgment layer monocultural; self-violations behavioral, not cosmetic. Names the empirically proven weakest link — brief carried 5 of 6 defect classes — and fixes it mechanically (numbered per-defect checklist, promotion blocked until 1:1 closure), while keeping the monoculture ceiling and adding the unique point (G3.5 only proposed; own package has dangling refs today). B close second: cleanest apply-vs-promote trust split and cheapest fix, but ignores correlated judgment.
2. **Biggest blind spot: E.** Calls the 5-of-6 escape and broken package "the demo reel," "mostly cosmetic," then urges promoting v2.1.0 — which check-package currently blocks. E inverts the evidence: #6 escaped at the brief, not at judgment; that's the threat model falsified from inside, not validation.
3. **All five missed:** The question says "moving/merging"; every answer audits moves only. Merge semantics — collisions, content divergence, winner arbitration, history continuity — untouched. And none flags the meta-case: this review panel is the same single model, so consensus here is correlated judgment in action, not independent corroboration.

### Review 5
1. **Strongest: C.** Only it frames both tiers correctly: judgment monoculture as the systemic flaw, but the loss-check→repair-brief closure as the actionable weakest point — precisely where the incident occurred (#6 detected, dropped in prose, shipped). Unique insight: "moves-only" is legalistic comfort; a wrong move scatters a skill. Avoids A's overreach ("ignore the council") and B's over-charity.
2. **Biggest blind spot: E.** It inverts the anchor incident. Loss-check found all 6 classes; the brief carried 5; the 6th shipped — a delivery failure, not "the tool caught its own violations." E converts it into demo-reel collateral, blesses promoting a draft it simultaneously says needs a monoculture fix, and calls the broken package "mostly cosmetic."
3. **All five missed:** Apply atomicity/crash recovery. No one asked what happens when a multi-dir apply is interrupted mid-batch — partial moves, journal replay, re-run semantics. Journal integrity is unverified: "append-only" is a convention; nothing hash-chains entries or detects rewrites. G2's n=15 single-run uplift is celebrated (E) or ignored — never statistically questioned.

## Chairman synthesis

### Where the Council Agrees

1. **The mechanical core is sound.** All five advisors, and all five peer reviews independently, hold this: move-only (never deletes), per-source sha256 re-verify at apply time, destination lock, symlink/junction refusal, append-only JSONL journal, stdlib-only fail-closed CLI. The 71-vs-72 rogue-write incident is read differently (proof the design detects its target vs. proof state mutates after "final") — but no one disputes that the apply path has genuinely low destructive risk. This is the strongest independent convergence in the record.

2. **The judgment layer is monocultural, and that is structural, not incidental.** Five personas, one set of weights; loss-check, G2 judge, council, peer review all share blind spots. The #6 escape is the fixed point of the design, not an anomaly — writer, checker, and auditor think alike, and "admission of correlated judgment" is not mitigation. Even the Expansionist, who wants to promote, concedes the judge must become provider-swappable with ≥2 independent models before any certification claim holds.

3. **The empirically demonstrated weakest link is the loss-check → repair-brief → approval handoff.** Loss-check found 6 defect classes; the brief carried 5; #6 shipped. Every advisor that proposes an actionable fix converges on mechanically closing this handoff — the Contrarian's numbered 1:1 defect closure, the Executor's class-ID + count stamping with re-assertion at apply, the Outsider's "approve the state, not the draft." This is the one point grounded in incident evidence rather than theory, which is why three of five reviews rate the Outsider/Contrarian analysis as the strongest.

4. **The self-violations are not cosmetic.** Four of five advisors (Contrarian, First Principles, Outsider, Executor) and all five peer reviews read 17 missing references, the 680-line SKILL.md, and committed `__pycache__` as behavioral evidence: the gates run advisory or not at all, on the one artifact this tool is supposed to govern. Unenforced rules are documentation. The Executor's one legitimate nuance — check-package failing means promotion *is* blocked, so the incomplete package partly self-limits — does not erase the other two violations.

5. **There are two different trust questions, and only one is answered.** "Is the apply path safe to run?" — yes, mechanically. "Is the promotion claim ready to rely on?" — no; v2.1.0-draft is correctly unpromoted, and the failing check-package is that state working as intended. The council's honest consensus: trust the mechanics, distrust the paperwork.

### Where the Council Clashes

1. **The Expansionist vs. the other four: what do the self-violations and incident history mean?** The Expansionist reads the 1,342-char G0 catch, the 71-vs-72 detection, and the six-class loss-check as a demo reel — proof the thesis works — calls the broken package "mostly cosmetic," and recommends promoting v2.1.0 and licensing the pattern. The other four read the same evidence as the threat model falsified from inside: a governance layer that dropped defect #6 in its own handoff and ships violating its own G0 cannot certify anyone's skills. All five peer reviews independently name this as the biggest blind spot — unusual unanimity. The disagreement is genuine because the objectives differ: the Expansionist optimizes for the market value of the machinery; the rest optimize for this artifact's trustworthiness with live directories. The question asked was the latter. The Expansionist's *facts* are correct — the incident history does demonstrate detection capability — but the inference (promote now, sell the pattern) fails on both the evidence and the known state (check-package blocks promotion). Chairman sides with the majority.

2. **What is the single weakest point: the monoculture or the brief handoff?** The Contrarian, First Principles Thinker, and Expansionist argue the monoculture is THE weakness — it caps the entire certification claim and cannot be fixed by mechanics. The Outsider and Executor argue the brief handoff is — it is the link that demonstrably failed, recently, in production of the tool's own package. Peer reviews split on who is strongest but consistently concede both tiers. This is less a contradiction than two timescales: the monoculture is the load-bearing ceiling over any future certification claim; the brief handoff is the floor that has already collapsed. Fix the floor first — it is demonstrated, cheap, mechanical — then raise the ceiling by adding one independent anchor (different model or human) to the final re-audit.

3. **Is "never deletes" a safety property or legalistic comfort?** Most of the council treats move-only as the design's saving grace. The Contrarian notes a wrong move is worse than a delete — it scatters a skill across the tree and the journal happily records it — a point peer review (Review 5) flags as the session's unique insight. It doesn't overturn the mechanical-core consensus, but it correctly reframes "never deletes" as reducer-of-blast-radius, not guarantee-of-correctness.

4. **Is check-package failing fail-closed working, or proof the enforcement is advisory?** The Executor argues self-limiting: promotion is blocked, so the system behaved. The others argue advisory-by-design: the gates never ran on the shipping artifact, so "blocking" was coincidental to the package simply not having been shipped. Both observe the same behavior. The resolution is testable — whether enforcement is hard-wired into the apply/approve paths — and that test is the first thing to run (below).

### Blind Spots the Council Caught

1. **Apply atomicity and crash recovery — missed by all five advisors, flagged by all five reviews.** "Append-only journal" was treated as safety evidence; no one asked whether a multi-tree apply is transactional, what a mid-batch crash leaves behind, whether the journal can restore a bad move, or what re-run semantics are. Append-only ≠ recoverable. Review 3 adds this platform's reality: file locks, MAX_PATH, OneDrive sync — real blast radius.

2. **The merge half of "moving/merging" — missed by every advisor; flagged by Reviews 2 and 4.** Every response audited moves only. Merge is entirely unaudited: conflict resolution, content divergence, winner arbitration, history continuity, non-commutative outcomes, partial-batch crash states. The journal logs merge results; it does not define, validate, or recover them.

3. **Journal integrity is unverified — Review 5.** "Append-only" is a convention. Nothing hash-chains journal entries or detects rewrites. The same mutation class the 71-vs-72 check caught in trees is unaddressed in the journal itself.

4. **Every fix presumes a diligent human — Review 2.** The approval handoff presumes someone reads the brief carefully. This is an agent skill, likely run unattended. Mechanical gates must not depend on human attention to be safe.

5. **G2's 15/15-vs-9/15 statistic was never interrogated — Reviews 1 and 5.** n=15, single run, judged by the same model that generated the comparison. Under the council's own monoculture critique, that stat is weak evidence — the Expansionist's "sales collateral" framing ignores the methodology problem everyone else concedes.

6. **No test suite or ground-truth fixtures — Reviews 1 and 3.** The mechanical core is trusted on design, not demonstrated behavior. Known-good / known-bad fixtures would let every gate assert real behavior instead of intent.

7. **The meta-blind spot — Review 4.** This review panel is the same single model. Its consensus is correlated judgment, not independent corroboration. The chairman owns this: it raises the epistemic bar, which is why this verdict weights incident-derived convergence (the brief handoff, the journal, the counts) above preference convergence (monoculture disputes, market framing).

### The Recommendation

**Trust the mechanics. Do not trust the promotion claim — yet. Do not approve or apply anything until the handoff is mechanical.**

Direct answers to the three questions:

1. **Trustworthy for moving user skill directories?** The apply path — yes, provisionally. Hash re-verification, destination locking, move-only, append-only logging, symlink refusal, and fail-closed semantics are the right bones, and the 71-vs-72 incident shows the design detects the mutation class it targets. The governance layer around those moves (council → loss-check → approval) is not yet trustworthy: its enforcement is advisory, its closure was blown once producing its own package, and its judgment is single-model.

2. **Single weakest point?** The loss-check → repair-brief → approval handoff — the one link that empirically dropped defect class #6. The monoculture is the ceiling; the brief is the floor that already failed. Fix the floor.

3. **Is the raw trust broken, or is it all cosmetic?** Not cosmetic. Self-violated rules on one's own package are behavioral evidence of advisory enforcement. But they do not invalidate the mechanical core, and they are cheaply fixable. The incomplete package is correctly blocking promotion today — that part is fail-closed working, as the Executor argues — yet it remains proof of advisory-only governance until the gates are hard and the package passes its own.

The chairman sides with the majority against the Expansionist's promote-and-license advice: it misreads a delivery failure as validation and contradicts known state. The chairman adopts the minority's valid kernel — the Expansionist's provider-swappable, ≥2-model binding for loss-check/approval — as the ceiling fix; the Outsider's "approve the state, not the draft" as the floor fix; and the Executor's apply-vs-promote split as the operative mental model. Before this system governs a user's live skill directories: (a) close the handoff mechanically; (b) hard-wire gates into apply/approve so fail-closed means *refuse*, not warn; (c) make the package pass its own G0 and check-package; (d) add one independent anchor to the final semantic re-audit; (e) design merge semantics and apply recovery before any merge feature exists — the "merging" half of the remit is currently unimplemented and unaudited, and only the "moving" half was ever validated.

### The One Thing to Do First

**Make the pre-approval gate re-run loss-check against the live tree and hard-refuse unless the detected-condition set — class IDs and counts — exactly equals what the brief recorded in the journal: approve the state, not the draft.** One gate closes both demonstrated failures: the 5-of-6 drop (a stale recorded set can no longer mask a dropped class) and the 71-vs-72 mutation (verification happens at apply time against live state, not against a hash captured earlier). It subsumes the Contrarian's 1:1 checklist and the Executor's count-stamp in a single mechanical assertion, costs about an afternoon, and converts the weakest link — currently untyped human copy-paste — into a CLI gate that cannot be walked around.