#!/usr/bin/env python3
"""Fail-closed helpers for skills-catalog governance.

This module intentionally uses only the Python standard library.  It never mutates a
catalog during validation or planning.  Moves require an explicit plan produced by
``preflight-moves`` and both ``--apply`` and ``--yes``.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
import os
import re
import sys
from collections import Counter
import time
import stat
import uuid
from pathlib import Path
from typing import Any, Iterable

SCHEMA_VERSION = "1"
REF_RE = re.compile(r"`(references/[^`]+)`")
HEADING_RE = re.compile(r"^#{1,6}\s+(.+?)\s*$")
WORD_RE = re.compile(r"[a-z0-9][a-z0-9_.:/-]*")
ABS_WIN_RE = re.compile(r"^[A-Za-z]:[\\/]")


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
    return 0 if report.get("status") in {"PASS", "PLANNED"} else 1


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
            if overlap >= 0.50:
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
        "max_group_size": args.max_group_size,
        "candidates": candidates,
        "suggested_groups": suggested,
        "oversized_groups": oversized,
    }
    return emit(report, args.output)


def cmd_check_package(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    skill = root / "SKILL.md"
    if not skill.is_file():
        return fail("package is missing SKILL.md", [str(skill)])
    references = referenced_files(skill)
    required_payload = ["scripts/catalog_governance.py", "schemas/manifest.schema.json", "schemas/loss-check.schema.json", "schemas/approval.schema.json", "schemas/provenance.schema.json"]
    required_files = sorted(set(references + required_payload))
    missing = [relative for relative in required_files if not (root / relative).is_file()]
    report = {
        "status": "PASS" if not missing else "FAIL",
        "root": str(root),
        "skill_sha256": sha256_file(skill),
        "required_files": required_files,
        "missing_files": missing,
        "message": "all required package files are present" if not missing else "required package files are missing",
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
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(token + "\n")
    except FileExistsError:
        return fail(f"governance lock already exists: {lock}")
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
            os.rename(source, destination)
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
    grouping.add_argument("--max-group-size", type=int, default=8)
    grouping.add_argument("--output")
    grouping.set_defaults(func=cmd_detect_groups)
    package = sub.add_parser("check-package")
    package.add_argument("--root", default=".")
    package.add_argument("--output")
    package.set_defaults(func=cmd_check_package)
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
    apply.set_defaults(func=cmd_apply_moves)
    loss = sub.add_parser("loss-check")
    loss.add_argument("--draft", required=True)
    loss.add_argument("--source", action="append", required=True)
    loss.add_argument("--min-overlap", type=float, default=0.35)
    loss.add_argument("--output")
    loss.set_defaults(func=cmd_loss_check)
    approval = sub.add_parser("verify-approval")
    approval.add_argument("--draft", required=True)
    approval.add_argument("--approval", required=True)
    approval.add_argument("--loss-report")
    approval.add_argument("--output")
    approval.set_defaults(func=cmd_verify_approval)
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        return args.func(args)
    except (OSError, ValueError, KeyError) as exc:
        return fail(str(exc))


if __name__ == "__main__":
    sys.exit(main())
