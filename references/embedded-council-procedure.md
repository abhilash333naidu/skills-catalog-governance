# Embedded Council Procedure (MANDATORY fallback — guarantees the council always runs)

> Part of the `skills-catalog-governance` package. `SKILL.md` (Council Per-Group Merge
> Governance, Step 2) points here. Adapted from Karpathy's LLM Council. Five advisors, five
> anonymous reviewers, one chairman.

The council is a non-negotiable quality gate (SKILL.md, Council Per-Group, Step 2). This
procedure keeps it possible in ANY harness, with no external skill dependency: if the harness
lacks `llm-council`, run this inline. The council is never skipped for convenience — this is
the mechanism that makes it always executable. Each advisor independently answers the framed
question; reviewers then critique the five anonymously; the chairman synthesizes the verdict.

**Honesty note on independence:** the 5 advisors + 5 reviewers are usually ONE underlying
model at different persona-prompts — CORRELATED judgments, not an independent-model
ensemble. The point of the council is diverse LENSES on one judgment (catches single-frame
blind spots), not statistical independence. Do NOT claim the council gives "independent
model diversity"; frame it as "multiple perspectives on a correlated base model." Real
model diversity (if ever needed) requires genuinely different providers/models, and the
gateway wedge risk on parallel multi-model calls was a hard constraint this session.

## The five advisors (thinking styles, not personas)

1. **The Contrarian** — actively looks for what's wrong, what's missing, what will fail.
   Assumes the proposal has a fatal flaw and tries to find it.
2. **The First Principles Thinker** — ignores the surface question, asks "what are we
   actually trying to solve here?", strips assumptions, rebuilds from the ground up.
3. **The Expansionist** — looks for the upside everyone else missed; what could be bigger,
   what adjacent opportunity is hiding, what's undervalued.
4. **The Outsider** — has zero context about the project's history; responds purely to what's
   in front of them; catches the curse of knowledge.
5. **The Executor** — only cares whether it can actually be done and the fastest path;
   "what do you do Monday morning?"

**Honesty note (external review):** the five advisors are LENSES on one judgment, not five
independent models — they will share any bias of the underlying model. The council's value
is forcing divergent framings and surfacing blind spots, NOT statistical independence. Do
not overstate it as "five independent opinions"; state it as "five lenses, one model."

## Step 1 — Frame the question

Reframe the group decision as a clear, neutral question: the core decision, the member
skills involved (by dir name), what's at stake, and any binding constraints (e.g. ONE
survivor per group, portability covenant). Do not add your own opinion; do not steer.

## Step 2 — Convene the advisors (independent, ideally parallel)

Give each advisor the framed question plus: "Respond from your perspective. Be direct and
specific. Don't hedge or try to be balanced. Lean fully into your assigned angle. Keep it
150-300 words. No preamble."

## Step 3 — Anonymous peer review

Collect all 5 advisor responses, anonymize them as Response A–E (randomize the mapping),
and for EACH advisor (5 reviewers) ask the same three questions:
1. Which response is the strongest and why? (pick one)
2. Which response has the biggest blind spot and what is it?
3. What did ALL responses miss that the council should consider?
Keep each review under 200 words.

## Step 4 — Chairman synthesis

Give the chairman the original question, all 5 advisor responses (de-anonymized), and all
5 peer reviews. Produce the verdict in this exact structure:
- Where the council agrees (high-confidence signals)
- Where the council clashes (genuine disagreements, both sides, why)
- Blind spots the council caught (only surfaced through peer review)
- The recommendation (a real answer, not "it depends"; chairman may side with the minority)
- The one thing to do first (a single concrete next step)

Save the transcript as `skills-merge-drafts/<group>-council-verdict.md` (or the drafts dir
in use) — it is the artifact the writer consumes and the loss-check checks against.