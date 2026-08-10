# M3 Council Verdict — commit-message skill family

**Date:** 2026-08-10
**Brief:** `docs/council-brief-commit-family-20260810.md`
**Method:** `llm-council` skill (Karpathy LLM Council protocol) — 5 advisors in parallel → 5 anonymous peer reviewers in parallel → 1 chairman synthesis
**Governing standard:** `skills-catalog-governance` v2.1.0-draft — Council Per-Group Merge Governance

> **Honesty note:** advisors and reviewers were of the same correlated base model at different thinking-lens prompts (LENSES, not independent models). Council value = divergent framing + blind-spot surfacing, NOT statistical independence.

---

## Step 1 — Framed question

Three skills in the catalog all handle writing git commit messages, but come from different harness families. **Decision: consolidate into ONE master skill, or keep separate?**

| Skill | Family | Kind |
|---|---|---|
| `caveman-commit` | caveman plugin pack (one of ~10 `caveman-*`) | pure **generator** — terse message, Conventional Commits, <=50 chars, does NOT git commit/stage/amend, outputs paste-ready code block |
| `ce-commit` | Claude Engineer / `ce-*` (one of many) | full **executor** — context gather, convention detect, detached-HEAD prompt, logical commit split, stage, git commit via heredoc, confirm loop; uses `AskUserQuestion`/`request_user_input`/`ask_user` |
| `writing-commit-messages` | vendored in `herdr/vendor/libghostty-vt` | **style system** — subsystem-prefix subjects from file paths (`terminal/osc`), prose bodies, `jj` auto-detection |

**Binding constraints:** at most ONE survivor per group; survivor keeps identity (dir + frontmatter); sources archive only after content absorbed; portability covenant — no `AskUserQuestion`, no `/ce-*`, no `$GSTACK_BIN`, no telemetry; master must work in any harness (Hermes, Claude Code, opencode, codex, OMP).

---

## Step 2 — Advisor statements (150-300 words each)

### 1. The Contrarian
The framing is wrong — you have grouped three skills by the surface keyword "commit message," not by function. These are three distinct task types. Style contract (caveman-commit: terse, <=50 chars). Style contract in the inverse (writing-commit-messages: subsystem prefixes, prose). And an execution workflow (ce-commit: a git operator, not a formatter at all). No single survivor can honor two contradictory style contracts. Either one style wins and the other's users get misformatted output, or you ship a "pick your style" menu — nondeterministic output across harnesses, which is worse for portability than any forbidden primitive.

Strip the interactive context gates from ce-commit to satisfy the portability covenant and you have excised its core value. You are not consolidating; you are amputating. And you are ignoring ownership: writing-commit-messages is vendored inside herdr's vendor tree. Archiving it forks herdr's vendor tree and guarantees exactly the drift you set out to eliminate.

Verdict: **no merge.** Regroup by function. ce-commit belongs in a commit-executors bucket judged against executors, not message stylists.

### 2. The First Principles Thinker
You're asking the wrong question. "Three skills handle commit messages" is surface coincidence, not a functional grouping. Group by primitive, not topic.

The primitive is message generation: transform diff -> message. `caveman-commit` and `writing-commit-messages` are both exactly this, differing only by style knobs (terse/conventional vs subsystem/prose) and one tool-detection branch (jj vs git). Those are the same skill. Merging them into one master with a style parameter is correct — the only defensible merge in the stack.

`ce-commit` is NOT a generator. Its core is execution: context gathering, staging, logical splits, detached-HEAD handling, actually running `git commit`. Message style is incidental plumbing. Force-merging it produces exactly the failure the question fears — a bloated, contradictory master. And blocking prompts aren't an implementation detail; they ARE ce-commit's mechanism. Strip them and you have a hairless twin of a generator you already own.

Verdict: **ONE survivor for the generator group**, absorbing `caveman-commit` + `writing-commit-messages` + ce-commit's convention-detection logic. ce-commit's execution layer belongs to a different group — git operations — not this council's slot. **Recategorize it, don't archive it**; harvest its message logic first.

### 3. The Expansionist
Consolidate. The merger is the whole upside; the split is the status-quo tax.

These three aren't duplicates — they're a three-piece system. `caveman-commit` owns the voice (compression, Conventional Commits, 50-char discipline). `ce-commit` owns the mechanics (diff context, staging, detached-HEAD handling, logical-split). `writing-commit-messages` owns the domain intelligence (subsystem routing, jj detection, prose bodies). No single one is a commit skill. Together they're a commit *platform*.

