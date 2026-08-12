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
import subprocess
import sys
from collections import Counter
import time
import stat
import uuid
from pathlib import Path
from typing import Any, Iterable

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
        raise ValueError("inventory must be a JSON list or an object with an inventory list")

    validated: list[dict[str, Any]] = []
    for index, entry in enumerate(inventory):
        if not isinstance(entry, dict):
            raise ValueError(f"inventory[{index}] must be an object")
        for field in ("name", "path"):
            if not isinstance(entry.get(field), str) or not entry[field].strip():
                raise ValueError(f"inventory[{index}] missing valid {field}")
        description = entry.get("description", "")
        if not isinstance(description, str):
            raise ValueError(f"inventory[{index}].description must be a string")
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
    for label, source in entries:
        relative = source.relative_to(root)
        result.append({"label": label, "source": str(source), "destination": str(archive / relative)})
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
        if exc.errno in {errno.ESRCH, errno.ENOENT}:
            return False
        return True
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
    except Exception as exc:
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
        if fenced and re.match(r"\s*(?:[$>#]|python\s|find\s|git\s|test\s|sha256|python3\s)", line, re.I):
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
        if candidate.is_file():
            if re.search(r'["\']\^|["\']~', candidate.read_text(encoding="utf-8")):
                g1_flagged.append(f"unpinned dependency range in {dep_file}")

    # G3 — version discipline (quoted string, semver-ish) + merged-from provenance
    fm = _frontmatter_region(text)
    version_match = re.search(r"^version\s*:\s*(.*?)\s*$", fm, re.M)
    if not version_match:
        g3.append("version missing from frontmatter")
    else:
        raw = version_match.group(1).strip()
        if not ((raw.startswith('"') and raw.endswith('"')) or (raw.startswith("'") and raw.endswith("'"))):
            g3.append(f"version must be a QUOTED string (YAML float trap): {raw!r}")
        elif not re.fullmatch(r"\d+\.\d+(?:\.\d+)?(?:[-+][0-9A-Za-z.-]+)?", raw[1:-1]):
            g3.append(f"version not valid semver-ish: {raw!r}")
    if re.search(r"^merged-from\s*:", fm, re.M):
        after = fm[re.search(r"^merged-from\s*:", fm, re.M).end():]
        if not re.search(r"^\s+-\s+.+", after, re.M):
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
            if isinstance(c, dict) and "source" in c:
                if any(s in c["source"] or c["source"].endswith(s) for s in allowed_sources):
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
            if poll_seconds < 0:
                poll_seconds = 0
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
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        return args.func(args)
    except (OSError, ValueError, KeyError) as exc:
        return fail(str(exc))


if __name__ == "__main__":
    sys.exit(main())
