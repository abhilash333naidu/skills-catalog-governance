# INSTALLER SPEC — install subcommand + one-liner scripts (v3.2)

**Date:** 2026-08-10
**Authority:** user-approved recommendation (harness-detecting installer, terminal-native)
**Implementer:** FreeBuff (coding agent)
**Orchestrator:** Coder CEO (verification, gates)

## Goal

Give a new user the standard "detect my harnesses, let me pick one" setup experience
when they clone the repo — without a GUI (this is a skill, not an app; terminal is home).

Three deliverables:
1. `install` subcommand in scripts/catalog_governance.py — the real logic
2. `install.sh` — POSIX one-liner wrapper (curl | bash)
3. `install.ps1` — Windows PowerShell one-liner wrapper

## Part 1 — `install` subcommand (scripts/catalog_governance.py)

`python3 scripts/catalog_governance.py install [--target <name>] [--yes] [--output]`

### Harness detection table (probe in this order, both OSes)

Probe paths relative to HOME (POSIX) and APPDATA/USERPROFILE (Windows).
A harness is DETECTED if any of its candidate skill dirs exists (is_dir).

| Harness | POSIX paths | Windows paths |
|---|---|---|
| opencode | ~/.config/opencode/skills | %USERPROFILE%\.config\opencode\skills |
| pi | ~/.pi/agent/skills | %USERPROFILE%\.pi\agent\skills |
| claude | ~/.claude/skills | %USERPROFILE%\.claude\skills |
| codex | ~/.codex/skills | %USERPROFILE%\.codex\skills |
| omp | ~/.omp/skills | %USERPROFILE%\.omp\skills |
| hermes | ~/.hermes/skills | %APPDATA%\hermes\profiles\*\skills |
| master | ~/.agents/skills | %USERPROFILE%\.agents\skills |
| gstack | ~/.gstack/skills | %USERPROFILE%\.gstack\skills |

### Behaviour

1. Determine the package root: the directory containing this script (scripts/) parent.
2. Detect all harnesses present. If none found: status FAIL with a helpful message
   ("no supported harness detected; create a skills dir or pass --target").
3. If `--target <name>` given: use ONLY that harness; error if its dir doesn't exist.
4. If interactive (no --yes and stdin and stdout are ttys):
   - Print a numbered list: "1) opencode  ~/.config/opencode/skills   [detected]"
   - Also always offer: "N) all" (install into every detected harness) and "N+1) custom path"
   - Prompt "select:" and read one line from stdin.
   - If non-interactive, require `--target` or explicit `--yes`; otherwise fail closed
     instead of selecting every detected harness.
5. Copy the whole package (SKILL.md, references/, schemas/, scripts/, tests/, LICENSE, README.md)
   into `<harness-dir>/skills-catalog-governance/`.
6. Idempotent + safe:
   - If destination dir exists: report "exists" and (unless --yes) ASK before overwriting.
     Never silently overwrite. If --yes and exists: replace after a timestamped backup
     (`.bak-YYYYmmdd-HHMMSS`).
   - Never touch any other file in the harness dir. Never modify harness config.
7. After copy: run check-package against the NEW location; include its output in the report.
8. Report JSON: {status, installed: [{harness, target, existed, overwritten}], check_package: {...}, errors}

## Part 2 — install.sh (POSIX)

```bash
#!/usr/bin/env bash
# One-liner: curl -fsSL <repo>/install.sh | bash
set -euo pipefail
# Clone to a temp dir if not already inside a checkout, detect python, run the install subcommand
```

Rules:
- If run from inside the repo (scripts/ exists next to it), use the local copy.
- Else: clone https://github.com/abhilash333naidu/skills-catalog-governance to a temp dir.
- Pick python3 (fallback python). Run `python3 scripts/catalog_governance.py install`.
- Pass through stdin so the interactive harness picker works: `exec 3<&0` or read from /dev/tty when interactive.
- Print the same numbered list behaviour; exit non-zero on failure with a clear message.

## Part 3 — install.ps1 (Windows PowerShell)

```powershell
# One-liner: irm https://raw.githubusercontent.com/abhilash333naidu/skills-catalog-governance/main/install.ps1 | iex
```

Rules:
- Same behaviour: detect harnesses, list, pick, copy, check-package.
- Clone via git (or download zip via Invoke-WebRequest if git missing).
- Use python (py launcher preferred: `py -3`, fallback `python`).
- Handle the interactive picker with Read-Host.

## Tests (add to tests/test_catalog_governance.py)

- T1: install into a temp harness dir (created manually) with --target → status PASS,
  package present at <dir>/skills-catalog-governance/SKILL.md, check-package PASS.
- T2: install when no harnesses detected → status FAIL, helpful message.
- T3: install with --target to a NON-EXISTENT dir → status FAIL, clear error.
- T4: install without `--target` or `--yes` in non-interactive mode (stdin not a tty) →
  status FAIL, no harness is modified, and the report explains how to opt in explicitly.
  An explicit `--target` remains narrow; explicit `--yes` opts into all detected harnesses.
- T5: install --yes over existing → backup created (timestamped .bak), new copy present.
- T6: detection table — point HOME at a temp dir containing one harness skill dir,
  detect-skills-style probe returns that harness in the list.

## Verification (orchestrator runs, never subagent)

1. `python -m pytest tests/ -x -q` passes (existing 29 + new).
2. Fresh temp-home simulation: run install with --target into a temp dir, confirm
   package + check-package PASS, with literal output.
3. install.sh: run `bash install.sh` from a fresh clone copy in a temp dir with
   HOME redirected to a fake harness layout → shows detection list, installs, PASS.
4. install.ps1: syntax check (`pwsh -NoProfile -Command "& { . ./install.ps1 -WhatIf }"` or
   at minimum parse check via `pwsh -NoProfile -Command "[scriptblock]::Create((Get-Content -Raw ./install.ps1))"`).
5. Literal outputs captured for every step.

## Constraints

- Stdlib-only for catalog_governance.py (no new pip deps).
- install.sh / install.ps1: no external tools beyond git + python.
- Never modify harness config files. Only create the skill folder.
- Never delete user data: overwrite only with --yes AND after a .bak timestamped backup.
- Match existing code style (emit() JSON reports, argparse subcommands, fail() helper).