The unified master unlocks a composition surface: emit a caveman-terse subject for a chore, a subsystem-scoped prose body for a multi-file change, a jj-backed commit when `.jj` exists, an interactive split when HEAD is detached — choosing the mode from the diff itself, not from which harness you're in. That's the adjacent opportunity nobody's pricing: commit-message generation as a decision tree over diff shape.

The portability covenant isn't a constraint — it's the unlock. Stripping `AskUserQuestion` is what makes the master harness-agnostic, which is what a catalog should ship: one skill, every agent, deterministic output. Worst case: bloat — but the archive gate catches that. Best case: this becomes the canonical commit layer for the whole catalog, a reference other skills route to. Bet on the best case. **Merge.**

### 4. The Outsider
Category error. These three do different verbs. `caveman-commit` is a **generator** — output is text, zero side effects. `ce-commit` is an **executor** — output is a staged, committed repo; its detached-HEAD prompting, splitting, and staging are irreconcilable with the portability covenant; strip `AskUserQuestion` and you airlift out the very feature that justifies its existence. `writing-commit-messages` is a **style system** — subsystem prefixes from file paths, `.jj` detection; house rules for a specific toolchain in a specific repo topology.

The overlap exists only in the input domain (git context) — the cheapest thing to share. You don't merge skills to share inputs. Merging produces one artifact with three incompatible output contracts, half of it stripped to pass portability gates, useless to every harness and loved by none. Keeping all three means the *names* collide — that IS the real drift.

So: **no merge.** Rename `writing-commit-messages` to signal what it is (e.g., `subsystem-commit-style`), keep it vendored with its host repo, and add a routing table outside all three: need text -> caveman-commit; need the repo changed -> ce-commit; live in a jj/subsystem repo -> the style guide. A routing table outranks any merger.

### 5. The Executor
Merged. Three-way merge, ce-commit survives.

The three aren't real duplicates. `caveman-commit` = message *generation*. `writing-commit-messages` = a *style* (subsystem prefixes, prose bodies). `ce-commit` = the only *complete executor* (context gathering, staging, staged-commits, verify loop). Two of them are content, not processes — you can't executor-ize a generator without writing the whole pipeline from scratch.

