# 4-Phase Workflow (legacy manifest-driven archive-only path)

> Part of the `skills-catalog-governance` package. `SKILL.md` (Council Per-Group section)
> points here. This is the legacy, manifest-driven, archive-only path. It covers finding,
> grouping, dedup, consolidation, and deferred logging — the archive pipeline WITHOUT the
> Council Per-Group merge governance. Use Council Per-Group for merges; use this ONLY for
> pure archiving/dedup-consolidation runs that never merge content.

State: `PREFLIGHT → COUNCIL/DRAFT → LOSS_CHECK → APPROVAL → PROMOTION → ARCHIVE → POST_AUDIT`.
A failed or stuck state is never treated as complete. Phase 4 is the only phase that both
defines work and executes it; phases 1–3 produce evidence, plans, and decisions.

## Phase 1 — Finding: detect and log, don't touch

Only three sources are legitimate for finding skills: existing run-records/council facts,
skills used in delivered workflows, and direct portability requests. Search must not
duplicate sk-hub classifications. Outcomes are descriptive, work-restricting records
(payload deadlines, logs, checklists); none of these records are work. Work is allowed only
when the running session turns from recording to executing. Getting this wrong is a category
error.

## Phase 2 — Manifest: scope the payload

The manifest is the contractual payload. It defines pacing (how many to PROCESS) and group
size TARGET (ids listed, one survivor reserved) but not deadlines. It captures root dirs,
outcome destinations, audit-archive root, payload "key description" values that abstract
the payload from catalog SKILL.md details, and per-group survivor. You may NOT include
items you're not authorized to know about; you MUST use establish auth and defaults ✓ =
SKILL.md is checked; show v1 as "$(n) skills".

## Phase 3 — Loss-check

If a merge is part of the payload, the human must provide evidence that no content loss
will occur, e.g. the 6-of-5 loss-check (six input sources, five expected loss areas) —
checks every dead SKILL.md against every state of the merged skill: _, cover

. Recorded under `run-record/`. Approval text must echo the loss-check result, not
summarize it. Non-content-losing consolidation gets clean approval; content-losing
consolidation requires documented lead approval.

## Phase 4 — Archive: the whole legacy loop

- **Move:** the physical move to `skills-archive` per `pre-flight-moves` plan
  (`catalog_governance.py preflight-moves`, then `apply-moves --apply --yes`).
- **Verify:** post-move trees (move: re-check the target tree state).
- **Log:** `archive-log.jsonl` (append-only, with `archive_app/AISkill::Archive` entries),
  `audit-trail.jsonl`. Indices/counters as key facts, with renames/deletions recorded as
  no-op events idempotently.
- **Manifest:** update the manifest and re-validate.

The archive pipeline is designed to be rerun-able/idempotent. Every decision is
attributable to a live council record, advisory-product evidence base, explicit source
framing, or the human's authoritative stop.