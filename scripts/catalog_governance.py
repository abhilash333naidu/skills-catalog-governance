#!/usr/bin/env python3
"""Fail-closed helpers for skills-catalog governance.

This module intentionally uses only the Python standard library.  It never mutates a
catalog during validation or planning.  Moves require an explicit plan produced by
``preflight-moves`` and both ``--apply`` and ``--yes``.
"""
from __future__ import annotations

import argparse
import ast
import errno
import hashlib
import json
import math
import os
import re
import shutil
import stat
import subprocess
import sys
import time
import uuid
from collections import Counter
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MIN_PYTHON = (3, 10)


def require_python_version(minimum: tuple[int, int] = MIN_PYTHON) -> None:
    """Fail-closed prereq guard: structured FAIL (never a raw traceback) on old Python."""
    if sys.version_info < minimum:
        print(json.dumps({
            "status": "FAIL",
            "message": (
                f"Python {minimum[0]}.{minimum[1]} or newer is required "
                f"(found {sys.version_info[0]}.{sys.version_info[1]}.{sys.version_info[2]})"
            ),
        }, indent=2, sort_keys=True))
        sys.exit(1)


require_python_version()

SCHEMA_VERSION = "1"
REF_RE = re.compile(r"`(references/[^`]+)`")
HEADING_RE = re.compile(r"^#{1,6}\s+(.+?)\s*$")
WORD_RE = re.compile(r"[a-z0-9][a-z0-9_.:/-]*")
ABS_WIN_RE = re.compile(r"^[A-Za-z]:[\\/]")
OVERLAP_THRESHOLD = 0.50


def fail(message: str, details: list[str] | None = None) -> int:
    report: dict[str, Any] = {"status": "FAIL", "message": message}
    if details:
        report["details"] = details
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1


def emit(report: dict[str, Any], output: str | None = None) -> int:
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if output:
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        Path(output).write_text(rendered, encoding="utf-8", newline="\n")
    print(rendered, end="")
    return 0 if report.get("status") in {"PASS", "PLANNED", "ESCALATE"} else 1


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def tree_digest(path: Path) -> str:
    """Hash a tree without following symlinks, including relative names and targets."""
    digest = hashlib.sha256()
    if not path.exists() and not path.is_symlink():
        raise FileNotFoundError(path)
    if path.is_symlink():
        digest.update(b"L\0" + os.readlink(path).encode() + b"\0")
        return digest.hexdigest()
    for item in sorted(path.rglob("*"), key=lambda p: p.relative_to(path).as_posix()):
        rel = item.relative_to(path).as_posix().encode()
        if item.is_symlink():
            digest.update(b"L\0" + rel + b"\0" + os.readlink(item).encode() + b"\0")
        elif item.is_file():
            digest.update(b"F\0" + rel + b"\0" + sha256_file(item).encode() + b"\0")
        elif item.is_dir():
            digest.update(b"D\0" + rel + b"\0")
    return digest.hexdigest()


def is_absolute(value: str) -> bool:
    return Path(value).is_absolute() or bool(ABS_WIN_RE.match(value))


def within(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
        return True
    except ValueError:
        return False


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"missing JSON file: {path}")
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {path}: {exc}")


def referenced_files(skill: Path) -> list[str]:
    return sorted(set(REF_RE.findall(skill.read_text(encoding="utf-8"))))


def is_link_or_reparse(path: Path) -> bool:
    """Return true for POSIX symlinks and Windows symlink/junction reparse points."""
    if os.path.islink(path):
        return True
    if os.name == "nt":
        try:
            attributes = path.stat(follow_symlinks=False).st_file_attributes
        except (AttributeError, FileNotFoundError, OSError):
            return False
        return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
    return False


def frontmatter_value(value: str) -> str:
    value = value.strip()
    if not value:
        return ""
    if value[0] in {'\"', "'"}:
        if len(value) < 2 or value[-1] != value[0]:
            raise ValueError("frontmatter string value is not closed")
        try:
            parsed = ast.literal_eval(value)
        except (SyntaxError, ValueError) as exc:
            raise ValueError("frontmatter string value is malformed") from exc
        return parsed if isinstance(parsed, str) else str(parsed)
    return value


def skill_frontmatter(text: str) -> tuple[str | None, str | None]:
    """Read name and description from the simple YAML frontmatter we support."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, None
    end = next((index for index, line in enumerate(lines[1:], 1) if line.strip() == "---"), None)
    if end is None:
        raise ValueError("frontmatter opening delimiter has no closing delimiter")

    values: dict[str, str] = {}
    current_key: str | None = None
    continuation: list[str] = []

    def finish_value() -> None:
        if current_key is None:
            return
        if current_key not in {"name", "description"}:
            return
        value = values.get(current_key, "")
        if continuation:
            marker = value.strip()
            parts = [part.strip() for part in continuation]
            if marker in {">", ">-", ">+"}:
                value = " ".join(parts)
            elif marker in {"|", "|-", "|+"}:
                value = "\n".join(parts)
            else:
                value = " ".join([value.rstrip(), *parts]).strip()
        values[current_key] = value

    for line in lines[1:end]:
        if not line.strip():
            if current_key is not None:
                continuation.append("")
            continue

        if line[0].isspace():
            if current_key is None:
                raise ValueError(f"malformed frontmatter line: {line}")
            continuation.append(line.strip())
            continue

        match = re.match(r"^([A-Za-z_][\w.-]*)\s*:\s*(.*?)\s*$", line)
        if match:
            finish_value()
            current_key = match.group(1)
            continuation = []
            values[current_key] = frontmatter_value(match.group(2))
            continue

        if line.lstrip().startswith("-"):
            if current_key is not None:
                continuation.append(line.strip())
            continue

        raise ValueError(f"malformed frontmatter line: {line}")

    finish_value()
    return values.get("name"), values.get("description")


def council_verdict_frontmatter(text: str) -> dict[str, str | list[str]]:
    """Parse a simple YAML frontmatter block for council verdicts."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    end = next((index for index, line in enumerate(lines[1:], 1) if line.strip() == "---"), None)
    if end is None:
        raise ValueError("frontmatter opening delimiter has no closing delimiter")

    values: dict[str, str | list[str]] = {}
    current_key: str | None = None
    for line in lines[1:end]:
        if not line.strip():
            continue
        match = re.match(r"^([A-Za-z_][\w.-]*)\s*:\s*(.*?)\s*$", line)
        if match:
            current_key = match.group(1)
            if current_key in values:
                raise ValueError(f"duplicate key in frontmatter: {current_key}")
            raw_value = match.group(2).strip()
            # Accept an inline empty list literal (`absorbed: []`) as a true empty
            # list, not the string "[]" the generic scalar parser would produce.
            values[current_key] = [] if raw_value == "[]" else frontmatter_value(raw_value)
            continue
        list_match = re.match(r"^\s+-\s+(.+?)\s*$", line)
        if list_match:
            if current_key is None:
                raise ValueError(f"malformed frontmatter line: {line}")
            if isinstance(values[current_key], list):
                values[current_key].append(frontmatter_value(list_match.group(1)))
            elif isinstance(values[current_key], str) and not values[current_key]:
                values[current_key] = [frontmatter_value(list_match.group(1))]
            else:
                raise ValueError(f"malformed frontmatter line: {line}")
            continue
        raise ValueError(f"malformed frontmatter line: {line}")
    return values