ce-commit is the only viable survivor: it does the full job Monday through Friday. The other two degrade cleanly into it. caveman-commit -> a `terse: true` config profile (subject <=50, Conventional Commits, code-block output — that's a message style, not a skill). writing-commit-messages -> a `style: subsystem` profile, with jj detection as a git-backend flag.

The portability covenant decides the real work: rip out `AskUserQuestion`/`request_user_input`/`ask_user`, replace with a deliberation contract — gather context -> build commit plan -> emit plan as return value -> the harness renders its own blocking question. That's a one-day refactor, not a week.

Failure mode to avoid: keeping all three separate guarantees drift — three authors editing message conventions independently, forever. Hours: 1 day rip-out + absorb, 1 day consistent baseline across six harnesses, half a day archive plumbing. Copy content in, delete old dirs, run the portability gate, **ship**.

---

## Step 3 — Anonymous peer reviews

Responses anonymized A-E (mapping randomized before review, disclosed after):

| Letter | Advisor |
|---|---|
| A | The Expansionist |
| B | The Contrarian |
| C | The Executor |
| D | The Outsider |
| E | The First Principles Thinker |

### Peer review 1
1. **Strongest: E.** Groups by primitive, not shared keyword. Correctly isolates the generator core (caveman-commit + writing-commit-messages) from ce-commit's executor core — and uniquely resolves this *within* the binding one-survivor rule by recategorizing ce-commit instead of settling for "keep all separate" (B, D) or forcing a contradictory master (A, C).
2. **Biggest blind spot: A.** Treats two mutually exclusive style contracts (terse <=50 vs subsystem prose) as a pleasant "composition surface." Never specifies how ONE survivor honors both deterministically — either one style wins or a nondeterministic menu ships, exactly what the covenant forbids.
3. **All missed:** the executors family — ce-commit-push-pr and shipping skills also run git commit; the survivor must stay the plugin point for downstream executors. And nobody actually read the three skill files; debate ran on abstractions.

### Peer review 2
1. **Strongest: E.** Correct primitive taxonomy (generator vs executor); respects one-survivor rule while fixing faulty grouping; action and constraint-honest.
2. **Biggest blind spot: A.** "Portability covenant as unlock" never confronts that blocking questions ARE ce-commit's core — stripping = amputation. And A alone ignores the style-contract contradiction.
3. **All missed:** family coherence + survivor identity — caveman-commit is one of ten `caveman-*` skills, ce-commit one of many `ce-*`; absorbing orphans the suite and breaks sibling discoverability. No migration plan for existing users; no verification gate for absorbed logic.

### Peer review 3
1. **Strongest: E.** Decomposes by primitive, proves the "contradictory style contracts" are parameters not conflicts, honors one-survivor by regrouping, preserves most value via harvest-then-recategorize.
2. **Biggest blind spot: A.** Pure upside thesis; ignores incompatible output contracts, dismisses amputated-ce-commit, never touches the vendored herdr tree; worst case hand-waved as "the archive gate catches that."
3. **All missed:** no golden-output experiment (fixed diffs -> expected formats through the portability gate); no usage data (which harness fires which skill, how often); parent-tree ownership — both plugin trees fork on archive, guaranteeing rebase conflicts on every parent upgrade.

### Peer review 4
1. **Strongest: E.** Resolves the core conflict instead of dodging it; converts style contradiction into a parameter; recategorizes ce-commit rather than amputating or inflating; satisfies both constraints.
2. **Biggest blind spot: A.** Never engages the contradictory output contracts; "archive gate catches bloat" is faith, not mechanism.
3. **All missed:** nobody opened the skills — no proof caveman-commit and writing-commit-messages actually share a diff->message core; no price on discoverability; never verified outcomes against the binding constraints.

### Peer review 5
1. **Strongest: E.** Groups by primitive, quarantines ce-commit as execution, harvests convention-detection; gives the only survivor with a defensible identity.
2. **Biggest blind spot: B.** "Two contradictory style contracts can't share a survivor" is factually wrong — style is a parameter, not identity; a `terse`/`subsystem` knob with a deterministic default dissolves the conflict.
3. **All missed:** verification — "content absorbed" is empirical; nobody proposed golden message pairs replayed per style knob before archiving; and a single merged description must dispatch two divergent intents (emit text vs mutate repo) — the heavier executor behavior wins discoverability.

---

## Step 4 — Chairman synthesis

## Where the Council Agrees

- **The grouping axis is wrong.** Contrarian, First Principles, and Outsider independently arrived at the same point: "writes a commit message" is a surface keyword, not a functional category. Group by primitive, not topic.
- **ce-commit is an executor, not a formatter.** Four advisors independently identified ce-commit's substance as workflow — context gathering, staging, logical splits, running `git commit` — and its blocking prompts as mechanism, not decoration. Stripping them is amputation.
- **Style is a parameter, not identity.** The "two contradictory style contracts" objection collapses: terse <=50 vs subsystem-prefix prose are knobs with deterministic defaults, not irreconcilable souls fighting over one body.
- **The Expansionist's three-way master is the weakest position.** Every reviewer flagged it: incompatible output contracts treated as a "composition surface," no mechanism for honoring both deterministically, amputation dismissed, bloat hand-waved.

## Where the Council Clashes

1. **Do the two generators merge?** E says merge (same diff->message primitive; style param resolves the conflict). B and C say keep separate (contradictory contracts, family coherence, vendored drift). The disagreement is legitimate because *both sides argue from an unverified empirical premise*: nobody confirmed caveman-commit and writing-commit-messages share a real diff->message core. One side asserts it; the other side's "contradiction" is refuted — but the shared-core claim remains untested.

2. **What is ce-commit's fate?** Reject the strip-to-fit-covenant option outright (4 of 5 agree it's amputation). The open question: does ce-commit "recategorize" out of the one-survivor rule, or must it be absorbed? Reasonable dissent exists because the one-survivor constraint reads as binding against all three as a single group — and E's regrouping is either principled or constraint-evasion, depending on your reading.

3. **Does regrouping comply with the constraint?** The Outsider's "routing table outranks any merger" explicitly subsumes the binding constraint to a convenience — evasion of a kind. E and the Executor both find a path *within the letter* of the constraint: one survivor per function group, not one survivor per topic.

