# M4 BUILD BRIEF — staged master draft for the commit generator group

**Date:** 2026-08-10
**Authority:** M3 Council Verdict (docs/council-verdict-commit-family-20260810.md) +
M3.5 Golden-Output Experiment (docs/golden-output-experiment-20260810.md) — ABSORPTION AUTHORIZED (6/6)

## Task

Write the staged master SKILL.md draft to:
`skills-merge-drafts/caveman-commit.SKILL.md`

This is the GENERATOR group survivor: caveman-commit (identity kept) + absorbed
writing-commit-messages content + harvested ce-commit convention-detection logic.

## What the master must contain

1. **Survivor identity:** frontmatter `name: caveman-commit` (unchanged), dir stays
   `caveman-commit`, version bumped, `merged-from:` metadata listing source dirs:
   - caveman-commit (survivor)
   - writing-commit-messages (absorbed content; vendored tree left untouched)
   - ce-commit (harvested convention-detection logic only, NOT absorbed as executor)

2. **The style parameter** (the core of the merge — verified by golden-output experiment):
   - `style: terse` (DEFAULT) → Conventional Commits `type(scope): imperative summary`,
     subject ≤50 chars (hard cap 72), body only for non-obvious why, bullets `-`, wrap
     72, `Closes #42`/`Refs #17` trailers, no emoji, no AI attribution
   - `style: subsystem` → `subsystem: summary` prefix derived from diff file paths
     (e.g. terminal, vt, lib, config, font; nested terminal/osc), lowercase start,
     whole subject <60 chars, references on own lines (`#1234`) after blank line,
     long-form prose body (what changed / previous behavior / how it works now)
   - Deterministic default: terse. When style is ambiguous, terse wins.

3. **jj auto-detection** (absorbed from writing-commit-messages): if `.jj` exists,
   use jj instead of git for any diff-gathering commands.

4. **Convention-detection logic** (harvested from ce-commit — adapt, don't copy verbatim;
   strip all AskUserQuestion/request_user_input/ask_user — portability covenant):
   detect the project's existing commit style (capitalization after colon, presence of
   conventional types) before generating, so output matches repo conventions.

5. **Boundary:** output-only. Does NOT run git commit, does NOT stage, does NOT push.
   Emit the message as a paste-ready code block. (This is the generator group's
   contract — ce-commit remains the executor.)

6. **Portability covenant (BINDING):** no AskUserQuestion, no /ce-*, no $GSTACK_BIN,
   no telemetry. Works in any harness (Hermes, Claude Code, opencode, codex, OMP).

## Constraints

- Write ONLY to skills-merge-drafts/caveman-commit.SKILL.md. Never write to the live
  skills root. Never edit the vendored herdr tree.
- Follow G0: name == parent dir name (caveman-commit), description ≤1024 chars, no XML
  angle brackets in frontmatter, body <500 lines.
- Keep the description's first ~57 chars intact from the original caveman-commit
  description (the trigger window), extending additively.
- Standard library of the file: must reproduce BOTH style outputs per the golden-output
  experiment — the master contract from docs/golden-output-experiment-brief-20260810.md
  is the authoritative phrasing to start from; verify it still passes the 6 golden pairs.

## Verification before you call it done

- Re-run the golden-output experiment mentally on D1-D3 with your draft: style=terse
  must produce the GOLD_TERSE outputs, style=subsystem the GOLD_SUBSYS outputs.
- Report: draft file path, line count, frontmatter name, merged-from list, and which
  golden pairs your draft reproduces.