def validate_council_verdict(file: Path) -> dict[str, Any]:
    """Validate the machine-readable frontmatter of a council verdict."""
    resolved_file = str(file.resolve())
    try:
        frontmatter = council_verdict_frontmatter(file.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {
            "status": "FAIL",
            "file": resolved_file,
            "verdict": "",
            "survivors": [],
            "recategorizations": [],
            "absorbed": [],
            "gates_passed": [],
            "errors": [str(exc)],
        }

    errors: list[str] = []
    if not frontmatter:
        errors.append(
            "no frontmatter block; expected a YAML frontmatter block declaring `verdict` "
            "and a non-empty `survivors` list (see schemas/council-verdict.schema.json)"
        )

    verdict = frontmatter.get("verdict", "")
    allowed_verdicts = {"MERGE", "SPLIT", "RECATEGORIZE", "KEEP_SEPARATE", "NO_MERGE"}
    if not isinstance(verdict, str) or not verdict:
        errors.append("missing required key: verdict")
    elif verdict not in allowed_verdicts:
        errors.append(f"invalid verdict value: {verdict}")

    survivors = frontmatter.get("survivors", [])
    if not isinstance(survivors, list) or not survivors or not all(isinstance(item, str) and item for item in survivors):
        errors.append("survivors must be a non-empty list of non-empty strings")

    optional_lists: dict[str, list[str]] = {}
    for key in ("recategorizations", "absorbed", "gates_passed"):
        value = frontmatter.get(key, [])
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            errors.append(f"{key} must be a list of strings")
            optional_lists[key] = []
        else:
            optional_lists[key] = value

    report: dict[str, Any] = {
        "status": "PASS" if not errors else "FAIL",
        "file": resolved_file,
        "verdict": verdict if isinstance(verdict, str) else "",
        "survivors": survivors if isinstance(survivors, list) else [],
        "recategorizations": optional_lists["recategorizations"],
        "absorbed": optional_lists["absorbed"],
        "gates_passed": optional_lists["gates_passed"],
        "errors": errors,
    }
    return report


def hermes_store_paths(home: Path) -> list[Path]:
    return [home / ".hermes" / "skills"]


def default_skill_stores() -> list[tuple[str, Path]]:
    home = Path.home()
    stores: list[tuple[str, Path]] = [("master", home / ".agents" / "skills"), ("pi", home / ".pi" / "agent" / "skills")]
    stores.extend(("hermes", path) for path in hermes_store_paths(home))
    return stores


def iter_skill_files(root: Path) -> Iterable[Path]:
    """Yield SKILL.md files while never descending through linked directories."""
    pending = [root]
    visited: set[str] = set()
    while pending:
        current = pending.pop()
        canonical = os.path.normcase(str(current.resolve(strict=False)))
        if canonical in visited:
            continue
        visited.add(canonical)
        try:
            with os.scandir(current) as directory:
                children = sorted(directory, key=lambda entry: entry.name)
                for child in children:
                    path = Path(child.path)
                    if is_link_or_reparse(path):
                        continue
                    if child.is_dir(follow_symlinks=False):
                        pending.append(path)
                    elif child.name == "SKILL.md" and child.is_file(follow_symlinks=False):
                        yield path
        except OSError as exc:
            raise ValueError(f"cannot scan directory {current}: {exc}") from exc


def scan_skill_store(store: str, root: Path) -> tuple[list[dict[str, Any]], list[str]]:
    inventory: list[tuple[str, dict[str, Any]]] = []
    errors: list[str] = []
    try:
        scan_root = root.resolve(strict=True)
        if not scan_root.is_dir():
            return [], [f"store is not a directory: {root}"]
        candidates = iter_skill_files(scan_root)
        for skill_file in candidates:
            skill_dir = skill_file.parent
            canonical = os.path.normcase(str(skill_dir.resolve(strict=False)))
            try:
                content = skill_file.read_bytes()
                name, description = skill_frontmatter(content.decode("utf-8"))
            except (OSError, UnicodeDecodeError, ValueError) as exc:
                errors.append(f"cannot read or parse {skill_file}: {exc}")
                continue
            entry: dict[str, Any] = {
                "store": store,
                "path": str(skill_dir.resolve()),
                "name": name or skill_dir.name,
                "description": description or "",
                "sha256": sha256_bytes(content),
            }
            if store == "external":
                entry["read_only"] = True
            inventory.append((canonical, entry))
    except (OSError, RuntimeError, ValueError) as exc:
        errors.append(str(exc))
    return [entry for _, entry in inventory], errors


def load_usage_counts(store_root: Path) -> dict[str, int]:
    """Best-effort .usage.json reader (Hermes-style per-skill counts).

    Fail-open: a missing/unreadable usage file yields no counts, not an error.
    Expected shape (any of these tolerated):
      {"skill-name": N}  or  {"skills": {"skill-name": N}}
      {"skill-name": {"use_count": N, ...}}
      {"skills": {"skill-name": {"use_count": N, ...}}}
    """
    usage_path = store_root / ".usage.json"
    try:
        data = json.loads(usage_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    raw = data.get("skills", data)
    if not isinstance(raw, dict):
        return {}
    counts: dict[str, int] = {}
    for key, value in raw.items():
        if isinstance(value, (int, float)):
            counts[str(key)] = int(value)
        elif isinstance(value, dict) and isinstance(value.get("use_count"), (int, float)):
            counts[str(key)] = int(value["use_count"])
    return counts


def cmd_detect_skills(args: argparse.Namespace) -> int:
    if args.stores:
        raw_stores = [item for group in args.stores for item in group]
        stores = [("external", Path(raw).expanduser()) for raw in raw_stores]
    else:
        stores = [(tag, path) for tag, path in default_skill_stores() if path.is_dir()]
    usage: dict[str, int] = {}
    if args.usage_dir:
        usage = load_usage_counts(Path(args.usage_dir).expanduser())
    inventory: list[dict[str, Any]] = []
    errors: list[str] = []
    seen_paths: set[str] = set()
    for store, root in stores:
        entries, store_errors = scan_skill_store(store, root)
        errors.extend(store_errors)
        for entry in entries:
            canonical = os.path.normcase(str(Path(entry["path"]).resolve(strict=False)))
            if canonical not in seen_paths:
                seen_paths.add(canonical)
                if usage and entry["name"] in usage:
                    entry["usage"] = usage[entry["name"]]
                inventory.append(entry)
    inventory.sort(key=lambda entry: (entry["store"], entry["path"]))
    counts: dict[str, int] = {store: 0 for store, _ in stores}
    for entry in inventory:
        counts[entry["store"]] = counts.get(entry["store"], 0) + 1
    report: dict[str, Any] = {
        "status": "PASS" if not errors else "FAIL",
        "counts": counts,
        "total": len(inventory),
        "inventory": inventory,
    }
    if errors:
        report["errors"] = errors
    return emit(report, args.output)


GROUP_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "can", "do", "for",
    "from", "has", "have", "how", "if", "in", "into", "is", "it", "its",
    "may", "more", "of", "on", "or", "our", "that", "the", "their", "this",
    "to", "up", "use", "using", "when", "with", "you", "your",
}
GROUP_TOKEN_RE = re.compile(r"[^\W_]+", re.UNICODE)


def group_tokens(name: str, description: str) -> list[str]:
    """Normalize one skill document into comparable, non-trivial word tokens."""
    normalized = " ".join(f"{name} {description}".split()).lower()
    return [token for token in GROUP_TOKEN_RE.findall(normalized) if len(token) > 1 and token not in GROUP_STOPWORDS]


def load_group_inventory(path: Path) -> list[dict[str, Any]]:
    try:
        payload = load_json(path)
    except ValueError as exc:
        raise ValueError(f"cannot load inventory {path}: {exc}") from exc

    if isinstance(payload, list):
        inventory = payload
    elif isinstance(payload, dict) and isinstance(payload.get("inventory"), list):
        if payload.get("status") != "PASS":
            raise ValueError("inventory report status must be PASS")
        if payload.get("errors"):
            raise ValueError("inventory report contains errors")
        inventory = payload["inventory"]
    else:
        raise ValueError("inventory must be a JSON list or an object with an inventory list")  # noqa: TRY004 - ValueError is the established CLI error contract

    validated: list[dict[str, Any]] = []
    for index, entry in enumerate(inventory):
        if not isinstance(entry, dict):
            raise ValueError(f"inventory[{index}] must be an object")  # noqa: TRY004 - ValueError is the established CLI error contract
        for field in ("name", "path"):
            if not isinstance(entry.get(field), str) or not entry[field].strip():
                raise ValueError(f"inventory[{index}] missing valid {field}")
        description = entry.get("description", "")
        if not isinstance(description, str):
            raise ValueError(f"inventory[{index}].description must be a string")  # noqa: TRY004 - ValueError is the established CLI error contract
        validated.append({"name": entry["name"], "path": entry["path"], "description": description})
    return validated


def group_cosine(left: dict[str, int], right: dict[str, int], idf: dict[str, float]) -> float:
    left_norm = math.sqrt(sum((count * idf[term]) ** 2 for term, count in left.items()))
    right_norm = math.sqrt(sum((count * idf[term]) ** 2 for term, count in right.items()))
    if not left_norm or not right_norm:
        return 0.0
    dot = sum(left[term] * idf[term] * right.get(term, 0) * idf[term] for term in left)
    return dot / (left_norm * right_norm)


def connected_group_names(candidates: list[dict[str, Any]], max_size: int = 8) -> list[list[str]]:
    """Build suggested groups from HIGH-CONFIDENCE pairs only, with a size cap.

    A strong pair must be flagged by BOTH signals (cosine AND word overlap).
    Single-signal pairs — even high-cosine ones — share vocabulary but not a
    functional core (e.g. caveman-commit vs ce-commit both mention commit/git
    at cosine 0.68 yet are generator vs executor, a council-decided split).
    Weak pairs stay candidates but never bridge groups, so transitivity cannot
    chain unrelated families into a mega-group (observed: 24-member component
    chaining ce-*/design-*/ios-*/qa before this fix).

    Groups over max_size are still returned but flagged for manual review (the
    council cannot be asked to read N unrelated skills); callers mark them
    oversized and do not treat them as clean merge groups.
    """
    # Both signals must agree: cosine above threshold AND word overlap >= 0.50.
    strong = [p for p in candidates if len(p.get("flagged_by", [])) >= 2]
    parent: dict[str, str] = {}

    def find(name: str) -> str:
        parent.setdefault(name, name)
        while parent[name] != name:
            parent[name] = parent[parent[name]]
            name = parent[name]
        return name

    def union(left: str, right: str) -> None:
        left_root, right_root = find(left), find(right)
        if left_root != right_root:
            parent[right_root] = left_root

    for pair in strong:
        union(pair["a"], pair["b"])

    # Isolated skills (never part of a strong pair) are NOT groups.
    member_names = {p["a"] for p in strong} | {p["b"] for p in strong}
    components: dict[str, list[str]] = {}
    for name in member_names:
        components.setdefault(find(name), []).append(name)
    return sorted((sorted(names) for names in components.values()), key=lambda names: names[0])


def cmd_detect_groups(args: argparse.Namespace) -> int:
    if not math.isfinite(args.threshold) or not 0 <= args.threshold <= 1:
        return fail("threshold must be a finite number between 0 and 1")
    if not math.isfinite(args.overlap_threshold) or not 0 <= args.overlap_threshold <= 1:
        return fail("overlap-threshold must be a finite number between 0 and 1")
    try:
        inventory = load_group_inventory(Path(args.inventory))
    except (OSError, ValueError) as exc:
        return fail(str(exc))

    documents = [group_tokens(entry["name"], entry["description"]) for entry in inventory]
    term_frequencies = [Counter(tokens) for tokens in documents]
    document_frequency: Counter[str] = Counter()
    for frequencies in term_frequencies:
        document_frequency.update(frequencies.keys())
    document_count = len(documents)
    idf = {
        term: math.log((document_count + 1) / (frequency + 1)) + 1
        for term, frequency in document_frequency.items()
    }

    candidates: list[dict[str, Any]] = []
    for left_index in range(document_count):
        for right_index in range(left_index + 1, document_count):
            cosine = group_cosine(term_frequencies[left_index], term_frequencies[right_index], idf)
            left_words, right_words = set(documents[left_index]), set(documents[right_index])
            overlap = len(left_words & right_words) / min(len(left_words), len(right_words)) if left_words and right_words else 0.0
            flagged_by: list[str] = []
            if cosine >= args.threshold:
                flagged_by.append("cosine")
            if overlap >= args.overlap_threshold:
                flagged_by.append("overlap")
            if not flagged_by:
                continue
            left, right = inventory[left_index], inventory[right_index]
            candidates.append({
                "a": left["name"],
                "b": right["name"],
                "path_a": left["path"],
                "path_b": right["path"],
                "cosine": round(cosine, 6),
                "word_overlap": round(overlap, 6),
                "flagged_by": flagged_by,
            })

    suggested = connected_group_names(candidates, args.max_group_size)
    oversized = [names for names in suggested if len(names) > args.max_group_size]
    report = {
        "status": "PASS",
        "counts": {
            "skills": document_count,
            "pairs": document_count * (document_count - 1) // 2,
            "candidates": len(candidates),
            "groups": len(suggested),
        },
        "threshold": args.threshold,
        "overlap_threshold": args.overlap_threshold,
        "max_group_size": args.max_group_size,
        "candidates": candidates,
        "suggested_groups": suggested,
        "oversized_groups": oversized,
    }
    return emit(report, args.output)


def package_report(root: Path) -> dict[str, Any]:
    root = root.resolve()
    skill = root / "SKILL.md"
    if not skill.is_file():
        return {
            "status": "FAIL",
            "root": str(root),
            "required_files": [],
            "missing_files": ["SKILL.md"],
            "message": "package is missing SKILL.md",
        }
    references = referenced_files(skill)
    required_payload = [
        "scripts/catalog_governance.py",
        "schemas/manifest.schema.json",
        "schemas/loss-check.schema.json",
        "schemas/approval.schema.json",
        "schemas/provenance.schema.json",
        "schemas/council-verdict.schema.json",
        "schemas/golden.schema.json",
        "schemas/benchmark.schema.json",
        "schemas/proposal.schema.json",
        "schemas/policy.schema.json",
        "schemas/decision.schema.json",
        "schemas/lifecycle.schema.json",
        "schemas/active-record.schema.json",
        "schemas/hermes-capture.schema.json",
        "schemas/hermes-receipt.schema.json",
    ]
    required_files = sorted(set(references + required_payload))
    missing = [relative for relative in required_files if not (root / relative).is_file()]
    # Content check beyond presence: bundled JSON schemas must actually parse.
    # Presence-only checking let a byte-corrupted schema report PASS (acceptance F3).
    invalid = []
    for relative in required_payload:
        candidate = root / relative
        if relative.startswith("schemas/") and candidate.is_file():
            try:
                json.loads(candidate.read_text(encoding="utf-8"))
            except ValueError:
                invalid.append(relative)
    clean = not missing and not invalid
    return {
        "status": "PASS" if clean else "FAIL",
        "root": str(root),
        "skill_sha256": sha256_file(skill),
        "required_files": required_files,
        "missing_files": missing,
        "invalid_files": invalid,
        "message": (
            "all required package files are present and valid"
            if clean
            else ("required package files are missing" if missing else "required schema files are not valid JSON")
        ),
    }


def cmd_check_package(args: argparse.Namespace) -> int:
    return emit(package_report(Path(args.root)), args.output)


INSTALL_HARNESSES = (
    "opencode",
    "pi",
    "claude",
    "codex",
    "omp",
    "hermes",
    "master",
    "gstack",
)
INSTALL_DIRS = ("references", "schemas", "scripts", "tests")
INSTALL_FILES = ("SKILL.md", "LICENSE", "README.md")


def install_user_home() -> Path:
    """Resolve the user root for harness detection.

    Order: HOME (explicit override — enables isolated tests and portable installs)
    -> USERPROFILE (Windows) -> Path.home() fallback.
    On POSIX Path.home() already honours HOME, but making the override explicit
    keeps Windows behaviour identical so detection is testable on every OS.
    """
    raw = os.environ.get("HOME") or os.environ.get("USERPROFILE")
    if raw:
        return Path(raw)
    return Path.home()


def install_harness_candidates() -> list[tuple[str, Path]]:
    """Return supported harness skill stores in the specification's order."""
    user_root = install_user_home()
    if os.name == "nt":
        appdata = os.environ.get("APPDATA")
        candidates: dict[str, list[Path]] = {
            "opencode": [user_root / ".config" / "opencode" / "skills"],
            "pi": [user_root / ".pi" / "agent" / "skills"],
            "claude": [user_root / ".claude" / "skills"],
            "codex": [user_root / ".codex" / "skills"],
            "omp": [user_root / ".omp" / "skills"],
            "hermes": [],
            "master": [user_root / ".agents" / "skills"],
            "gstack": [user_root / ".gstack" / "skills"],
        }
        if appdata:
            candidates["hermes"] = sorted((Path(appdata) / "hermes" / "profiles").glob("*") )
            candidates["hermes"] = [path / "skills" for path in candidates["hermes"]]
    else:
        home = user_root
        candidates = {
            "opencode": [home / ".config" / "opencode" / "skills"],
            "pi": [home / ".pi" / "agent" / "skills"],
            "claude": [home / ".claude" / "skills"],
            "codex": [home / ".codex" / "skills"],
            "omp": [home / ".omp" / "skills"],
            "hermes": [home / ".hermes" / "skills"],
            "master": [home / ".agents" / "skills"],
            "gstack": [home / ".gstack" / "skills"],
        }
    return [
        (harness, path)
        for harness in INSTALL_HARNESSES
        for path in candidates[harness]
        if path.is_dir()
    ]


def install_target_candidates(raw_target: str) -> list[tuple[str, Path]]:
    detected = install_harness_candidates()
    if raw_target in INSTALL_HARNESSES:
        matches = [(harness, path) for harness, path in detected if harness == raw_target]
        if not matches:
            raise ValueError(f"target harness directory does not exist: {raw_target}")
        return matches
    target = Path(raw_target).expanduser()
    if not target.is_dir():
        raise ValueError(f"target directory does not exist: {target}")
    return [("custom", target)]


def choose_install_targets(detected: list[tuple[str, Path]]) -> list[tuple[str, Path]] | None:
    """Prompt on a real terminal; return None for an invalid/cancelled choice."""
    all_number = len(detected) + 1
    custom_number = all_number + 1
    print("Detected supported harnesses:", file=sys.stderr)
    for index, (harness, target) in enumerate(detected, 1):
        print(f"{index}) {harness}  {target}   [detected]", file=sys.stderr)
    print(f"{all_number}) all", file=sys.stderr)
    print(f"{custom_number}) custom path", file=sys.stderr)
    print("select: ", end="", file=sys.stderr, flush=True)
    try:
        selection = sys.stdin.readline().strip().lower()
    except (EOFError, KeyboardInterrupt):
        return None
    if selection == str(all_number) or selection == "all":
        return detected
    if selection == str(custom_number) or selection == "custom":
        print("custom skills directory: ", end="", file=sys.stderr, flush=True)
        try:
            custom = sys.stdin.readline().strip()
        except (EOFError, KeyboardInterrupt):
            return None
        if not custom:
            return None
        try:
            return install_target_candidates(custom)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return None
    try:
        selected = int(selection)
    except ValueError:
        return None
    if 1 <= selected <= len(detected):
        return [detected[selected - 1]]
    return None


def install_package(source_root: Path, target_root: Path) -> None:
    """Copy into a sibling staging directory, then publish it atomically."""
    destination = target_root / "skills-catalog-governance"
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(destination)
    target_root.mkdir(parents=True, exist_ok=True)
    staging = target_root / f".{destination.name}.tmp-{uuid.uuid4().hex}"
    try:
        staging.mkdir()
        for directory in INSTALL_DIRS:
            shutil.copytree(source_root / directory, staging / directory, symlinks=True)
        for filename in INSTALL_FILES:
            shutil.copy2(source_root / filename, staging / filename)
        staging.rename(destination)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def backup_destination(destination: Path) -> Path:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup = destination.with_name(f"{destination.name}.bak-{stamp}")
    suffix = 1
    while backup.exists() or backup.is_symlink():
        backup = destination.with_name(f"{destination.name}.bak-{stamp}-{suffix}")
        suffix += 1
    shutil.move(str(destination), str(backup))
    return backup


def cmd_install(args: argparse.Namespace) -> int:
    source_root = Path(__file__).resolve().parent.parent
    errors: list[str] = []
    installed: list[dict[str, Any]] = []
    checks: list[dict[str, Any]] = []

    try:
        if args.target:
            targets = install_target_candidates(args.target)
        else:
            detected = install_harness_candidates()
            if not detected:
                return emit({
                    "status": "FAIL",
                    "installed": [],
                    "check_package": {},
                    "errors": ["no supported harness detected; create a skills dir or pass --target"],
                }, args.output)
            if not args.yes and sys.stdin.isatty() and sys.stdout.isatty():
                targets = choose_install_targets(detected)
                if targets is None:
                    return emit({
                        "status": "FAIL",
                        "installed": [],
                        "check_package": {},
                        "errors": ["invalid or cancelled harness selection"],
                    }, args.output)
            elif not args.yes:
                return emit({
                    "status": "FAIL",
                    "installed": [],
                    "check_package": {},
                    "errors": [
                        "non-interactive install requires --target or --yes; refusing to install into all detected harnesses"
                    ],
                }, args.output)
            else:
                targets = detected
    except (OSError, ValueError) as exc:
        return emit({"status": "FAIL", "installed": [], "check_package": {}, "errors": [str(exc)]}, args.output)

    for harness, target_root in targets:
        destination = target_root / "skills-catalog-governance"
        existed = destination.exists() or destination.is_symlink()
        overwritten = False
        if existed:
            if not args.yes:
                confirmed = False
                if sys.stdin.isatty() and sys.stdout.isatty():
                    print(f"{destination} exists; overwrite? [y/N] ", end="", file=sys.stderr, flush=True)
                    try:
                        confirmed = sys.stdin.readline().strip().lower() in {"y", "yes"}
                    except (EOFError, KeyboardInterrupt):
                        confirmed = False
                if not confirmed:
                    installed.append({"harness": harness, "target": str(target_root), "existed": True, "overwritten": False})
                    errors.append(f"destination exists; rerun with --yes to replace: {destination}")
                    continue
            try:
                backup_destination(destination)
                overwritten = True
            except OSError as exc:
                installed.append({"harness": harness, "target": str(target_root), "existed": True, "overwritten": False})
                errors.append(f"could not back up existing destination {destination}: {exc}")
                continue
        try:
            install_package(source_root, target_root)
            check = package_report(destination)
            checks.append(check)
            installed.append({"harness": harness, "target": str(target_root), "existed": existed, "overwritten": overwritten})
            if check["status"] != "PASS":
                errors.append(f"check-package failed for {destination}: {check.get('message', 'package is incomplete')}")
        except (OSError, ValueError, shutil.Error) as exc:
            installed.append({"harness": harness, "target": str(target_root), "existed": existed, "overwritten": overwritten})
            errors.append(f"installation failed for {destination}: {exc}")

    if len(checks) == 1:
        check_package: dict[str, Any] = checks[0]
    else:
        check_package = {
            "status": "PASS" if checks and all(check["status"] == "PASS" for check in checks) else "FAIL",
            "results": checks,
        }
    report = {
        "status": "PASS" if installed and not errors and check_package.get("status") == "PASS" else "FAIL",
        "installed": installed,
        "check_package": check_package,
        "errors": errors,
    }
    return emit(report, args.output)


def path_from_manifest(value: str, root: Path) -> Path:
    if is_absolute(value):
        return Path(value)
    return root / value


def collect_manifest_paths(manifest: dict[str, Any], root: Path) -> tuple[list[tuple[str, Path]], list[str]]:
    entries: list[tuple[str, Path]] = []
    errors: list[str] = []
    archive = manifest.get("archive", {})
    if not isinstance(archive, dict):
        errors.append("manifest.archive must be an object mapping names to absolute paths")
    else:
        for name, value in sorted(archive.items()):
            if not isinstance(value, str):
                errors.append(f"archive[{name}] must be a path string")
                continue
            if not is_absolute(value):
                errors.append(f"archive[{name}] must use an absolute PATH VALUE: {value}")
            entries.append((f"archive:{name}", path_from_manifest(value, root)))
    for field in ("merge_sources", "nested_duplicates"):
        values = manifest.get(field, [])
        if not isinstance(values, list):
            errors.append(f"manifest.{field} must be an array")
            continue
        for index, value in enumerate(values):
            if not isinstance(value, str):
                errors.append(f"{field}[{index}] must be a path string")
                continue
            entries.append((f"{field}:{index}", path_from_manifest(value, root)))
    return entries, errors


def cmd_validate_manifest(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    try:
        manifest = load_json(Path(args.manifest))
    except ValueError as exc:
        return fail(str(exc))
    errors: list[str] = []
    if not isinstance(manifest, dict):
        errors.append("manifest root must be an object")
        manifest = {}
    required = {"archive", "merge", "merge_survivors"}
    errors.extend(f"missing required key: {key}" for key in sorted(required - manifest.keys()))
    entries, entry_errors = collect_manifest_paths(manifest, root)
    errors.extend(entry_errors)
    seen: dict[str, str] = {}
    for label, path in entries:
        key = os.path.normcase(str(path.resolve(strict=False)))
        if key in seen:
            errors.append(f"duplicate path in {label} and {seen[key]}: {path}")
        seen[key] = label
        if not within(path, root):
            errors.append(f"path escapes catalog root: {label}: {path}")
    survivors = manifest.get("merge_survivors", [])
    if not isinstance(survivors, list):
        errors.append("manifest.merge_survivors must be an array")
    protected = manifest.get("protected", manifest.get("keep", []))
    if not isinstance(protected, list):
        errors.append("manifest.protected/keep must be an array when present")
    report = {
        "status": "PASS" if not errors else "FAIL",
        "manifest": str(Path(args.manifest).resolve()),
        "manifest_sha256": sha256_file(Path(args.manifest)),
        "entry_count": len(entries),
        "errors": errors,
    }
    return emit(report, args.output)


def build_move_entries(manifest: dict[str, Any], root: Path, archive: Path) -> list[dict[str, str]]:
    entries, errors = collect_manifest_paths(manifest, root)
    if errors:
        raise ValueError("; ".join(errors))
    result: list[dict[str, str]] = []
    root_resolved = root.resolve(strict=False)
    for label, source in entries:
        source_resolved = source.resolve(strict=False)
        relative = source_resolved.relative_to(root_resolved)
        result.append({"label": label, "source": str(source_resolved), "destination": str(archive.resolve(strict=False) / relative)})
    return result


def validate_move_entries(entries: Iterable[dict[str, str]], root: Path, archive: Path, *, compute_hashes: bool = True) -> tuple[list[dict[str, Any]], list[str]]:
    entries = list(entries)
    plans: list[dict[str, Any]] = []
    errors: list[str] = []
    root_resolved = root.resolve(strict=False)
    archive_resolved = archive.resolve(strict=False)
    if root_resolved == archive_resolved:
        errors.append("archive root must not equal catalog root")
    else:
        try:
            archive_resolved.relative_to(root_resolved)
            errors.append(f"archive root must be a sibling, not inside catalog root: {archive}")
        except ValueError:
            try:
                root_resolved.relative_to(archive_resolved)
                errors.append(f"catalog root must not be inside archive root: {root}")
            except ValueError:
                pass
    if archive.is_symlink():
        errors.append(f"archive root is a symlink/junction; refusing: {archive}")
    seen_sources: set[str] = set()
    seen_destinations: set[str] = set()
    canonical_sources = [(entry, Path(entry["source"]).resolve(strict=False)) for entry in entries]
    for entry, source_resolved in canonical_sources:
        if source_resolved == root_resolved:
            errors.append(f"source must not be the catalog root: {entry['source']}")
        if source_resolved == archive_resolved or within(source_resolved, archive_resolved) or within(archive_resolved, source_resolved):
            errors.append(f"source overlaps archive root: {entry['source']}")
        for other_entry, other_resolved in canonical_sources:
            if entry is other_entry:
                continue
            if source_resolved != other_resolved and (within(source_resolved, other_resolved) or within(other_resolved, source_resolved)):
                errors.append(f"source entries overlap: {entry['source']} and {other_entry['source']}")
    for entry in entries:
        source = Path(entry["source"])
        destination = Path(entry["destination"])
        source_key = os.path.normcase(str(source.resolve(strict=False)))
        destination_key = os.path.normcase(str(destination.resolve(strict=False)))
        if source_key in seen_sources:
            errors.append(f"duplicate source: {source}")
        if destination_key in seen_destinations:
            errors.append(f"duplicate destination: {destination}")
        seen_sources.add(source_key)
        seen_destinations.add(destination_key)
        if not within(source, root):
            errors.append(f"source escapes root: {source}")
        if not within(destination, archive):
            errors.append(f"destination escapes archive root: {destination}")
        if source.is_symlink():
            errors.append(f"source is a symlink/junction; refusing: {source}")
        if not source.is_dir():
            errors.append(f"source directory missing: {source}")
        elif not (source / "SKILL.md").is_file():
            errors.append(f"source has no SKILL.md: {source}")
        if destination.exists() or destination.is_symlink():
            errors.append(f"destination already exists: {destination}")
        for parent in [destination.parent, *destination.parent.parents]:
            if parent == archive:
                break
            if parent.is_symlink():
                errors.append(f"destination parent is a symlink/junction; refusing: {parent}")
                break
        if source.exists() and source.is_dir():
            plan_entry: dict[str, Any] = dict(entry)
            if compute_hashes:
                try:
                    plan_entry["source_tree_sha256"] = tree_digest(source)
                except OSError as exc:
                    errors.append(f"cannot hash source {source}: {exc}")
                    plan_entry["source_tree_sha256"] = ""
            plans.append(plan_entry)
    return plans, errors


def cmd_preflight_moves(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    archive = Path(args.archive).resolve()
    manifest_path = Path(args.manifest).resolve()
    try:
        manifest = load_json(manifest_path)
        entries = build_move_entries(manifest, root, archive)
    except (ValueError, OSError) as exc:
        return fail(f"move preflight failed: {exc}")
    plans, errors = validate_move_entries(entries, root, archive)
    if errors:
        return fail("move preflight failed; no mutation occurred", errors)
    plan = {
        "schema": "skills-catalog-move-plan-1",
        "status": "PLANNED",
        "plan_id": str(uuid.uuid4()),
        "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "root": str(root),
        "archive": str(archive),
        "manifest": str(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "entries": plans,
        "apply_requires": ["--apply", "--yes", "same manifest hash", "same source and destination state"],
    }
    return emit(plan, args.plan)


def create_move_lock(lock: Path, token: str) -> None:
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(token + "\n")


def process_is_alive(pid: int) -> bool:
    """Return false only when the OS proves that a process does not exist."""
    if pid <= 0:
        return False
    if os.name == "nt":
        # os.kill(pid, 0) is not a reliable existence probe on Windows.
        import ctypes
        import ctypes.wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.argtypes = [ctypes.wintypes.DWORD, ctypes.wintypes.BOOL, ctypes.wintypes.DWORD]
        kernel32.OpenProcess.restype = ctypes.wintypes.HANDLE
        kernel32.CloseHandle.argtypes = [ctypes.wintypes.HANDLE]
        kernel32.CloseHandle.restype = ctypes.wintypes.BOOL
        handle = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if handle:
            kernel32.CloseHandle(handle)
            return True
        # ERROR_INVALID_PARAMETER (87) means the PID does not exist; other
        # failures are treated as alive so recovery remains fail-closed.
        return ctypes.get_last_error() != 87
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError as exc:
        return exc.errno not in {errno.ESRCH, errno.ENOENT}
    return True


def recover_stale_lock(lock: Path) -> bool:
    """Remove a lock only when its recorded PID is provably no longer alive."""
    content = lock.read_text(encoding="utf-8").strip()
    try:
        pid_text, _ = content.split(":", 1)
        pid = int(pid_text)
    except (ValueError, TypeError):
        return False
    if process_is_alive(pid):
        return False
    lock.unlink()
    return True


def move_tree(source: Path, destination: Path, expected_digest: str) -> None:
    """Move atomically on one device, or verify a staged copy across devices."""
    try:
        os.rename(source, destination)
        return
    except OSError as exc:
        if exc.errno != errno.EXDEV:
            raise

    staging = destination.with_name(f".{destination.name}.tmp-{uuid.uuid4().hex}")
    try:
        shutil.copytree(source, staging, symlinks=True)
        if tree_digest(source) != expected_digest:
            raise RuntimeError(f"source changed during cross-device copy: {source}")
        if tree_digest(staging) != expected_digest:
            raise RuntimeError(f"cross-device copy hash mismatch: {staging}")
        staging.rename(destination)
        shutil.rmtree(source)
    except Exception:
        if staging.exists() or staging.is_symlink():
            shutil.rmtree(staging, ignore_errors=True)
        raise


def cmd_apply_moves(args: argparse.Namespace) -> int:
    if not args.apply or not args.yes:
        return fail("refusing to move: require both --apply and --yes")
    try:
        plan = load_json(Path(args.plan))
    except ValueError as exc:
        return fail(str(exc))
    if not isinstance(plan, dict) or plan.get("status") != "PLANNED":
        return fail("invalid or already-consumed move plan")
    root = Path(plan["root"]).resolve()
    archive = Path(plan["archive"]).resolve()
    manifest = Path(plan["manifest"]).resolve()
    if not manifest.is_file() or sha256_file(manifest) != plan.get("manifest_sha256"):
        return fail("manifest changed since preflight; refusing to move")
    # Structural validation must not replace the preflight hashes. The apply phase
    # compares fresh hashes against the exact values recorded in the approved plan.
    entries, errors = validate_move_entries(plan.get("entries", []), root, archive, compute_hashes=False)
    if errors:
        return fail("move state changed since preflight; refusing to move", errors)
    lock = root.parent / f".{root.name}.catalog-governance.lock"
    token = f"{os.getpid()}:{uuid.uuid4()}"
    try:
        create_move_lock(lock, token)
    except FileExistsError:
        if not args.recover_stale_lock:
            return fail(
                f"governance lock already exists: {lock}; inspect it and retry with --recover-stale-lock if its owner is dead"
            )
        try:
            recovered = recover_stale_lock(lock)
        except OSError as exc:
            return fail(f"cannot inspect governance lock {lock}: {exc}")
        if not recovered:
            return fail(f"governance lock is active or cannot be proven stale: {lock}")
        try:
            create_move_lock(lock, token)
        except FileExistsError:
            return fail(f"governance lock changed while recovering; refusing to move: {lock}")
    journal_path = Path(args.journal) if args.journal else Path(str(args.plan) + ".journal.jsonl")
    moved: list[dict[str, Any]] = []
    try:
        for entry in entries:
            source = Path(entry["source"])
            destination = Path(entry["destination"])
            current_digest = tree_digest(source)
            if current_digest != entry.get("source_tree_sha256"):
                raise RuntimeError(f"source changed after preflight: {source}")
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.exists() or destination.is_symlink():
                raise RuntimeError(f"destination appeared after preflight: {destination}")
            move_tree(source, destination, current_digest)
            destination_digest = tree_digest(destination)
            if destination_digest != current_digest:
                raise RuntimeError(f"post-move hash mismatch: {destination}")
            record = {"label": entry["label"], "source": str(source), "destination": str(destination), "sha256": destination_digest, "status": "MOVED"}
            with journal_path.open("a", encoding="utf-8") as journal:
                journal.write(json.dumps(record, sort_keys=True) + "\n")
            moved.append(record)
    except Exception as exc:  # noqa: BLE001 - intentional rollback safety net for move loop
        return fail(f"move stopped after {len(moved)} successful move(s): {exc}", [f"journal: {journal_path}"])
    finally:
        try:
            if lock.read_text(encoding="utf-8").strip() == token:
                lock.unlink()
        except OSError:
            pass
    report = {"status": "PASS", "message": "all planned moves completed", "plan_id": plan["plan_id"], "journal": str(journal_path), "moved": moved}
    return emit(report)


def normalized_words(text: str) -> set[str]:
    return {word for word in WORD_RE.findall(text.lower()) if len(word) > 2}


def headings(text: str) -> set[str]:
    return {re.sub(r"\s+", " ", match.group(1).strip().lower()) for line in text.splitlines() if (match := HEADING_RE.match(line))}


def fenced_commands(text: str) -> set[str]:
    commands: set[str] = set()
    fenced = False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            fenced = not fenced
            continue
        if fenced and re.match(r"\s*(?:[$>#]|python\s|find\s|git\s|test\s|sha256|python3\s)", line, re.IGNORECASE):
            cleaned = re.sub(r"^\s*[$>#]\s*", "", line).strip()
            if cleaned:
                commands.add(cleaned)
    return commands


def one_loss_check(source_path: Path, draft: str, draft_sha256: str, min_overlap: float) -> dict[str, Any]:
    """Compute the mechanical loss-check for a single source against a draft."""
    try:
        source = source_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"cannot read source {source_path}: {exc}")
    source_words = normalized_words(source)
    overlap = len(source_words & normalized_words(draft)) / max(1, len(source_words))
    missing_headings = sorted(headings(source) - headings(draft))
    missing_commands = sorted(fenced_commands(source) - fenced_commands(draft))
    status = "PASS" if not missing_headings and not missing_commands and overlap >= min_overlap else "REVIEW"
    return {
        "source": str(source_path.resolve()),
        "source_sha256": sha256_bytes(source.encode("utf-8")),
        "draft_sha256": draft_sha256,
        "word_overlap": round(overlap, 4),
        "minimum_overlap": min_overlap,
        "missing_headings": missing_headings,
        "missing_commands": missing_commands,
        "status": status,
    }


def cmd_loss_check(args: argparse.Namespace) -> int:
    draft_path = Path(args.draft)
    try:
        draft = draft_path.read_text(encoding="utf-8")
    except OSError as exc:
        return fail(str(exc))
    draft_sha = sha256_file(draft_path)
    checks: list[dict[str, Any]] = []
    for raw_source in args.source:
        try:
            checks.append(one_loss_check(Path(raw_source), draft, draft_sha, args.min_overlap))
        except ValueError as exc:
            return fail(str(exc))
    overall = "PASS" if checks and all(item["status"] == "PASS" for item in checks) else "REVIEW"
    report = {"schema": "skills-catalog-loss-check-1", "status": overall, "draft": str(draft_path.resolve()), "checks": checks, "manual_review_required": True}
    return emit(report, args.output)


def cmd_verify_approval(args: argparse.Namespace) -> int:
    draft = Path(args.draft).resolve()
    approval_path = Path(args.approval)
    try:
        approval = load_json(approval_path)
    except ValueError as exc:
        return fail(str(exc))
    errors: list[str] = []
    if not isinstance(approval, dict):
        errors.append("approval must be an object")
        approval = {}
    if approval.get("decision") != "APPROVE":
        errors.append("decision must be APPROVE")
    if approval.get("draft") not in {str(draft), str(Path(args.draft))}:
        errors.append("approval draft path does not match target draft")
    if approval.get("draft_sha256") != sha256_file(draft):
        errors.append("approval hash does not match current draft")
    if not isinstance(approval.get("approval_text"), str) or not approval["approval_text"].strip():
        errors.append("approval_text must be a non-empty written approval")
    if not isinstance(approval.get("reviewed_by"), str) or not approval["reviewed_by"].strip():
        errors.append("reviewed_by must be present")
    approved_at = approval.get("approved_at_utc")
    if not isinstance(approved_at, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", approved_at):
        errors.append("approved_at_utc must be an ISO-8601 UTC timestamp ending in Z")
    reverified: list[dict[str, Any]] = []
    if args.loss_report is not None:
        try:
            report = load_json(Path(args.loss_report))
        except ValueError as exc:
            return fail(str(exc))
        if not isinstance(report, dict):
            report = {}
        checks = report.get("checks")
        if not isinstance(checks, list) or not checks:
            errors.append("loss-report.checks must be a non-empty array")
        else:
            if report.get("status") != "PASS":
                errors.append("loss-report overall status is not PASS")
            try:
                draft_text = draft.read_text(encoding="utf-8")
            except OSError as exc:
                draft_text = None
                errors.append(f"cannot re-read draft for live loss-check: {exc}")
            live_draft_sha = sha256_file(draft)
            for index, check in enumerate(checks):
                prefix = f"loss-report.checks[{index}]"
                if not isinstance(check, dict):
                    errors.append(f"{prefix} must be an object")
                    continue
                if check.get("draft_sha256") != approval.get("draft_sha256"):
                    errors.append(f"{prefix}.draft_sha256 does not match the bound draft hash")
                if check.get("status") != "PASS":
                    errors.append(f"{prefix}.recorded status is {check.get('status')}; approval requires every check PASS")
                source = check.get("source")
                if not isinstance(source, str) or not source:
                    errors.append(f"{prefix}.source must be a path string")
                    continue
                source_path = Path(source)
                if not source_path.is_file():
                    errors.append(f"{prefix}.source missing on disk: {source}")
                    continue
                min_overlap = check.get("minimum_overlap")
                if not isinstance(min_overlap, (int, float)) or not 0 <= min_overlap <= 1:
                    min_overlap = 0.35
                if draft_text is None:
                    continue
                try:
                    fresh = one_loss_check(source_path, draft_text, live_draft_sha, float(min_overlap))
                except ValueError as exc:
                    errors.append(f"{prefix}: {exc}")
                    continue
                revert_prefix = prefix
                if fresh["source_sha256"] != check.get("source_sha256"):
                    errors.append(f"{revert_prefix}.source changed since loss-check (hash mismatch): {source}")
                if fresh["status"] != check.get("status"):
                    errors.append(f"{revert_prefix}.live re-check status differs from recorded: live={fresh['status']} recorded={check.get('status')}")
                if fresh["missing_headings"] != check.get("missing_headings", []):
                    errors.append(f"{revert_prefix}.live missing_headings differs from recorded: {fresh['missing_headings']}")
                if fresh["missing_commands"] != check.get("missing_commands", []):
                    errors.append(f"{revert_prefix}.live missing_commands differs from recorded: {fresh['missing_commands']}")
                reverified.append({"source": source, "status": fresh["status"], "missing_headings": fresh["missing_headings"], "missing_commands": fresh["missing_commands"]})
    report = {
        "status": "PASS" if not errors else "FAIL",
        "draft": str(draft),
        "approval": str(approval_path.resolve()),
        "loss_report": str(Path(args.loss_report).resolve()) if args.loss_report else None,
        "reverified_count": len(reverified),
        "reverified_checks": reverified,
        "errors": errors,
    }
    return emit(report, args.output)


def cmd_validate_council_verdict(args: argparse.Namespace) -> int:
    return emit(validate_council_verdict(Path(args.verdict)), args.output)


# ---------------------------------------------------------------------------
# Enforced CLI gates for formerly method-only phases (acceptance scope):
#   check-master  -> G0 + G1 + G3 deterministic gates on a staged SKILL.md
#   golden-gate   -> parameterized source/master output reproduction (N/N)
#   benchmark     -> G2 bundle verification (>=3 runs, no LOSS, beats best source)
# ---------------------------------------------------------------------------


def _frontmatter_region(text: str) -> str:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return ""
    end = next((i for i, line in enumerate(lines[1:], 1) if line.strip() == "---"), None)
    if end is None:
        return ""
    return "\n".join(lines[1:end])


G0_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
G1_BLOCK_RE = [
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"(?i)password\s*=\s*['\"][^'\"]{6,}"),
    re.compile(r"(?i)-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"(?i)powershell\s+(-enc\b|-encod\b)"),
    re.compile(r"(?i)base64\s+-d\b"),
]
G1_FLAG_RE = [
    re.compile(r"subprocess"),
    re.compile(r"os\.system"),
    re.compile(r"eval\s*\("),
    re.compile(r"exec\s*\("),
    re.compile(r"curl\s"),
    re.compile(r"wget\s"),
    re.compile(r"powershell\s+-enc\b"),
    re.compile(r"os\.environ"),
    re.compile(r"process\.env"),
    re.compile(r"\.aws"),
]


def master_report(draft: Path, dir_name: str | None = None) -> dict[str, Any]:
    """Run the deterministic G0/G1/G3 gates on a staged master SKILL.md."""
    root = draft.parent
    try:
        text = draft.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"cannot read draft {draft}: {exc}")
    errors: list[str] = []
    g0: list[str] = []
    g1_blocked: list[str] = []
    g1_flagged: list[str] = []
    g3: list[str] = []

    expected_dir = dir_name or root.name
    name: str | None = None
    description: str | None = None
    try:
        name, description = skill_frontmatter(text)
    except ValueError as exc:
        errors.append(f"frontmatter parse failed: {exc}")

    # G0 — spec conformance (agentskills.io-derived constraints)
    if name is None:
        g0.append("frontmatter name missing")
    else:
        if name != expected_dir:
            g0.append(f"name ({name!r}) != directory name ({expected_dir!r})")
        if len(name) > 64:
            g0.append(f"name longer than 64 chars ({len(name)})")
        if not G0_NAME_RE.match(name):
            g0.append(f"name must be lowercase/numbers/hyphens, no leading/trailing/consecutive hyphens: {name!r}")
    if description is None:
        g0.append("description missing")
    else:
        if len(description) > 1024:
            g0.append(f"description longer than 1024 chars ({len(description)})")
        if "<" in description or ">" in description:
            g0.append("description contains XML angle brackets (< >) — prompt-injection surface")
    if len(text.splitlines()) >= 500:
        g0.append(f"SKILL.md body >= 500 lines ({len(text.splitlines())})")
    for ref in referenced_files(draft):
        parts = ref.split("/")
        if len(parts) != 2 or parts[0] != "references":
            g0.append(f"reference not one level deep under references/: {ref}")
        elif not (root / ref).is_file():
            g0.append(f"referenced file missing: {ref}")

    # G1 — security scan (block credential-exfil / obfuscated payload; flag the rest)
    for pattern in G1_BLOCK_RE:
        if pattern.search(text):
            g1_blocked.append(pattern.pattern)
    for pattern in G1_FLAG_RE:
        if pattern.search(text):
            g1_flagged.append(pattern.pattern)
    for dep_file in ("package.json", "requirements.txt"):
        candidate = root / dep_file
        if candidate.is_file() and re.search(r'["\']\^|["\']~', candidate.read_text(encoding="utf-8")):
            g1_flagged.append(f"unpinned dependency range in {dep_file}")

    # G3 — version discipline (quoted string, semver-ish) + merged-from provenance
    fm = _frontmatter_region(text)
    version_match = re.search(r"^version\s*:\s*(.*?)\s*$", fm, re.MULTILINE)
    if not version_match:
        g3.append("version missing from frontmatter")
    else:
        raw = version_match.group(1).strip()
        if not ((raw.startswith('"') and raw.endswith('"')) or (raw.startswith("'") and raw.endswith("'"))):
            g3.append(f"version must be a QUOTED string (YAML float trap): {raw!r}")
        elif not re.fullmatch(r"\d+\.\d+(?:\.\d+)?(?:[-+][0-9A-Za-z.-]+)?", raw[1:-1]):
            g3.append(f"version not valid semver-ish: {raw!r}")
    if re.search(r"^merged-from\s*:", fm, re.MULTILINE):
        after = fm[re.search(r"^merged-from\s*:", fm, re.MULTILINE).end():]
        if not re.search(r"^\s+-\s+.+", after, re.MULTILINE):
            g3.append("merged-from must be a non-empty list of source paths")

    g0_status = "PASS" if not g0 else "FAIL"
    g1_status = "PASS" if not g1_blocked else "FAIL"
    g3_status = "PASS" if not g3 else "FAIL"
    status = "PASS" if not errors and g0_status == g1_status == g3_status == "PASS" else "FAIL"
    return {
        "schema": "skills-catalog-master-check-1",
        "status": status,
        "draft": str(draft.resolve()),
        "dir_name": expected_dir,
        "errors": errors,
        "gates": {
            "G0": {"status": g0_status, "details": g0},
            "G1": {"status": g1_status, "blocked": g1_blocked, "flagged": g1_flagged},
            "G3": {"status": g3_status, "details": g3},
        },
    }


def cmd_check_master(args: argparse.Namespace) -> int:
    try:
        report = master_report(Path(args.draft), args.dir)
    except ValueError as exc:
        return fail(str(exc))
    return emit(report, args.output)


SHELL_META_RE = re.compile(r"[;&|`$()<>*?\[\]{}!]")


INLINE_CODE_ARGS = {"-c", "--command", "--commands", "-e", "--eval", "-eval", "--code", "-exec"}


def validate_runner_argv(runner: Any, errors: list[str], label: str) -> bool:
    if not isinstance(runner, list) or not runner or not all(isinstance(x, str) and x for x in runner):
        errors.append(f"{label}: runner must be a non-empty argv list of non-empty strings")
        return False
    for element in runner:
        if element in INLINE_CODE_ARGS:
            errors.append(
                f"{label}: inline-code executor argument {element!r} is refused "
                "(a benign argv could otherwise run arbitrary code)"
            )
            return False
        if "\x00" in element:
            errors.append(f"{label}: runner element contains NUL byte")
            return False
        if SHELL_META_RE.search(element):
            errors.append(
                f"{label}: runner element contains shell metacharacters; refusing to execute through a shell: {element!r}"
            )
            return False
    return True


def run_runner(runner: list[str], args_list: list[str], workdir: Path, timeout: float) -> tuple[int, str]:
    completed = subprocess.run(
        [*runner, *args_list],
        cwd=str(workdir),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    return completed.returncode, completed.stdout


def golden_gate_report(manifest_path: Path, workdir: Path) -> dict[str, Any]:
    """Run a golden-output gate: every source must reproduce the master's output
    on every fixed input (N/N). Runners are orchestrator-provided argv lists."""
    try:
        manifest = load_json(manifest_path)
    except ValueError as exc:
        return {
            "schema": "skills-catalog-golden-1",
            "status": "FAIL",
            "manifest": str(manifest_path.resolve()),
            "errors": [str(exc)],
            "matched": 0,
            "total": 0,
            "absorption_authorized": False,
            "cells": [],
        }
    if not workdir.is_dir():
        return {
            "schema": "skills-catalog-golden-1",
            "status": "FAIL",
            "manifest": str(manifest_path.resolve()),
            "errors": [f"workdir is not a directory: {workdir}"],
            "matched": 0,
            "total": 0,
            "absorption_authorized": False,
            "cells": [],
        }
    errors: list[str] = []
    if not isinstance(manifest, dict):
        errors.append("manifest must be an object")
        manifest = {}
    master = manifest.get("master")
    sources = manifest.get("sources", [])
    inputs = manifest.get("inputs", [])
    timeout = manifest.get("timeout_seconds", 30)
    if manifest.get("allow_runners") is not True:
        errors.append(
            "runner execution is DISABLED by default; set \"allow_runners\": true in the "
            "golden manifest to opt in (contained, orchestrator-provided argv runners)"
        )
    if not isinstance(master, dict):
        errors.append("master must be an object with a runner argv list")
    if not isinstance(sources, list) or not sources:
        errors.append("sources must be a non-empty array")
    if not isinstance(inputs, list) or not inputs:
        errors.append("inputs must be a non-empty array")
    if not isinstance(timeout, (int, float)) or not 0 < timeout <= 120:
        errors.append("timeout_seconds must be a positive number <= 120")

    master_ok = validate_runner_argv(master.get("runner") if isinstance(master, dict) else None, errors, "master")
    source_runners: list[dict[str, Any]] = []
    for index, source in enumerate(sources if isinstance(sources, list) else []):
        if not isinstance(source, dict) or not isinstance(source.get("name"), str) or not source["name"]:
            errors.append(f"sources[{index}].name must be a non-empty string")
            continue
        if validate_runner_argv(source.get("runner"), errors, f"sources[{index}].runner"):
            source_runners.append(source)
    input_cases: list[dict[str, Any]] = []
    for index, entry in enumerate(inputs if isinstance(inputs, list) else []):
        if not isinstance(entry, dict) or not isinstance(entry.get("id"), str) or not entry["id"]:
            errors.append(f"inputs[{index}].id must be a non-empty string")
            continue
        if not isinstance(entry.get("args", []), list) or not all(isinstance(a, str) for a in entry.get("args", [])):
            errors.append(f"inputs[{index}].args must be a list of strings")
            continue
        input_cases.append(entry)

    cells: list[dict[str, Any]] = []
    matched = 0
    total = 0
    if not errors and master_ok and source_runners and input_cases:
        for entry in input_cases:
            args_list = entry.get("args", [])
            for source in source_runners:
                total += 1
                try:
                    master_rc, master_out = run_runner(master["runner"], args_list, workdir, float(timeout))
                except subprocess.TimeoutExpired:
                    cells.append({"input": entry["id"], "source": source["name"], "status": "FAIL", "error": "master runner timed out"})
                    continue
                if master_rc != 0:
                    cells.append({"input": entry["id"], "source": source["name"], "status": "FAIL", "error": f"master runner exited {master_rc}"})
                    continue
                try:
                    src_rc, src_out = run_runner(source["runner"], args_list, workdir, float(timeout))
                except subprocess.TimeoutExpired:
                    cells.append({"input": entry["id"], "source": source["name"], "status": "FAIL", "error": "source runner timed out"})
                    continue
                if src_rc != 0:
                    cells.append({"input": entry["id"], "source": source["name"], "status": "FAIL", "error": f"source runner exited {src_rc}"})
                    continue
                equal = master_out == src_out
                if equal:
                    matched += 1
                cells.append({
                    "input": entry["id"],
                    "source": source["name"],
                    "status": "PASS" if equal else "FAIL",
                    "master_sha256": sha256_bytes(master_out.encode("utf-8")),
                    "source_sha256": sha256_bytes(src_out.encode("utf-8")),
                    "equal": equal,
                })
    status = "PASS" if not errors and total and matched == total else "FAIL"
    return {
        "schema": "skills-catalog-golden-1",
        "status": status,
        "manifest": str(manifest_path.resolve()),
        "workdir": str(workdir.resolve()),
        "matched": matched,
        "total": total,
        "absorption_authorized": status == "PASS",
        "cells": cells,
        "errors": errors,
    }


def cmd_golden_gate(args: argparse.Namespace) -> int:
    try:
        report = golden_gate_report(Path(args.manifest), Path(args.workdir))
    except (ValueError, OSError) as exc:
        return fail(str(exc))
    return emit(report, args.output)


def benchmark_report(bundle_path: Path) -> dict[str, Any]:
    """Verify a G2 benchmark bundle: >=3 runs/cell, master wins-or-ties every
    cell, and master beats the best source overall. Judge verdicts are the
    orchestrator's LLM-judge artifact; this gate enforces the conditions."""
    try:
        bundle = load_json(bundle_path)
    except ValueError as exc:
        return {
            "schema": "skills-catalog-benchmark-1",
            "status": "FAIL",
            "bundle": str(bundle_path.resolve()),
            "errors": [str(exc)],
            "verdict": "NO-GO",
            "cells": 0,
            "master_wins": 0,
            "best_source_wins": 0,
        }
    errors: list[str] = []
    if not isinstance(bundle, dict):
        errors.append("bundle must be an object")
        bundle = {}
    min_runs = bundle.get("runs_per_cell")
    if not isinstance(min_runs, int) or min_runs < 3:
        errors.append("runs_per_cell must be an integer >= 3")
    cells = bundle.get("cells", [])
    if not isinstance(cells, list) or not cells:
        errors.append("cells must be a non-empty array")

    has_vs_source = False
    has_vs_baseline = False
    wins: dict[str, int] = {}
    source_beats: dict[str, int] = {}
    losses: list[str] = []
    for index, cell in enumerate(cells if isinstance(cells, list) else []):
        prefix = f"cells[{index}]"
        if not isinstance(cell, dict):
            errors.append(f"{prefix} must be an object")
            continue
        cid = cell.get("id")
        kind = cell.get("kind")
        verdict = cell.get("verdict")
        runs = cell.get("runs")
        if not isinstance(cid, str) or not cid:
            errors.append(f"{prefix}.id must be a non-empty string")
        if kind not in {"master_vs_source", "master_vs_baseline"}:
            errors.append(f"{prefix}.kind must be master_vs_source or master_vs_baseline")
        elif kind == "master_vs_source":
            has_vs_source = True
        else:
            has_vs_baseline = True
        if verdict not in {"WIN", "TIE", "LOSS"}:
            errors.append(f"{prefix}.verdict must be WIN/TIE/LOSS")
        if not isinstance(runs, int) or runs < 3:
            errors.append(f"{prefix}.runs must be an integer >= 3")
        if verdict == "LOSS":
            losses.append(str(cid))
        if kind == "master_vs_source":
            source_name = cell.get("source", "?")
            if verdict == "WIN":
                wins[source_name] = wins.get(source_name, 0) + 1
            elif verdict == "LOSS":
                source_beats[source_name] = source_beats.get(source_name, 0) + 1
    if not has_vs_source:
        errors.append("bundle must contain at least one master_vs_source cell")
    if not has_vs_baseline:
        errors.append("bundle must contain at least one master_vs_baseline cell")
    if losses:
        errors.append(f"master LOST {len(losses)} cell(s); promotion blocked: {losses}")

    master_wins = sum(wins.values())
    best_source_wins = max(source_beats.values()) if source_beats else 0
    if source_beats and master_wins <= best_source_wins:
        errors.append(f"master ({master_wins} wins) does not beat the best source ({best_source_wins} source-wins)")

    status = "PASS" if not errors else "FAIL"
    return {
        "schema": "skills-catalog-benchmark-1",
        "status": status,
        "bundle": str(bundle_path.resolve()),
        "runs_per_cell": min_runs if isinstance(min_runs, int) else None,
        "cell_count": len(cells if isinstance(cells, list) else []),
        "master_wins": master_wins,
        "best_source_wins": best_source_wins,
        "errors": errors,
        "verdict": "GO" if status == "PASS" else "NO-GO",
    }


def cmd_benchmark(args: argparse.Namespace) -> int:
    try:
        report = benchmark_report(Path(args.bundle))
    except (ValueError, OSError) as exc:
        return fail(str(exc))
    return emit(report, args.output)


def cmd_repair(args: argparse.Namespace) -> int:
    loss_report_path = Path(args.loss_report)
    draft_path = Path(args.draft)
    
    errors = []
    try:
        loss_report = load_json(loss_report_path)
    except ValueError as exc:
        errors.append(f"malformed loss-report: {exc}")
        return _repair_emit_fail(errors, args)
        
    if not isinstance(loss_report, dict) or loss_report.get("schema") != "skills-catalog-loss-check-1":
        errors.append("malformed loss-report: invalid schema or format")
        return _repair_emit_fail(errors, args)
        
    checks = loss_report.get("checks", [])
    if not isinstance(checks, list) or not checks:
        errors.append("malformed loss-report: non-empty checks array is required")
        return _repair_emit_fail(errors, args)
        
    # Get expected draft_sha256 from the report
    expected_draft_sha = None
    for c in checks:
        if isinstance(c, dict) and "draft_sha256" in c:
            expected_draft_sha = c["draft_sha256"]
            break
            
    if not expected_draft_sha:
        errors.append("malformed loss-report: missing draft_sha256 in checks")
        return _repair_emit_fail(errors, args)
        
    # Read current draft
    try:
        draft_content = draft_path.read_text(encoding="utf-8")
    except OSError as exc:
        errors.append(f"cannot read draft {draft_path}: {exc}")
        return _repair_emit_fail(errors, args)
        
    current_draft_sha = sha256_bytes(draft_content.encode("utf-8"))
    
    # Hash-bind: refuse if changed unless --allow-draft-change
    if current_draft_sha != expected_draft_sha and not args.allow_draft_change:
        errors.append("draft hash changed and --allow-draft-change absent")
        return _repair_emit_fail(errors, args)
        
    # Filter checks if --source is provided
    if args.source:
        allowed_sources = set(args.source)
        filtered_checks = []
        for c in checks:
            if isinstance(c, dict) and "source" in c and any(
                s in c["source"] or c["source"].endswith(s) for s in allowed_sources
            ):
                filtered_checks.append(c)
        if not filtered_checks:
            errors.append("no matching sources found in loss-report checks")
            return _repair_emit_fail(errors, args)
        checks = filtered_checks

    # Keep track of per-round verdicts for each check
    check_records = []
    for c in checks:
        source_path = Path(c["source"])
        min_overlap = c.get("minimum_overlap", 0.35)
        check_records.append({
            "source": str(source_path.resolve()),
            "source_path": source_path,
            "minimum_overlap": min_overlap,
            "verdicts": []
        })

    rounds_run = 0
    max_rounds = 3
    final_status = "ESCALATE"
    
    last_seen_sha = current_draft_sha
    
    for r in range(1, max_rounds + 1):
        rounds_run = r
        
        # Re-read current draft content and sha
        try:
            draft_content = draft_path.read_text(encoding="utf-8")
        except OSError as exc:
            errors.append(f"cannot read draft {draft_path} in round {r}: {exc}")
            return _repair_emit_fail(errors, args)
        current_draft_sha = sha256_bytes(draft_content.encode("utf-8"))
        last_seen_sha = current_draft_sha
        
        round_all_pass = True
        latest_results = {}
        
        for rec in check_records:
            # Re-run mechanical one_loss_check
            try:
                res = one_loss_check(rec["source_path"], draft_content, current_draft_sha, rec["minimum_overlap"])
            except ValueError as exc:
                errors.append(str(exc))
                return _repair_emit_fail(errors, args)
            
            rec["verdicts"].append(res["status"])
            latest_results[rec["source"]] = res
            if res["status"] != "PASS":
                round_all_pass = False
                
        if round_all_pass:
            final_status = "PASS"
            break
            
        # If any fail and we haven't reached round 3, wait for modification
        if r < max_rounds:
            # Default wait of 2 seconds per round, overridable via CATALOG_GOVERNANCE_REPAIR_POLL_SECONDS
            try:
                poll_seconds = float(os.environ.get("CATALOG_GOVERNANCE_REPAIR_POLL_SECONDS", "2.0"))
            except ValueError:
                poll_seconds = 2.0
            poll_seconds = max(poll_seconds, 0)
            iterations = max(1, int(poll_seconds * 10))
            for _ in range(iterations):
                time.sleep(0.1)
                try:
                    new_content = draft_path.read_text(encoding="utf-8")
                    new_sha = sha256_bytes(new_content.encode("utf-8"))
                    if new_sha != last_seen_sha:
                        break
                except OSError:
                    pass

    # Build final checks and defects
    final_checks = []
    defects = []
    for rec in check_records:
        final_verdict = rec["verdicts"][-1]
        final_checks.append({
            "source": rec["source"],
            "verdicts": rec["verdicts"],
            "final_verdict": final_verdict
        })
        if final_verdict != "PASS":
            latest_res = latest_results.get(rec["source"], {})
            defects.append({
                "source": rec["source"],
                "missing_headings": latest_res.get("missing_headings", []),
                "missing_commands": latest_res.get("missing_commands", []),
                "word_overlap": latest_res.get("word_overlap", 0.0),
                "minimum_overlap": rec["minimum_overlap"]
            })
            
    report = {
        "schema": "skills-catalog-repair-1",
        "status": final_status,
        "rounds_run": rounds_run,
        "checks": final_checks,
        "defects": defects
    }
    
    return emit(report, args.output)


def _repair_emit_fail(errors: list[str], args: argparse.Namespace) -> int:
    """Helper for cmd_repair to emit a structured FAIL report with errors[]."""
    report = {
        "schema": "skills-catalog-repair-1",
        "status": "FAIL",
        "rounds_run": 0,
        "checks": [],
        "defects": [],
        "errors": errors,
    }
    return emit(report, args.output)

V2_SUCCESS_STATUSES = {
    "PASS", "PLANNED", "ESCALATE", "QUARANTINED", "EVALUATED", "APPROVED",
    "ACTIVE", "CLEAN", "RESTORED", "REJECTED", "BLOCKED", "REQUIRES_REVIEW", "CAPTURED",
}
V2_PROPOSAL_SCHEMA = "skill-proposal-1"
V2_POLICY_SCHEMA = "skill-policy-1"
V2_CREATE_ACTION = "CREATE"
V2_AUTO_APPROVAL_FIELDS = {"allow_low_risk_auto_approval", "allow_automatic_merge"}
V2_CAPABILITIES = {
    "read_repository", "write_filesystem", "mutate_git", "execute_process",
    "access_network", "access_credentials", "modify_harness_config",
    "modify_skill_catalog", "invoke_other_skills",
}
V2_RISK_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
V2_STATUS_TRANSITIONS = {
    "RECEIVED": {"QUARANTINED"},
    "QUARANTINED": {"EVALUATING"},
    "EVALUATING": {"REQUIRES_REVIEW", "APPROVED", "REJECTED", "BLOCKED"},
    "REQUIRES_REVIEW": {"APPROVED", "REJECTED", "BLOCKED"},
    "APPROVED": {"ACTIVATING"},
    "ACTIVATING": {"ACTIVE", "QUARANTINED"},
    "ACTIVE": {"ROLLBACK_PENDING", "DRIFTED"},
    "ROLLBACK_PENDING": {"RESTORED", "ACTIVE"},
}


def v2_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def v2_report(report: dict[str, Any], output: str | None = None) -> int:
    status = report.get("status")
    exit_code = 0 if status in V2_SUCCESS_STATUSES else 1
    report = {"exit_code": exit_code, **report}
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if output:
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        Path(output).write_text(rendered, encoding="utf-8", newline="\n")
    print(rendered, end="")
    return exit_code


def _emit_v2_failure(report: dict[str, Any], output: str | None = None) -> int:
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if output:
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        Path(output).write_text(rendered, encoding="utf-8", newline="\n")
    print(rendered, end="")
    return 1


def v2_path(path_value: str | Path) -> Path:
    return Path(path_value).expanduser().resolve(strict=False)


def v2_reject_links(path: Path, label: str) -> None:
    if is_link_or_reparse(path):
        raise ValueError(f"{label} is a symlink/junction/reparse point; refusing: {path}")


def v2_reject_link_ancestors(path: Path, label: str) -> None:
    candidate = path.expanduser()
    for ancestor in (candidate, *candidate.parents):
        if ancestor.exists() and is_link_or_reparse(ancestor):
            raise ValueError(f"{label} contains a symlink/junction/reparse ancestor; refusing: {ancestor}")


def v2_validate_roots(governance_root: Path, active_root: Path) -> tuple[Path, Path]:
    v2_reject_link_ancestors(governance_root, "governance root")
    v2_reject_link_ancestors(active_root, "active root")
    governance_root = v2_path(governance_root)
    active_root = v2_path(active_root)
    if governance_root == active_root:
        raise ValueError("governance root and active root must be different")
    if within(governance_root, active_root) or within(active_root, governance_root):
        raise ValueError("governance root and active root must not overlap")
    if governance_root.exists():
        v2_reject_links(governance_root, "governance root")
    if active_root.exists():
        v2_reject_links(active_root, "active root")
    return governance_root, active_root


def v2_safe_id(value: Any, label: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", value):
        raise ValueError(f"{label} must be a non-empty safe identifier")
    return value


def v2_validate_proposal(skill_path: Path, provenance_path: Path, active_root: Path) -> tuple[dict[str, Any], bytes, str]:
    try:
        payload = load_json(provenance_path)
    except ValueError as exc:
        raise ValueError(f"invalid proposal provenance: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("proposal provenance must be an object")  # noqa: TRY004 - ValueError is the established CLI error contract
    if payload.get("schema") != V2_PROPOSAL_SCHEMA:
        raise ValueError("proposal schema must be skill-proposal-1")
    proposal_id = v2_safe_id(payload.get("proposal_id"), "proposal_id")
    if payload.get("requested_action") != V2_CREATE_ACTION:
        raise ValueError("V2.0 accepts requested_action CREATE only")
    required = (
        "generated_by", "generator_version", "generated_at_utc", "source_session",
        "source_task", "skill_sha256", "declared_capabilities", "target",
    )
    missing = [key for key in required if key not in payload]
    if missing:
        raise ValueError(f"proposal missing required fields: {', '.join(missing)}")
    if not skill_path.is_file():
        raise ValueError(f"skill file does not exist: {skill_path}")
    try:
        skill_bytes = skill_path.read_bytes()
        skill_text = skill_bytes.decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ValueError(f"cannot read UTF-8 skill file: {exc}") from exc
    actual_sha = sha256_bytes(skill_bytes)
    if payload.get("skill_sha256") != actual_sha:
        raise ValueError("proposal hash (skill_sha256) does not match exact SKILL.md bytes")
    target = payload.get("target")
    if not isinstance(target, dict):
        raise ValueError("proposal target must be an object")  # noqa: TRY004 - ValueError is the established CLI error contract
    if target.get("kind") != "new_skill":
        raise ValueError("V2.0 CREATE target kind must be new_skill")
    target_name = target.get("name")
    if not isinstance(target_name, str) or not G0_NAME_RE.fullmatch(target_name):
        raise ValueError("proposal target name must be lowercase letters, numbers, and hyphens")
    parsed_name, _ = skill_frontmatter(skill_text)
    if parsed_name != target_name:
        raise ValueError("proposal target name does not match SKILL.md frontmatter name")
    declared = payload.get("declared_capabilities")
    if not isinstance(declared, list) or not all(isinstance(item, str) and item for item in declared):
        raise ValueError("declared_capabilities must be a list of non-empty strings")
    if any(item not in V2_CAPABILITIES for item in declared):
        unknown = sorted(set(declared) - V2_CAPABILITIES)
        raise ValueError(f"unknown declared capabilities: {unknown}")
    if target.get("active_root") is None:
        raise ValueError("proposal target active root is required")
    if v2_path(target["active_root"]) != active_root:
        raise ValueError("proposal target active root does not match --active-root")
    for key in V2_AUTO_APPROVAL_FIELDS:
        if payload.get(key) is True:
            raise ValueError(f"{key}=true is forbidden in V2.0")
    payload_dir = payload.get("payload_dir")
    if payload_dir:
        payload_path = v2_path(payload_dir)
        if payload_path.exists():
            try:
                has_payload = any(payload_path.iterdir())
            except OSError as exc:
                raise ValueError(f"cannot inspect proposal payload: {exc}") from exc
            if has_payload:
                raise ValueError("non-empty proposal payload is unsupported in V2.0; reject explicitly")
    return payload, skill_bytes, proposal_id


def v2_append_event(root: Path, proposal_id: str, source: str, target: str, actor: str, command: str, input_hashes: list[str] | None = None, artifacts: list[str] | None = None) -> dict[str, Any]:
    journal = root / "lifecycle.jsonl"
    journal.parent.mkdir(parents=True, exist_ok=True)
    event_no = 1
    if journal.is_file():
        for line in journal.read_text(encoding="utf-8").splitlines():
            if line.strip():
                event_no += 1
    event = {
        "schema": "skill-lifecycle-1",
        "event_no": event_no,
        "proposal_id": proposal_id,
        "from": source,
        "to": target,
        "actor": actor,
        "command": command,
        "created_at_utc": v2_timestamp(),
        "input_sha256": sorted(input_hashes or []),
        "artifact_paths": sorted(artifacts or []),
    }
    with journal.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")
    return event


def cmd_check_policy(args: argparse.Namespace) -> int:
    try:
        policy = load_json(Path(args.policy))
    except ValueError as exc:
        return v2_report({"status": "FAIL", "message": str(exc), "errors": [str(exc)]}, args.output)
    errors: list[str] = []
    if not isinstance(policy, dict):
        errors.append("policy must be an object")
        policy = {}
    if policy.get("schema") != V2_POLICY_SCHEMA:
        errors.append("policy schema must be skill-policy-1")
    if policy.get("default_state") != "QUARANTINED":
        errors.append("policy default_state must be QUARANTINED")
    if policy.get("allow_low_risk_auto_approval") is True:
        errors.append("automatic approval is forbidden in V2.0")
    if policy.get("allow_automatic_merge") is True:
        errors.append("automatic merge is forbidden in V2.0")
    for key in ("require_human_for_low_risk", "require_human_for_medium_risk", "require_human_for_high_risk", "block_auto_activation_for_critical", "require_snapshot_before_activation", "require_rollback_test"):
        if policy.get(key) is False:
            errors.append(f"policy cannot disable required V2.0 control: {key}")
    report = {"schema": "skills-catalog-policy-check-1", "status": "PASS" if not errors else "FAIL", "policy": str(Path(args.policy).resolve()), "policy_sha256": sha256_file(Path(args.policy)), "errors": errors}
    return v2_report(report, args.output)


def v2_capture_usage_record(usage_path: Path, skill_name: str) -> dict[str, Any]:
    usage = load_json(usage_path)
    if not isinstance(usage, dict):
        raise ValueError("Hermes usage file must be an object")  # noqa: TRY004 - ValueError is the established CLI error contract
    record = usage.get(skill_name)
    if not isinstance(record, dict):
        skills = usage.get("skills")
        record = skills.get(skill_name) if isinstance(skills, dict) else None
    if not isinstance(record, dict):
        raise ValueError(f"Hermes usage record is missing for skill: {skill_name}")  # noqa: TRY004 - ValueError is the established CLI error contract
    if record.get("created_by") != "agent" and record.get("agent_created") is not True:
        raise ValueError("Hermes usage record is not marked agent-created")
    return record


def v2_capture_metadata(metadata_path: Path) -> dict[str, Any]:
    metadata = load_json(metadata_path)
    if not isinstance(metadata, dict):
        raise ValueError("Hermes capture metadata must be an object")  # noqa: TRY004 - ValueError is the established CLI error contract
    required = ("schema", "hermes_version", "hermes_commit", "source_session", "captured_at_utc")
    missing = [key for key in required if key not in metadata]
    if missing:
        raise ValueError(f"capture metadata missing required fields: {', '.join(missing)}")
    if metadata.get("schema") != "hermes-capture-1":
        raise ValueError("capture metadata schema must be hermes-capture-1")
    if not re.fullmatch(r"[0-9a-fA-F]{40}", str(metadata["hermes_commit"])):
        raise ValueError("hermes_commit must be a 40-character hexadecimal commit")
    if not all(isinstance(metadata[key], str) and metadata[key].strip() for key in ("hermes_version", "source_session", "captured_at_utc")):
        raise ValueError("Hermes capture identity fields must be non-empty strings")
    for optional_key in ("source_task", "write_origin"):
        if optional_key in metadata and not isinstance(metadata[optional_key], str):
            raise ValueError(f"Hermes capture field must be a string: {optional_key}")
    try:
        datetime.fromisoformat(metadata["captured_at_utc"].replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("captured_at_utc must be an RFC 3339 timestamp") from exc
    return metadata


def cmd_capture_hermes(args: argparse.Namespace) -> int:
    skill_dir = v2_path(args.skill_dir)
    usage_path = v2_path(args.usage)
    metadata_path = v2_path(args.metadata)
    output_dir = v2_path(args.output)
    active_root = v2_path(args.active_root)
    try:
        v2_reject_link_ancestors(skill_dir, "Hermes skill directory")
        v2_reject_link_ancestors(output_dir, "capture output")
        if within(output_dir, active_root) or within(active_root, output_dir):
            raise ValueError("capture output and active root must not overlap")
        if not skill_dir.is_dir() or is_link_or_reparse(skill_dir):
            raise ValueError(f"Hermes skill directory is not a real directory: {skill_dir}")
        skill_path = skill_dir / "SKILL.md"
        if not skill_path.is_file() or is_link_or_reparse(skill_path):
            raise ValueError("Hermes skill directory must contain a regular SKILL.md")
        supporting = [path for path in skill_dir.rglob("*") if path != skill_path and not is_link_or_reparse(path)]
        if supporting:
            raise ValueError("non-empty Hermes skill payload is unsupported in the V2 single-file capture path")
        skill_text = skill_path.read_text(encoding="utf-8")
        skill_name, _ = skill_frontmatter(skill_text)
        if not skill_name:
            raise ValueError("Hermes SKILL.md must contain a valid name in frontmatter")
        usage_record = v2_capture_usage_record(usage_path, skill_name)
        metadata = v2_capture_metadata(metadata_path)
        skill_sha = sha256_file(skill_path)
        usage_sha = sha256_file(usage_path)
        metadata_sha = sha256_file(metadata_path)
        proposal_id = f"hermes-{skill_name}-{skill_sha[:12]}"
        proposal = {
            "schema": V2_PROPOSAL_SCHEMA,
            "proposal_id": proposal_id,
            "generated_by": "hermes",
            "generator_version": metadata["hermes_version"],
            "generated_at_utc": metadata["captured_at_utc"],
            "source_session": metadata["source_session"],
            "source_task": metadata.get("source_task", ""),
            "skill_sha256": skill_sha,
            "declared_capabilities": [],
            "requested_action": V2_CREATE_ACTION,
            "target": {"kind": "new_skill", "name": skill_name, "active_root": str(active_root)},
            "hermes_provenance": {
                "provenance_status": "ASSERTED_FROM_USAGE",
                "created_by": usage_record.get("created_by", "agent"),
                "hermes_commit": metadata["hermes_commit"],
                "usage_sha256": usage_sha,
                "metadata_sha256": metadata_sha,
                "capability_source": "not-provided-by-hermes",
            },
        }
        if usage_record.get("agent_created") is not None:
            proposal["hermes_provenance"]["agent_created"] = usage_record["agent_created"]
        if metadata.get("write_origin"):
            proposal["hermes_provenance"]["write_origin"] = metadata["write_origin"]
        if output_dir.exists():
            raise ValueError(f"capture output already exists; refusing overwrite: {output_dir}")
        output_dir.mkdir(parents=True)
        shutil.copy2(skill_path, output_dir / "SKILL.md")
        shutil.copy2(usage_path, output_dir / ".usage.json")
        shutil.copy2(metadata_path, output_dir / "hermes-capture.json")
        proposal_sha = v2_write_json(output_dir / "proposal.json", proposal)
        receipt = {
            "schema": "hermes-capture-receipt-1",
            "proposal_id": proposal_id,
            "provenance_status": "ASSERTED_FROM_USAGE",
            "skill_sha256": skill_sha,
            "usage_sha256": usage_sha,
            "metadata_sha256": metadata_sha,
            "proposal_sha256": proposal_sha,
            "source_skill": str(skill_path),
            "source_usage": str(usage_path),
            "source_metadata": str(metadata_path),
            "usage_record": usage_record,
            "hermes_version": metadata["hermes_version"],
            "hermes_commit": metadata["hermes_commit"],
        }
        receipt_sha = v2_write_json(output_dir / "receipt.json", receipt)
        return v2_report({"schema": "skills-catalog-hermes-capture-1", "status": "CAPTURED", "proposal_id": proposal_id, "output": str(output_dir), "skill_sha256": skill_sha, "proposal_sha256": proposal_sha, "receipt_sha256": receipt_sha, "provenance_status": "ASSERTED_FROM_USAGE"}, args.output_report)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return v2_report({"schema": "skills-catalog-hermes-capture-1", "status": "FAIL", "message": str(exc), "errors": [str(exc)]}, args.output_report)


def cmd_intake(args: argparse.Namespace) -> int:
    skill_path = v2_path(args.skill)
    provenance_path = v2_path(args.provenance)
    try:
        governance_root, active_root = v2_validate_roots(Path(args.root), Path(args.active_root))
        payload, skill_bytes, proposal_id = v2_validate_proposal(skill_path, provenance_path, active_root)
        quarantine = governance_root / "quarantine" / proposal_id
        existing_skill = quarantine / "SKILL.md"
        existing_provenance = quarantine / "proposal.json"
        if quarantine.exists():
            if not existing_skill.is_file() or not existing_provenance.is_file():
                raise ValueError("proposal ID already exists with incomplete quarantine record")
            if sha256_file(existing_skill) != payload["skill_sha256"] or sha256_file(existing_provenance) != sha256_file(provenance_path):
                raise ValueError("proposal ID collision with different content")
            return v2_report({"schema": "skills-catalog-intake-1", "status": "QUARANTINED", "proposal_id": proposal_id, "idempotent": True, "quarantine": str(quarantine.resolve()), "active_root": str(active_root)}, args.output)
        staging = governance_root / f".intake-{proposal_id}-{uuid.uuid4().hex}"
        staging.mkdir(parents=True, exist_ok=False)
        try:
            (staging / "SKILL.md").write_bytes(skill_bytes)
            shutil.copy2(provenance_path, staging / "proposal.json")
            record = {
                "schema": "skills-catalog-intake-1",
                "proposal_id": proposal_id,
                "status": "QUARANTINED",
                "active_root": str(active_root),
                "skill_sha256": payload["skill_sha256"],
                "proposal_sha256": sha256_file(provenance_path),
                "received_at_utc": v2_timestamp(),
            }
            (staging / "intake.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            quarantine.parent.mkdir(parents=True, exist_ok=True)
            staging.rename(quarantine)
        except Exception:
            shutil.rmtree(staging, ignore_errors=True)
            raise
        event = v2_append_event(governance_root, proposal_id, "RECEIVED", "QUARANTINED", args.actor, "intake", [payload["skill_sha256"], record["proposal_sha256"]], [str(quarantine / "intake.json")])
        return v2_report({"schema": "skills-catalog-intake-1", "status": "QUARANTINED", "proposal_id": proposal_id, "idempotent": False, "quarantine": str(quarantine.resolve()), "active_root": str(active_root), "event_no": event["event_no"]}, args.output)
    except (OSError, ValueError) as exc:
        return v2_report({"schema": "skills-catalog-intake-1", "status": "FAIL", "message": str(exc), "errors": [str(exc)]}, args.output)


def cmd_inspect_proposal(args: argparse.Namespace) -> int:
    proposal_dir = v2_path(args.proposal)
    try:
        data = load_json(proposal_dir / "proposal.json")
        skill = proposal_dir / "SKILL.md"
        if not isinstance(data, dict) or not skill.is_file():
            raise ValueError("quarantine record must contain proposal.json and SKILL.md")
        return v2_report({"schema": "skills-catalog-inspection-1", "status": "PASS", "proposal_id": data.get("proposal_id"), "skill_sha256": sha256_file(skill), "proposal_sha256": sha256_file(proposal_dir / "proposal.json"), "declared_capabilities": data.get("declared_capabilities", []), "target": data.get("target")}, args.output)
    except (OSError, ValueError) as exc:
        return v2_report({"schema": "skills-catalog-inspection-1", "status": "FAIL", "message": str(exc), "errors": [str(exc)]}, args.output)


def v2_detect_capabilities(text: str) -> tuple[set[str], list[str]]:
    signals: list[tuple[str, str, str]] = [
        ("write_filesystem", r"\b(write|modify|edit|create|delete|remove)\b.*\b(file|folder|directory|path)s?\b", "filesystem mutation language"),
        ("mutate_git", r"\bgit\s+(commit|push|reset|checkout|merge|rebase)\b", "git mutation command"),
        ("execute_process", r"\b(subprocess|shell|exec|run a command|execute)\b", "process execution language"),
        ("access_network", r"\b(curl|wget|http://|https://|network|web request)\b", "network language or URL"),
        ("access_credentials", r"\b(password|secret|token|api[_ -]?key|credential)\b", "credential language"),
        ("modify_harness_config", r"\b(AGENTS\.md|CLAUDE\.md|hook|harness config|policy)\b", "harness/configuration language"),
        ("modify_skill_catalog", r"\b(skill catalog|skill store|activate|quarantine|promote)\b", "skill catalog control language"),
        ("invoke_other_skills", r"\b(invoke|delegate|call)\b.*\bskill\b", "skill invocation language"),
        ("read_repository", r"\b(read|inspect|scan|search|find)\b.*\b(repository|repo|file|code)\b", "repository read language"),
    ]
    detected: set[str] = set()
    reasons: list[str] = []
    for capability, pattern, reason in signals:
        if re.search(pattern, text, re.IGNORECASE | re.DOTALL):
            detected.add(capability)
            reasons.append(f"{capability}: {reason}")
    return detected, sorted(reasons)


def v2_effective_risk(declared: list[str], detected: set[str]) -> str:
    capabilities = set(declared) | detected
    if capabilities & {"access_credentials", "modify_harness_config", "modify_skill_catalog"}:
        return "CRITICAL"
    if capabilities & {"write_filesystem", "mutate_git", "execute_process", "access_network", "invoke_other_skills"}:
        return "HIGH"
    if capabilities & {"read_repository"}:
        return "MEDIUM"
    return "LOW"


def v2_write_json(path: Path, payload: dict[str, Any]) -> str:
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(rendered, encoding="utf-8")
    return sha256_file(path)


def cmd_evaluate_proposal(args: argparse.Namespace) -> int:
    proposal_dir = v2_path(args.proposal)
    governance_root = v2_path(args.root)
    active_root = v2_path(args.active_root)
    try:
        data = load_json(proposal_dir / "proposal.json")
        skill_path = proposal_dir / "SKILL.md"
        if not isinstance(data, dict) or not skill_path.is_file():
            raise ValueError("quarantine record must contain proposal.json and SKILL.md")
        if data.get("requested_action") != V2_CREATE_ACTION:
            raise ValueError("V2.0 evaluation accepts CREATE proposals only")
        if v2_path(data.get("target", {}).get("active_root")) != active_root:
            raise ValueError("proposal active root does not match --active-root")
        text = skill_path.read_text(encoding="utf-8")
        declared = data.get("declared_capabilities", [])
        detected, reasons = v2_detect_capabilities(text)
        undeclared = sorted(detected - set(declared))
        effective = v2_effective_risk(declared, detected)
        skill_sha = sha256_file(skill_path)
        validation = {"schema": "skills-catalog-validation-1", "status": "PASS", "proposal_id": data["proposal_id"], "skill_sha256": skill_sha, "evaluated_skill_sha256": skill_sha, "frontmatter": skill_frontmatter(text)[0] is not None, "limits": "Package and frontmatter validation do not establish behavior or safety."}
        capabilities = {"schema": "skills-catalog-capabilities-1", "status": "PASS", "proposal_id": data["proposal_id"], "declared": sorted(declared), "detected": sorted(detected), "undeclared": undeclared, "effective": effective, "reasons": reasons, "limits": "Heuristic textual signal detection; it cannot prove runtime behavior or absence of prompt injection."}
        validation_sha = v2_write_json(proposal_dir / "validation.json", validation)
        capabilities_sha = v2_write_json(proposal_dir / "capabilities.json", capabilities)
        event = v2_append_event(governance_root, data["proposal_id"], "QUARANTINED", "EVALUATING", args.actor, "evaluate-proposal", [sha256_file(skill_path), sha256_file(proposal_dir / "proposal.json")], [str(proposal_dir / "validation.json"), str(proposal_dir / "capabilities.json")])
        return v2_report({"schema": "skills-catalog-evaluation-1", "status": "EVALUATED", "proposal_id": data["proposal_id"], "validation_sha256": validation_sha, "capabilities_sha256": capabilities_sha, "capabilities": capabilities, "event_no": event["event_no"]}, args.output)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return v2_report({"schema": "skills-catalog-evaluation-1", "status": "FAIL", "message": str(exc), "errors": [str(exc)]}, args.output)


def v2_scan_file_roots(roots: list[str], skill_name: str) -> tuple[list[str], list[str], list[dict[str, Any]]]:
    searched: list[str] = []
    unscanned: list[str] = []
    findings: list[dict[str, Any]] = []
    for raw_root in roots:
        root = v2_path(raw_root)
        if not root.is_dir() or is_link_or_reparse(root):
            unscanned.append(str(root))
            continue
        searched.append(str(root))
        try:
            files = sorted(path for path in root.rglob("*") if path.is_file() and not is_link_or_reparse(path))
        except OSError:
            unscanned.append(str(root))
            searched.remove(str(root))
            continue
        for path in files:
            try:
                content = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            if re.search(rf"\b{re.escape(skill_name)}\b", content, re.IGNORECASE):
                findings.append({"kind": "ACTIVE_CONSUMER_FOUND", "path": str(path.resolve()), "match": skill_name})
    return sorted(set(searched)), sorted(set(unscanned)), findings


def cmd_impact_report(args: argparse.Namespace) -> int:
    proposal_dir = v2_path(args.proposal)
    try:
        data = load_json(proposal_dir / "proposal.json")
        if not isinstance(data, dict):
            raise ValueError("proposal.json must be an object")  # noqa: TRY004 - ValueError is the established CLI error contract
        target = data.get("target", {})
        skill_name = target.get("name")
        roots = list(args.scan_root or [])
        if not roots:
            roots = [str(v2_path(args.active_root))]
        searched, unscanned, findings = v2_scan_file_roots(roots, str(skill_name))
        report = {"schema": "skills-catalog-impact-1", "status": "PASS", "proposal_id": data.get("proposal_id"), "active_root": str(v2_path(args.active_root)), "searched_roots": searched, "unscanned_roots": unscanned, "complete": not unscanned, "findings": sorted(findings, key=lambda item: (item["kind"], item["path"], item["match"]))}
        report_sha = v2_write_json(proposal_dir / "impact.json", report)
        return v2_report({**report, "impact_sha256": report_sha}, args.output)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return v2_report({"schema": "skills-catalog-impact-1", "status": "FAIL", "message": str(exc), "errors": [str(exc)]}, args.output)


def v2_evidence_hash(proposal_dir: Path) -> str:
    paths = [proposal_dir / name for name in ("validation.json", "capabilities.json", "impact.json")]
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        raise ValueError(f"missing evaluation evidence: {', '.join(missing)}")
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.name.encode("utf-8"))
        digest.update(sha256_file(path).encode("ascii"))
    return digest.hexdigest()


def cmd_decide(args: argparse.Namespace) -> int:
    proposal_dir = v2_path(args.proposal)
    governance_root = v2_path(args.root)
    policy_path = v2_path(args.policy)
    decision_path = v2_path(args.output) if args.output else governance_root / "decisions" / f"{proposal_dir.name}.json"
    try:
        proposal = load_json(proposal_dir / "proposal.json")
        if not isinstance(proposal, dict) or proposal.get("requested_action") != V2_CREATE_ACTION:
            raise ValueError("decision accepts CREATE proposals only")
        if args.decision not in {"APPROVE", "REJECT", "BLOCK", "REQUIRES_REVIEW"}:
            raise ValueError("decision must be APPROVE, REJECT, BLOCK, or REQUIRES_REVIEW")
        if not isinstance(args.actor, str) or not args.actor.strip():
            raise ValueError("actor must be non-empty")
        if not isinstance(args.text, str) or not args.text.strip():
            raise ValueError("decision text must be non-empty")
        policy = load_json(policy_path)
        if not isinstance(policy, dict):
            raise ValueError("policy must be an object")  # noqa: TRY004 - ValueError is the established CLI error contract
        policy_sha = sha256_file(policy_path)
        if policy.get("schema") != V2_POLICY_SCHEMA:
            raise ValueError("policy schema must be skill-policy-1")
        if policy.get("allow_low_risk_auto_approval") is True or policy.get("allow_automatic_merge") is True:
            raise ValueError("automatic approval or merge is forbidden in V2.0")
        proposal_sha = sha256_file(proposal_dir / "proposal.json")
        evidence_sha = v2_evidence_hash(proposal_dir)
        
        # REQ-A2/A3: For APPROVE, enforce re-evaluation on drift and HIGH findings block
        evaluated_skill_sha = None
        current_skill_sha = None
        high_findings = 0
        if args.decision == "APPROVE":
            # Load evaluation record to get evaluated_skill_sha256
            validation_path = proposal_dir / "validation.json"
            if not validation_path.is_file():
                raise ValueError("missing validation.json; run evaluate-proposal first")
            validation = load_json(validation_path)
            evaluated_skill_sha = validation.get("evaluated_skill_sha256")
            if not evaluated_skill_sha:
                raise ValueError("validation record missing evaluated_skill_sha256; re-run evaluate-proposal")
            # Recompute current skill hash
            skill_path = proposal_dir / "SKILL.md"
            if not skill_path.is_file():
                raise ValueError("quarantine record missing SKILL.md")
            current_skill_sha = sha256_file(skill_path)
            # Drift check: fail closed if hashes differ
            if current_skill_sha != evaluated_skill_sha:
                return v2_report({"schema": "skills-catalog-decision-1", "status": "FAIL", "message": "skill content drift detected", "errors": [f"evaluated_skill_sha256={evaluated_skill_sha}, current_skill_sha256={current_skill_sha}; re-evaluation required"]}, args.output)
            # HIGH findings block: run scan-security on current bytes
            scan_report = scan_security_tree(proposal_dir)
            high_findings = sum(1 for f in scan_report.get("findings", []) if f.get("severity") == "high")
            if high_findings > 0:
                return v2_report({"schema": "skills-catalog-decision-1", "status": "FAIL", "message": f"security gate: {high_findings} HIGH finding(s) block APPROVE", "errors": ["run scan-security with --fail-on high to review"]}, args.output)
        
        decision = {
            "schema": "skill-decision-1",
            "decision_id": f"{proposal_dir.name}-{uuid.uuid4().hex}",
            "proposal_id": proposal["proposal_id"],
            "decision": args.decision,
            "actor": args.actor.strip(),
            "proposal_sha256": proposal_sha,
            "policy_sha256": policy_sha,
            "evidence_sha256": evidence_sha,
            "decision_text": args.text.strip(),
            "decided_at_utc": v2_timestamp(),
        }
        # REQ-A4: for non-APPROVE decisions on drifted hashes, log both hashes
        if args.decision != "APPROVE" and evaluated_skill_sha and current_skill_sha and current_skill_sha != evaluated_skill_sha:
            decision["evaluated_skill_sha256"] = evaluated_skill_sha
            decision["current_skill_sha256"] = current_skill_sha
        elif args.decision == "APPROVE":
            decision["evaluated_skill_sha256"] = evaluated_skill_sha
            decision["current_skill_sha256"] = current_skill_sha
            decision["security_high_findings"] = high_findings
        
        decision_path.parent.mkdir(parents=True, exist_ok=True)
        decision_sha = v2_write_json(decision_path, decision)
        canonical_decision = governance_root / "decisions" / f"{proposal_dir.name}.json"
        if decision_path.resolve() != canonical_decision.resolve():
            canonical_decision.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(decision_path, canonical_decision)
        status = {"APPROVE": "APPROVED", "REJECT": "REJECTED", "BLOCK": "BLOCKED", "REQUIRES_REVIEW": "REQUIRES_REVIEW"}[args.decision]
        event = v2_append_event(governance_root, proposal["proposal_id"], "EVALUATING", status, args.actor, "decide", [proposal_sha, policy_sha, evidence_sha], [str(canonical_decision)])
        return v2_report({"schema": "skills-catalog-decision-1", "status": status, "proposal_id": proposal["proposal_id"], "decision": args.decision, "decision_sha256": decision_sha, "event_no": event["event_no"], "decision_path": str(canonical_decision.resolve())}, None)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return v2_report({"schema": "skills-catalog-decision-1", "status": "FAIL", "message": str(exc), "errors": [str(exc)]}, args.output)


def v2_load_decision(path: Path, proposal_dir: Path, policy_path: Path) -> tuple[dict[str, Any], str]:
    decision = load_json(path)
    if not isinstance(decision, dict):
        raise ValueError("decision must be an object")  # noqa: TRY004 - ValueError is the established CLI error contract
    if decision.get("schema") != "skill-decision-1" or decision.get("decision") != "APPROVE":
        raise ValueError("activation requires a skill-decision-1 APPROVE record")
    if decision.get("proposal_id") != proposal_dir.name:
        raise ValueError("decision proposal_id does not match quarantine proposal")
    if decision.get("proposal_sha256") != sha256_file(proposal_dir / "proposal.json"):
        raise ValueError("decision proposal hash does not match quarantined proposal")
    if decision.get("policy_sha256") != sha256_file(policy_path):
        raise ValueError("decision policy hash does not match current policy")
    if decision.get("evidence_sha256") != v2_evidence_hash(proposal_dir):
        raise ValueError("decision evidence hash does not match current evaluation artifacts")
    for key in ("actor", "decision_text", "decision_id"):
        if not isinstance(decision.get(key), str) or not decision[key].strip():
            raise ValueError(f"decision {key} is missing")
    return decision, sha256_file(path)


def cmd_activate(args: argparse.Namespace) -> int:
    proposal_dir = v2_path(args.proposal)
    governance_root = v2_path(args.root)
    active_root = v2_path(args.active_root)
    policy_path = v2_path(args.policy)
    decision_path = v2_path(args.decision)
    published_target: Path | None = None
    published_hash: str | None = None
    created_record_path: Path | None = None
    proposal_id = proposal_dir.name
    if not args.apply or not args.yes:
        return v2_report({"schema": "skills-catalog-activation-1", "status": "FAIL", "message": "activation requires both --apply and --yes", "errors": ["activation requires both --apply and --yes"]}, args.output)
    try:
        governance_root, active_root = v2_validate_roots(governance_root, active_root)
        proposal = load_json(proposal_dir / "proposal.json")
        if not isinstance(proposal, dict) or proposal.get("requested_action") != V2_CREATE_ACTION:
            raise ValueError("V2.0 activation accepts CREATE proposals only")
        target = proposal.get("target", {})
        if v2_path(target.get("active_root")) != active_root:
            raise ValueError("proposal active root does not match --active-root")
        target_name = target.get("name")
        if not isinstance(target_name, str) or not G0_NAME_RE.fullmatch(target_name):
            raise ValueError("proposal target name is invalid")
        target_path = active_root / target_name
        if target_path.exists() or target_path.is_symlink():
            raise ValueError(f"activation target already exists: {target_path}")
        published_target = target_path
        decision, decision_sha = v2_load_decision(decision_path, proposal_dir, policy_path)
        snapshot_id = f"{proposal_dir.name}-{uuid.uuid4().hex}"
        snapshot_dir = governance_root / "snapshots" / snapshot_id
        snapshot_dir.mkdir(parents=True, exist_ok=False)
        snapshot = {
            "schema": "skill-snapshot-1",
            "snapshot_id": snapshot_id,
            "proposal_id": proposal["proposal_id"],
            "active_root": str(active_root),
            "active_path": str(target_path),
            "target_existed": False,
            "target_sha256": None,
            "decision_sha256": decision_sha,
            "policy_sha256": sha256_file(policy_path),
            "scope": "affected target path plus governance metadata",
            "created_at_utc": v2_timestamp(),
        }
        snapshot_sha = v2_write_json(snapshot_dir / "snapshot.json", snapshot)
        stage = governance_root / f".activation-{proposal_dir.name}-{uuid.uuid4().hex}"
        stage.mkdir(parents=True, exist_ok=False)
        try:
            shutil.copy2(proposal_dir / "SKILL.md", stage / "SKILL.md")
            if target_path.exists() or target_path.is_symlink():
                raise ValueError(f"activation target appeared during staging: {target_path}")
            active_root.mkdir(parents=True, exist_ok=True)
            stage.rename(target_path)
        except Exception:
            shutil.rmtree(stage, ignore_errors=True)
            raise
        published_sha = sha256_file(target_path / "SKILL.md")
        published_hash = published_sha
        if published_sha != proposal.get("skill_sha256"):
            shutil.rmtree(target_path, ignore_errors=True)
            published_target = None
            raise ValueError("published skill hash does not match proposal")
        active_record = {
            "schema": "skill-active-record-1",
            "proposal_id": proposal["proposal_id"],
            "active_root": str(active_root),
            "active_path": str(target_path),
            "skill_sha256": published_sha,
            "snapshot_id": snapshot_id,
            "snapshot_sha256": snapshot_sha,
            "decision_sha256": decision_sha,
            "policy_sha256": sha256_file(policy_path),
            "status": "ACTIVE",
            "activated_at_utc": v2_timestamp(),
        }
        record_path = governance_root / "active-records" / f"{proposal_dir.name}.json"
        record_path.parent.mkdir(parents=True, exist_ok=True)
        created_record_path = record_path
        v2_write_json(record_path, active_record)
        archive_dir = governance_root / "archive" / proposal_dir.name
        archive_dir.mkdir(parents=True, exist_ok=False)
        shutil.copy2(target_path / "SKILL.md", archive_dir / "SKILL.md")
        event = v2_append_event(governance_root, proposal["proposal_id"], "APPROVED", "ACTIVE", decision["actor"], "activate", [proposal["skill_sha256"], decision_sha, snapshot_sha], [str(record_path), str(snapshot_dir / "snapshot.json")])
        return v2_report({"schema": "skills-catalog-activation-1", "status": "ACTIVE", "proposal_id": proposal["proposal_id"], "active_path": str(target_path.resolve()), "active_record": str(record_path.resolve()), "snapshot_id": snapshot_id, "snapshot_sha256": snapshot_sha, "event_no": event["event_no"]}, args.output)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        cleanup = "NOT_PUBLISHED"
        if published_target is not None and published_target.exists() and published_target.is_dir():
            try:
                current = published_target / "SKILL.md"
                if published_hash and current.is_file() and sha256_file(current) == published_hash:
                    shutil.rmtree(published_target)
                    cleanup = "REMOVED_PUBLISHED_TARGET"
                else:
                    cleanup = "CLEANUP_BLOCKED_TARGET_CHANGED"
            except OSError:
                cleanup = "CLEANUP_FAILED"
        if created_record_path is not None and created_record_path.is_file():
            try:
                created_record_path.unlink()
                cleanup = f"{cleanup}; REMOVED_ACTIVE_RECORD"
            except OSError:
                cleanup = f"{cleanup}; ACTIVE_RECORD_CLEANUP_FAILED"
        try:
            v2_append_event(governance_root, proposal_id, "ACTIVATING", "QUARANTINED", "local-user", "activate", [published_hash or ""], [cleanup])
        except OSError:
            cleanup = f"{cleanup}; JOURNAL_FAILED"
        failure_record = governance_root / "run-record" / f"{proposal_id}-activation-failed.json"
        try:
            v2_write_json(failure_record, {"schema": "skills-catalog-activation-failure-1", "status": "ACTIVATION_FAILED", "proposal_id": proposal_id, "published_hash": published_hash, "cleanup": cleanup, "error": str(exc), "created_at_utc": v2_timestamp()})
        except OSError:
            cleanup = f"{cleanup}; FAILURE_RECORD_FAILED"
        return v2_report({"schema": "skills-catalog-activation-1", "status": "ACTIVATION_FAILED", "message": str(exc), "cleanup": cleanup, "published_hash": published_hash, "failure_record": str(failure_record), "errors": [str(exc)]}, args.output)


def cmd_verify_active(args: argparse.Namespace) -> int:
    try:
        record_path = v2_path(args.record)
        record = load_json(record_path)
        if not isinstance(record, dict) or record.get("schema") != "skill-active-record-1":
            raise ValueError("invalid active record")
        active_path = Path(record["active_path"])
        errors: list[str] = []
        if not active_path.is_dir() or not (active_path / "SKILL.md").is_file():
            errors.append("active skill path is missing")
        else:
            if sha256_file(active_path / "SKILL.md") != record.get("skill_sha256"):
                errors.append("active skill hash drift detected")
        status = "CLEAN" if not errors else "DRIFTED"
        return v2_report({"schema": "skills-catalog-active-check-1", "status": status, "record": str(record_path), "active_path": str(active_path), "errors": errors}, args.output)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return v2_report({"schema": "skills-catalog-active-check-1", "status": "FAIL", "message": str(exc), "errors": [str(exc)]}, args.output)


def cmd_rollback(args: argparse.Namespace) -> int:
    record_path = v2_path(args.record)
    governance_root = v2_path(args.root)
    if not args.apply or not args.yes:
        return v2_report({"schema": "skills-catalog-rollback-1", "status": "FAIL", "message": "rollback requires both --apply and --yes", "errors": ["rollback requires both --apply and --yes"]}, args.output)
    try:
        record = load_json(record_path)
        if not isinstance(record, dict) or record.get("schema") != "skill-active-record-1":
            raise ValueError("invalid active record")
        active_path = Path(record["active_path"])
        if not active_path.is_dir() or not (active_path / "SKILL.md").is_file():
            raise ValueError("active path is missing; rollback cannot verify drift")
        current_sha = sha256_file(active_path / "SKILL.md")
        if current_sha != record.get("skill_sha256"):
            raise ValueError("active skill drift detected; refusing rollback")
        snapshot_dir = governance_root / "snapshots" / record["snapshot_id"]
        snapshot = load_json(snapshot_dir / "snapshot.json")
        if snapshot.get("target_existed") is not False:
            raise ValueError("unsupported snapshot target state")
        archive_dir = governance_root / "archive" / record["proposal_id"]
        archive_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(active_path / "SKILL.md", archive_dir / "SKILL.md")
        shutil.rmtree(active_path)
        record["status"] = "RESTORED"
        record["restored_at_utc"] = v2_timestamp()
        v2_write_json(record_path, record)
        event = v2_append_event(governance_root, record["proposal_id"], "ROLLBACK_PENDING", "RESTORED", "local-user", "rollback", [record["skill_sha256"], record.get("snapshot_sha256", "")], [str(record_path), str(archive_dir / "SKILL.md")])
        return v2_report({"schema": "skills-catalog-rollback-1", "status": "RESTORED", "proposal_id": record["proposal_id"], "record": str(record_path), "event_no": event["event_no"]}, args.output)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return v2_report({"schema": "skills-catalog-rollback-1", "status": "FAIL", "message": str(exc), "errors": [str(exc)]}, args.output)


# --- Security & Supply Chain Scanner (V2.1, OWASP-aligned) -----------------
#
# Static heuristic analysis only. Skill content is NEVER executed by this
# module. Findings are advisory evidence for human decisions; HIGH findings
# are intended to fail closed in downstream gates.

SECURITY_SCAN_SCHEMA = "skills-catalog-security-audit-1"
SECURITY_MAX_FILE_BYTES = 1_000_000
SECURITY_TEXT_SUFFIXES = {
    ".md", ".markdown", ".txt", ".json", ".yaml", ".yml", ".toml", ".py",
    ".sh", ".bash", ".ps1", ".js", ".ts", ".rb", ".cfg", ".ini", ".skill",
}

SECURITY_RULES: tuple[dict[str, Any], ...] = (
    {
        "id": "SEC-001",
        "rule": "pipe-to-shell-install",
        "severity": "high",
        "owasp_ref": "OWASP Secure Agent Playbook — Supply Chain / A06:2021",
        "pattern": re.compile(r"curl\s+[^\n|]*\|\s*(ba)?sh|wget\s+[^\n|]*\|\s*(ba)?sh|irm\s+\S+\s*\|\s*iex", re.IGNORECASE),
        "description": "Downloads remote content and pipes it directly into a shell interpreter.",
    },
    {
        "id": "SEC-002",
        "rule": "destructive-recursive-delete",
        "severity": "high",
        "owasp_ref": "OWASP Secure Agent Playbook — Dangerous Commands",
        "pattern": re.compile(r"rm\s+(-[a-zA-Z]*[rf][a-zA-Z]*\s+)+/?(\$\{?[A-Za-z_][A-Za-z0-9_]*}?/)?\s*$|rm\s+-rf\s+/(?:\s|$)|Remove-Item\s+[^\n]*-Recurse\s+[^\n]*-Force\s+/ ", re.IGNORECASE),
        "description": "Recursive force deletion targeting filesystem root or variable-rooted paths.",
    },
    {
        "id": "SEC-003",
        "rule": "credential-exfiltration-endpoint",
        "severity": "high",
        "owasp_ref": "OWASP Secure Agent Playbook — Data Exfiltration",
        "pattern": re.compile(r"(curl|wget|Invoke-WebRequest|fetch|requests\.post)[^\n]*(env|printenv|\.env|AWS_ACCESS_KEY|SECRET|TOKEN|PASSWORD)", re.IGNORECASE),
        "description": "Network command combined with credential/environment references (possible secret exfiltration).",
    },
    {
        "id": "SEC-004",
        "rule": "eval-exec-usage",
        "severity": "medium",
        "owasp_ref": "OWASP Secure Agent Playbook — Code Injection",
        "pattern": re.compile(r"\b(eval|exec)\s*\(|Invoke-Expression\b|iex\b", re.IGNORECASE),
        "description": "Dynamic code evaluation construct; review whether input is attacker-influenced.",
    },
    {
        "id": "SEC-005",
        "rule": "unpinned-remote-fetch",
        "severity": "medium",
        "owasp_ref": "OWASP Secure Agent Playbook — Supply Chain / Dependency Pinning",
        "pattern": re.compile(r"npx\s+(?!@?[A-Za-z0-9.-]+@[A-Za-z0-9.~^_+-])[A-Za-z0-9@./-]+|pip\s+install\s+(?![-\w]+\s*==\s*\d)[^\n|&;]+", re.IGNORECASE),
        "description": "Package fetch without an explicit version pin; supply-chain integrity cannot be verified.",
    },
    {
        "id": "SEC-006",
        "rule": "prompt-injection-override",
        "severity": "medium",
        "owasp_ref": "OWASP LLM Top-10 — Prompt Injection",
        "pattern": re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions|disregard\s+(your\s+)?(system\s+)?prompt|you\s+are\s+now\s+(a|an)\s+", re.IGNORECASE),
        "description": "Instruction-override phrasing typical of prompt injection payloads.",
    },
    {
        "id": "SEC-007",
        "rule": "hidden-exfiltration-tag",
        "severity": "low",
        "owasp_ref": "OWASP LLM Top-10 — Sensitive Information Disclosure",
        "pattern": re.compile(r"<system>|<\|im_start\|>|###\s*system:?|AI:\s*SYSTEM\s*OVERRIDE", re.IGNORECASE),
        "description": "Markup resembling chat/system role delimiters embedded in skill content.",
    },
)

SECURITY_SEVERITY_ORDER = {"none": [], "low": ["high", "medium", "low"], "medium": ["high", "medium"], "high": ["high"]}


def scan_security_tree(root: Path) -> dict[str, Any]:
    """Statically scan a directory tree for dangerous content patterns."""
    if not root.is_dir():
        raise ValueError(f"scan root is not a directory: {root}")
    findings: list[dict[str, Any]] = []
    files_scanned = 0
    files_skipped: list[str] = []
    for item in sorted(root.rglob("*"), key=lambda p: p.relative_to(root).as_posix()):
        rel = item.relative_to(root).as_posix()
        if item.is_symlink():
            files_skipped.append({"path": rel, "reason": "symlink"})
            continue
        if item.is_dir() or not item.is_file():
            continue
        if item.suffix.lower() not in SECURITY_TEXT_SUFFIXES:
            files_skipped.append({"path": rel, "reason": "non-text-suffix"})
            continue
        try:
            data = item.read_bytes()
        except OSError as exc:
            files_skipped.append({"path": rel, "reason": f"unreadable: {exc}"})
            continue
        if len(data) > SECURITY_MAX_FILE_BYTES:
            files_skipped.append({"path": rel, "reason": "oversize"})
            continue
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            files_skipped.append({"path": rel, "reason": "binary-or-non-utf8"})
            continue
        files_scanned += 1
        for line_no, line in enumerate(text.splitlines(), start=1):
            for rule_def in SECURITY_RULES:
                match = rule_def["pattern"].search(line)
                if match:
                    snippet = match.group(0)
                    redacted = snippet if len(snippet) <= 120 else snippet[:117] + "..."
                    findings.append({
                        "id": rule_def["id"],
                        "severity": rule_def["severity"],
                        "path": rel,
                        "line": line_no,
                        "column": match.start() + 1,
                        "rule": rule_def["rule"],
                        "description": rule_def["description"],
                        "owasp_ref": rule_def["owasp_ref"],
                        "match": redacted,
                    })
    return {
        "scanned_root": str(root),
        "tree_sha256": tree_digest(root),
        "files_scanned": files_scanned,
        "files_skipped": files_skipped,
        "findings": findings,
        "heuristic_notice": (
            "Static heuristic scan only; skill content was never executed. "
            "A PASS does not prove absence of malicious behavior."
        ),
    }


# --- grade-skill (V2.2 Phase 3) ---------------------------------------------
#
# Static fixture-based grader. NO LLM execution. Skills are evaluated by:
# - expect_exact_output: byte-comparison against a fenced 'output:' block in SKILL.md
#   (normalization: strip trailing whitespace per line, CRLF->LF, exact otherwise)
# - expected_tools: non-empty intersection AND all listed tools present in frontmatter allowed-tools
#
# Fixtures conform to schemas/skill-fixture.schema.json
# Grading is deterministic: same inputs -> byte-identical reports.

GRADE_SCHEMA = "skills-catalog-grade-1"
OUTPUT_FENCE_RE = re.compile(r"^(`{3,}|~{3,})\s*(\w+)?\s*$", re.MULTILINE)

def extract_output_block(skill_text: str) -> str | None:
    """Extract the first fenced block whose info string contains 'output'.
    
    Grammar:
    - Only ``` and ~~~ fence markers recognized
    - Output block = fence whose info string contains 'output' token
    - First matching block wins
    - Unclosed fences = explicit FAIL
    - Nested fences = explicit FAIL (any fence inside an open fence with different marker)
    - No match = explicit FAIL
    """
    lines = skill_text.splitlines()
    in_fence = False
    fence_marker = None
    fence_info = ""
    content_lines = []
    found_output_block = False
    output_content = None
    
    for i, line in enumerate(lines):
        m = OUTPUT_FENCE_RE.match(line)
        if m:
            marker = m.group(1)
            info = m.group(2) or ""
            if not in_fence:
                # Opening fence
                in_fence = True
                fence_marker = marker
                fence_info = info.lower()
                content_lines = []
                if "output" in fence_info:
                    found_output_block = True
            else:
                # Inside a fence - check if this closes (same marker, empty info) or nests
                if marker == fence_marker and not info:
                    # Same marker with empty info = closing fence
                    in_fence = False
                    if found_output_block and output_content is None:
                        output_content = "\n".join(content_lines)
                    found_output_block = False
                    fence_marker = None
                    fence_info = ""
                    content_lines = []
                else:
                    # Different marker or same marker with info = nested fence
                    raise ValueError("nested_fence")
        elif in_fence:
            content_lines.append(line)
    
    if in_fence and found_output_block:
        raise ValueError("unclosed_fence")
    
    if output_content is None:
        raise ValueError("no_output_block")
    
    return output_content


def normalize_text(text: str) -> str:
    """Apply normalization per REQ-B2: strip trailing whitespace per line, CRLF->LF."""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").splitlines()
    return "\n".join(line.rstrip() for line in lines)


def load_fixtures(path: Path) -> list[dict[str, Any]]:
    """Load fixture(s) from file or directory."""
    fixtures = []
    if path.is_file():
        data = load_json(path)
        if isinstance(data, list):
            fixtures.extend(data)
        else:
            fixtures.append(data)
    elif path.is_dir():
        for item in sorted(path.glob("*.json")):
            data = load_json(item)
            if isinstance(data, list):
                fixtures.extend(data)
            else:
                fixtures.append(data)
    return fixtures


def validate_fixture(fixture: dict[str, Any]) -> list[str]:
    """Validate fixture against schema. Returns list of error strings (empty = valid)."""
    errors = []
    if not isinstance(fixture.get("fixture_id"), str) or not fixture["fixture_id"]:
        errors.append("fixture_id missing or empty")
    if not isinstance(fixture.get("input"), dict) or not isinstance(fixture["input"].get("prompt"), str):
        errors.append("input.prompt missing or not a string")
    has_output = "expect_exact_output" in fixture
    has_tools = "expected_tools" in fixture
    if has_output and has_tools:
        errors.append("both expect_exact_output and expected_tools present; exactly one required")
    if not has_output and not has_tools:
        errors.append("neither expect_exact_output nor expected_tools present; exactly one required")
    if has_tools:
        tools = fixture["expected_tools"]
        if not isinstance(tools, list) or not all(isinstance(t, str) for t in tools):
            errors.append("expected_tools must be array of strings")
        if len(tools) == 0:
            errors.append("expected_tools must have at least one element")
    if has_output and not isinstance(fixture["expect_exact_output"], str):
        errors.append("expect_exact_output must be a string")
    if "case_sensitive" in fixture and not isinstance(fixture["case_sensitive"], bool):
        errors.append("case_sensitive must be boolean")
    return errors


def get_skill_output_block(skill_path: Path) -> str:
    """Extract output block from SKILL.md; raises ValueError with reason on failure."""
    text = skill_path.read_text(encoding="utf-8")
    return extract_output_block(text)


def parse_frontmatter_all(text: str) -> dict[str, Any]:
    """Parse all frontmatter fields (not just name/description). Supports YAML-like lists."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    end = next((index for index, line in enumerate(lines[1:], 1) if line.strip() == "---"), None)
    if end is None:
        raise ValueError("frontmatter opening delimiter has no closing delimiter")

    values: dict[str, Any] = {}
    current_key: str | None = None
    continuation: list[str] = []

    def finish_value() -> None:
        if current_key is None:
            return
        value = values.get(current_key, "")
        if continuation:
            marker = value.strip()
            parts = [part.strip() for part in continuation]
            if marker in {">", ">-", ">+"}:
                value = " ".join(parts)
            elif marker in {"|", "|-", "|+"}:
                value = "\n".join(parts)
            else:
                value = " ".join([value.rstrip(), *parts]).strip()
        # Try to parse as YAML list if it looks like one (whether or not continuation)
        value = values.get(current_key, "")
        if isinstance(value, str) and value.startswith("[") and value.endswith("]"):
            # Parse [a, b, c] -> ["a", "b", "c"]
            inner = value[1:-1].strip()
            if inner:
                value = [v.strip() for v in inner.split(",")]
            else:
                value = []
        values[current_key] = value

    for line in lines[1:end]:
        if not line.strip():
            if current_key is not None:
                continuation.append("")
            continue

        if line[0].isspace():
            if current_key is None:
                raise ValueError(f"malformed frontmatter line: {line}")
            continuation.append(line.strip())
            continue

        match = re.match(r"^([A-Za-z_][\w.-]*)\s*:\s*(.*?)\s*$", line)
        if match:
            finish_value()
            current_key = match.group(1)
            continuation = []
            values[current_key] = match.group(2)
            continue

        if line.lstrip().startswith("-"):
            if current_key is not None:
                continuation.append(line.strip())
            continue

        raise ValueError(f"malformed frontmatter line: {line}")

    finish_value()
    return values


def get_skill_allowed_tools(skill_path: Path) -> set[str]:
    """Extract allowed-tools from SKILL.md frontmatter."""
    text = skill_path.read_text(encoding="utf-8")
    fm = parse_frontmatter_all(text)
    if not fm:
        return set()
    allowed = fm.get("allowed-tools")
    if not allowed:
        return set()
    if isinstance(allowed, str):
        return {allowed.strip()}
    if isinstance(allowed, list):
        return {str(t).strip() for t in allowed}
    return set()


def cmd_grade_skill(args: argparse.Namespace) -> int:
    report: dict[str, Any] = {"schema": GRADE_SCHEMA}
    try:
        skill_dir = Path(args.path)
        if not skill_dir.is_dir():
            raise ValueError(f"skill path is not a directory: {skill_dir}")
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            raise ValueError(f"skill directory missing SKILL.md: {skill_dir}")
        
        fixtures = load_fixtures(Path(args.fixtures))
        if not fixtures:
            raise ValueError("no fixtures loaded")
        
        # Validate all fixtures first
        for fx in fixtures:
            errors = validate_fixture(fx)
            if errors:
                raise ValueError(f"fixture {fx.get('fixture_id', '?')}: {', '.join(errors)}")
        
        # Pre-extract skill artifacts
        try:
            skill_output = get_skill_output_block(skill_md)
        except ValueError as e:
            # FAIL reason will be recorded per-fixture
            skill_output = None
            skill_output_error = str(e)
        else:
            skill_output_error = None
        
        skill_tools = get_skill_allowed_tools(skill_md)
        
        skill_sha = sha256_file(skill_md)
        
        results = []
        passed = 0
        failed = 0
        
        for fx in fixtures:
            fx_id = fx["fixture_id"]
            case_sensitive = fx.get("case_sensitive", True)
            
            if "expect_exact_output" in fx:
                # Exact output comparison
                expected = fx["expect_exact_output"]
                if skill_output_error:
                    results.append({"fixture_id": fx_id, "result": "fail", "reason": f"skill_output_extraction_failed: {skill_output_error}"})
                    failed += 1
                    continue
                
                if case_sensitive:
                    actual_norm = normalize_text(skill_output)
                    expected_norm = normalize_text(expected)
                else:
                    actual_norm = normalize_text(skill_output).lower()
                    expected_norm = normalize_text(expected).lower()
                
                if actual_norm == expected_norm:
                    results.append({"fixture_id": fx_id, "result": "pass", "reason": None})
                    passed += 1
                else:
                    results.append({"fixture_id": fx_id, "result": "fail", "reason": "output_mismatch"})
                    failed += 1
                    
            else:
                # expected_tools comparison
                expected_tools = set(fx["expected_tools"])
                if not skill_tools:
                    results.append({"fixture_id": fx_id, "result": "fail", "reason": "no_tools_declared"})
                    failed += 1
                    continue
                
                if not expected_tools & skill_tools:
                    results.append({"fixture_id": fx_id, "result": "fail", "reason": "empty_intersection"})
                    failed += 1
                    continue
                
                if not expected_tools <= skill_tools:
                    missing = expected_tools - skill_tools
                    results.append({"fixture_id": fx_id, "result": "fail", "reason": f"missing_tools: {sorted(missing)}"})
                    failed += 1
                    continue
                
                results.append({"fixture_id": fx_id, "result": "pass", "reason": None})
                passed += 1
        
        verdict = "GO" if failed == 0 else "NO-GO"
        
        report.update({
            "skill_sha256": skill_sha,
            "verdict": verdict,
            "fixtures": results,
            "summary": {"passed": passed, "failed": failed},
            "labeling": {
                "scope": "structural grading only",
                "behavioral_claims": "advisory"
            }
        })
        report["status"] = "PASS" if verdict == "GO" else "FAIL"
        return emit(report, args.output)
        
    except (OSError, ValueError, KeyError, TypeError) as exc:
        report.update({"status": "FAIL", "message": str(exc), "errors": [str(exc)]})
        return emit(report, args.output)


def cmd_scan_security(args: argparse.Namespace) -> int:
    fail_on = args.fail_on
    if fail_on not in SECURITY_SEVERITY_ORDER:
        return fail(f"invalid --fail-on value: {fail_on}")
    report: dict[str, Any] = {"schema": SECURITY_SCAN_SCHEMA}
    try:
        result = scan_security_tree(Path(args.path))
    except (OSError, ValueError) as exc:
        report.update({"status": "FAIL", "message": str(exc), "errors": [str(exc)]})
        return emit(report, args.output)
    blocking = set(SECURITY_SEVERITY_ORDER[fail_on])
    hits = [f for f in result["findings"] if f["severity"] in blocking]
    status = "FAIL" if hits else "PASS"
    report.update(result)
    report["fail_on"] = fail_on
    report["blocking_findings"] = len(hits)
    report["status"] = status
    return emit(report, args.output)


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    detect = sub.add_parser("detect-skills")
    detect.add_argument("--stores", nargs="+", action="append", metavar="PATH")
    detect.add_argument("--usage-dir", help="optional dir containing .usage.json for usage enrichment")
    detect.add_argument("--output")
    detect.set_defaults(func=cmd_detect_skills)
    grouping = sub.add_parser("detect-groups")
    grouping.add_argument("--inventory", required=True)
    grouping.add_argument("--threshold", type=float, default=0.30)
    grouping.add_argument("--overlap-threshold", type=float, default=OVERLAP_THRESHOLD)
    grouping.add_argument("--max-group-size", type=int, default=8)
    grouping.add_argument("--output")
    grouping.set_defaults(func=cmd_detect_groups)
    package = sub.add_parser("check-package")
    package.add_argument("--root", default=".")
    package.add_argument("--output")
    package.set_defaults(func=cmd_check_package)
    install = sub.add_parser("install")
    install.add_argument("--target", help="harness name or existing skills directory")
    install.add_argument("--yes", action="store_true", help="replace existing installs after a timestamped backup")
    install.add_argument("--output")
    install.set_defaults(func=cmd_install)
    manifest = sub.add_parser("validate-manifest")
    manifest.add_argument("--root", required=True)
    manifest.add_argument("--manifest", required=True)
    manifest.add_argument("--output")
    manifest.set_defaults(func=cmd_validate_manifest)
    preflight = sub.add_parser("preflight-moves")
    preflight.add_argument("--root", required=True)
    preflight.add_argument("--archive", required=True)
    preflight.add_argument("--manifest", required=True)
    preflight.add_argument("--plan", required=True)
    preflight.set_defaults(func=cmd_preflight_moves)
    apply = sub.add_parser("apply-moves")
    apply.add_argument("--plan", required=True)
    apply.add_argument("--journal")
    apply.add_argument("--apply", action="store_true")
    apply.add_argument("--yes", action="store_true")
    apply.add_argument(
        "--recover-stale-lock",
        action="store_true",
        help="remove the move lock only when its recorded PID is no longer alive",
    )
    apply.set_defaults(func=cmd_apply_moves)
    loss = sub.add_parser("loss-check")
    loss.add_argument("--draft", required=True)
    loss.add_argument("--source", action="append", required=True)
    loss.add_argument("--min-overlap", type=float, default=0.35)
    loss.add_argument("--output")
    loss.set_defaults(func=cmd_loss_check)
    council_verdict = sub.add_parser("validate-council-verdict")
    council_verdict.add_argument("--verdict", required=True)
    council_verdict.add_argument("--output")
    council_verdict.set_defaults(func=cmd_validate_council_verdict)
    approval = sub.add_parser("verify-approval")
    approval.add_argument("--draft", required=True)
    approval.add_argument("--approval", required=True)
    approval.add_argument("--loss-report")
    approval.add_argument("--output")
    approval.set_defaults(func=cmd_verify_approval)
    master_check = sub.add_parser("check-master")
    master_check.add_argument("--draft", required=True)
    master_check.add_argument("--dir", help="expected directory name (default: draft parent dir name)")
    master_check.add_argument("--output")
    master_check.set_defaults(func=cmd_check_master)
    golden = sub.add_parser("golden-gate")
    golden.add_argument("--manifest", required=True)
    golden.add_argument("--workdir", required=True)
    golden.add_argument("--output")
    golden.set_defaults(func=cmd_golden_gate)
    bench = sub.add_parser("benchmark")
    bench.add_argument("--bundle", required=True)
    bench.add_argument("--output")
    bench.set_defaults(func=cmd_benchmark)
    repair = sub.add_parser("repair")
    repair.add_argument("--loss-report", required=True)
    repair.add_argument("--draft", required=True)
    repair.add_argument("--source", action="append", default=[])
    repair.add_argument("--allow-draft-change", action="store_true")
    repair.add_argument("--output")
    repair.set_defaults(func=cmd_repair)
    v2_capture = sub.add_parser("capture-hermes")
    v2_capture.add_argument("--skill-dir", required=True)
    v2_capture.add_argument("--usage", required=True)
    v2_capture.add_argument("--metadata", required=True)
    v2_capture.add_argument("--active-root", required=True)
    v2_capture.add_argument("--output", required=True, help="new capture bundle directory")
    v2_capture.add_argument("--output-report")
    v2_capture.set_defaults(func=cmd_capture_hermes)
    v2_intake = sub.add_parser("intake")
    v2_intake.add_argument("--skill", required=True)
    v2_intake.add_argument("--provenance", required=True)
    v2_intake.add_argument("--root", required=True)
    v2_intake.add_argument("--active-root", required=True)
    v2_intake.add_argument("--actor", default="local-user")
    v2_intake.add_argument("--output")
    v2_intake.set_defaults(func=cmd_intake)
    v2_inspect = sub.add_parser("inspect-proposal")
    v2_inspect.add_argument("--proposal", required=True)
    v2_inspect.add_argument("--output")
    v2_inspect.set_defaults(func=cmd_inspect_proposal)
    v2_policy = sub.add_parser("check-policy")
    v2_policy.add_argument("--policy", required=True)
    v2_policy.add_argument("--output")
    v2_policy.set_defaults(func=cmd_check_policy)
    v2_evaluate = sub.add_parser("evaluate-proposal")
    v2_evaluate.add_argument("--proposal", required=True)
    v2_evaluate.add_argument("--root", required=True)
    v2_evaluate.add_argument("--active-root", required=True)
    v2_evaluate.add_argument("--actor", default="local-user")
    v2_evaluate.add_argument("--output")
    v2_evaluate.set_defaults(func=cmd_evaluate_proposal)
    v2_impact = sub.add_parser("impact-report")
    v2_impact.add_argument("--proposal", required=True)
    v2_impact.add_argument("--active-root", required=True)
    v2_impact.add_argument("--scan-root", action="append", default=[])
    v2_impact.add_argument("--output")
    v2_impact.set_defaults(func=cmd_impact_report)
    v2_decide = sub.add_parser("decide")
    v2_decide.add_argument("--proposal", required=True)
    v2_decide.add_argument("--root", required=True)
    v2_decide.add_argument("--policy", required=True)
    v2_decide.add_argument("--decision", required=True)
    v2_decide.add_argument("--actor", required=True)
    v2_decide.add_argument("--text", required=True)
    v2_decide.add_argument("--output")
    v2_decide.set_defaults(func=cmd_decide)
    v2_activate = sub.add_parser("activate")
    v2_activate.add_argument("--proposal", required=True)
    v2_activate.add_argument("--root", required=True)
    v2_activate.add_argument("--active-root", required=True)
    v2_activate.add_argument("--policy", required=True)
    v2_activate.add_argument("--decision", required=True)
    v2_activate.add_argument("--apply", action="store_true")
    v2_activate.add_argument("--yes", action="store_true")
    v2_activate.add_argument("--output")
    v2_activate.set_defaults(func=cmd_activate)
    v2_verify = sub.add_parser("verify-active")
    v2_verify.add_argument("--record", required=True)
    v2_verify.add_argument("--output")
    v2_verify.set_defaults(func=cmd_verify_active)
    v2_rollback = sub.add_parser("rollback")
    v2_rollback.add_argument("--record", required=True)
    v2_rollback.add_argument("--root", required=True)
    v2_rollback.add_argument("--apply", action="store_true")
    v2_rollback.add_argument("--yes", action="store_true")
    v2_rollback.add_argument("--output")
    v2_rollback.set_defaults(func=cmd_rollback)
    grade = sub.add_parser("grade-skill")
    grade.add_argument("--path", required=True, help="skill directory to grade")
    grade.add_argument("--fixtures", required=True, help="fixture file or directory")
    grade.add_argument("--output")
    grade.set_defaults(func=cmd_grade_skill)
    scan_sec = sub.add_parser("scan-security")
    scan_sec.add_argument("--path", required=True, help="directory to scan")
    scan_sec.add_argument("--fail-on", default="high", choices=["none", "low", "medium", "high"])
    scan_sec.add_argument("--output")
    scan_sec.set_defaults(func=cmd_scan_security)
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        return args.func(args)
    except (OSError, ValueError, KeyError) as exc:
        return fail(str(exc))


if __name__ == "__main__":
    sys.exit(main())