## Blind Spots the Council Caught

- **Nobody read the files.** Two reviewers independently caught that the whole debate ran on abstractions — no proof the two generators share a core, no verification against the binding constraints. This is the council's single largest failure, and it determines whether the recommendation can be executed at all.
- **The Expansionist's amputation hand-wave.** Four reviews flagged that "portability covenant = unlock" never confronts that blocking questions are ce-commit's defining feature.
- **Family coherence was invisible to everyone except one reviewer.** caveman-commit is one of ~10 `caveman-*` skills; ce-commit is one of many `ce-*`. Absorbing them orphans their parent suites. The *survivor keeps identity* constraint is exactly the mechanism that mitigates this — caught only late.
- **Vendored-tree ownership drift.** writing-commit-messages lives in herdr's vendor tree; archiving forks the parent. Mitigation exists — absorb content *in*, edit our copy only, leave the vendored tree whole — but nobody proposed it during advisory.
- **No usage data, no migration plan, no verification gate.** Nobody established which harness actually fires which skill, and "content absorbed" (a binding constraint!) went unmeasured.
- **Downstream executors.** ce-commit-push-pr and shipping skills also run git commit; the executor survivor must remain their plugin point. Archiving ce-commit would break the chain.

## The Recommendation

**Consolidate narrowly — two survivors, not one.** Adopt the First Principles resolution; reject both the three-way master and full separation.

Group by primitive, and by primitive there are **two** groups, so the one-survivor constraint produces **two survivors**:

1. **Generator group (diff -> message).** Merge `caveman-commit` + `writing-commit-messages` into ONE survivor, keeping **caveman-commit's identity** (dir + frontmatter) — preserving its parent suite's coherence and the cleanest reading of the identity clause. Absorb writing-commit-messages' content as a `style: subsystem` profile with jj detection as a backend flag, alongside caveman's `terse` voice; a deterministic default (terse) keeps output reproducible across harnesses. Also harvest ce-commit's convention-detection logic into the survivor for shared style inference. Archive our copy of writing-commit-messages **only after** absorption clears the golden-output gate. herdr's vendored tree is left untouched — absorb content in, never edit the parent, so no fork drift.

2. **Executor group (staging, asking, committing).** **`ce-commit` survives untouched.** It is the only complete executor in the catalog and must remain the plugin point for ce-commit-push-pr and the shipping skills. No archive, no absorption, no covenant-violating strip. It handles "repo changed -> commit"; it never competes with the generator.

**Why not the three-way master:** it requires one artifact honoring two contradictory output contracts or defaults to a pick-your-style menu — nondeterministic output across harnesses, the exact thing the covenant exists to prevent — and it demands ce-commit's amputation to be "portable."

**Why not full separation:** it frames reconcilable parameters as irreconcilable wills, and it either mints a routing table that supersedes the binding constraint or quietly forks the vendored tree. Both failure modes are worse than the costs absorption mitigates.

**Conditional, but not a hedge:** if the golden-output experiment falsifies the shared-core premise — if no single style parameter deterministically reproduces both formats — then the inheritance claim dies and we fall back to keeping both generators plus a routing table. That is the constraint's own verification gate doing its job.

## The One Thing to Do First

**Run the golden-output experiment.** Read the three skill files, feed two or three fixed diffs through caveman-commit and writing-commit-messages, capture both outputs, and verify that a single `style` parameter (terse/subsystem, deterministic default) reproduces both byte-for-byte. That result is the archive gate: it converts the council's thesis from assertion to evidence, and it either authorizes absorbing writing-commit-messages into the caveman-commit survivor or kills the merge on the spot.

---

## Final recommendation (printed)

**Two survivors, not one.** By primitive there are two functional groups, so the one-survivor-per-group rule yields two survivors:

1. **Generator group:** merge `caveman-commit` (survivor, identity kept) + `writing-commit-messages` content as a `style: subsystem`/jj profile into one portable message-generator; harvest ce-commit's convention-detection logic; archive the writing-commit-messages copy only after a golden-output absorption test passes (vendored herdr tree left untouched).
2. **Executor group:** `ce-commit` survives untouched — it stays the plugin point for ce-commit-push-pr and shipping skills; no strip, no archive.

**First move:** run the golden-output experiment (fixed diffs -> expected formats per style knob) to verify the two generators share a single deterministic diff->message core before any absorption or archive.