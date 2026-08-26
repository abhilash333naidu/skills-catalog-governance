#!/usr/bin/env python3
"""Fail-closed drift check: SKILL.md documented CLI commands vs the argparse definition.

Compares the set of subcommands the CLI actually registers (``sub.add_parser(...)`` in
scripts/catalog_governance.py, extracted with ``ast`` so it survives formatting changes)
against the set of commands SKILL.md documents as literal CLI invocations
(``catalog_governance.py <command>`` in inline code spans and fenced blocks).

Fails loudly (non-zero exit + one message per drifted command) if either side lists a
command the other does not. Intended as a CI gate so the natural-language skill spec can
never silently drift from the code that implements it.

Runtime is stdlib-only, matching the rest of the codebase.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path

# Commands that are deliberately NOT documented as literal CLI invocations in SKILL.md.
# Each entry MUST carry a justification. Do not add entries to silence the check without
# an honest reason -- silent gaps are the whole point of this gate.
DOC_EXEMPT_COMMANDS = {
    # v2-lifecycle plumbing acts on a proposal JSON payload, not a skill catalog on disk.
    # It is driven by the lifecycle engine, not by an operator typing the command; SKILL.md
    # describes the v2 lifecycle as a directed pipeline and does not enumerate each message.
    "capture-hermes",
    "intake",
    "inspect-proposal",
    "check-policy",
    "evaluate-proposal",
    "impact-report",
    "decide",
    "activate",
    "verify-active",
    "rollback",
}


def cli_commands(script: Path) -> list[str]:
    """Extract subcommand names registered via ``sub.add_parser("<name>")`` using ast."""
    try:
        tree = ast.parse(script.read_text(encoding="utf-8"))
    except SyntaxError as exc:
        report = {
            "status": "FAIL",
            "reason": "could not parse the CLI module",
            "detail": f"{script}: {exc}",
            "undocumented": [],
            "reported_but_not_implemented": [],
            "skipped_exempt": [],
        }
        print(json.dumps(report, indent=2, sort_keys=True))
        sys.exit(1)
    names: list[str] = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "add_parser"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            names.append(node.args[0].value)
    return sorted(set(names))


def documented_commands(text: str) -> list[str]:
    """Extract commands SKILL.md shows as literal CLI invocations.

    Matches the actual convention used across SKILL.md: the subcommand name is the first
    whitespace-delimited token that immediately follows ``catalog_governance.py`` inside an
    inline code span or fenced block, e.g.::

        python3 scripts/catalog_governance.py check-package --root .
        python scripts/catalog_governance.py detect-groups --inventory ...

    The regex deliberately looks specifically for the ``catalog_governance.py <cmd>``
    adjacency -- that is what makes a mention a *literal CLI invocation* (end-user-typed)
    rather than prose discussion of a workflow step.
    """
    pat = re.compile(r"catalog_governance\.py\s+([a-z][a-z0-9-]*)")
    return sorted({m.group(1) for m in pat.finditer(text)})


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Check SKILL.md/CLI command drift (fail-closed).")
    ap.add_argument("root", nargs="?", default=".", help="repo root containing scripts/ and SKILL.md")
    ap.add_argument("--json", action="store_true", help="emit the report as JSON on stdout")
    ns = ap.parse_args(argv)

    root = Path(ns.root)
    script = root / "scripts" / "catalog_governance.py"
    skill = root / "SKILL.md"
    as_json = ns.json

    if not script.is_file() or not skill.is_file():
        report = {
            "status": "FAIL",
            "reason": f"repo layout not found under {root} (need scripts/catalog_governance.py and SKILL.md)",
            "undocumented": [],
            "reported_but_not_implemented": [],
            "skipped_exempt": [],
        }
        if as_json:
            print(json.dumps(report, indent=2, sort_keys=True))
        else:
            print(report["reason"])
        return 1

    implemented = set(cli_commands(script))
    documented = set(documented_commands(skill.read_text(encoding="utf-8")))
    exempt = DOC_EXEMPT_COMMANDS

    undocumented = sorted(implemented - documented - exempt)   # implemented, not doc-exempted, not documented
    stale = sorted(documented - implemented)                   # in SKILL.md but no such command
    skipped = sorted((implemented - documented) & exempt)       # implemented, undocumented, exempted

    ok = not undocumented and not stale
    report = {
        "status": "PASS" if ok else "FAIL",
        "undocumented": undocumented,
        "reported_but_not_implemented": stale,
        "skipped_exempt": skipped,
    }
    if as_json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        for cmd in undocumented:
            print(
                f"[drift] FAIL: command implemented in scripts/catalog_governance.py but not "
                f"documented in SKILL.md as a CLI invocation: {cmd}"
            )
        for cmd in stale:
            print(
                f"[drift] FAIL: command documented in SKILL.md but not implemented "
                f"(no add_parser): {cmd}"
            )
        for cmd in skipped:
            print(f"[skip] exempt (see DOC_EXEMPT_COMMANDS): {cmd}")
        if ok:
            print(
                f"check-docs-drift: PASS "
                f"({len(undocumented)} undocumented, {len(stale)} stale, {len(skipped)} exempt)"
            )
        else:
            print("check-docs-drift: FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())