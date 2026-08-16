import argparse
import errno
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "scripts" / "catalog_governance.py"
SCHEMAS = ROOT / "schemas"
FIXTURE_USAGE = ROOT / "tests" / "fixtures" / "usage-real-shape.json"
MODULE_SPEC = importlib.util.spec_from_file_location("catalog_governance", TOOL)
assert MODULE_SPEC is not None and MODULE_SPEC.loader is not None
GOVERNANCE = importlib.util.module_from_spec(MODULE_SPEC)
MODULE_SPEC.loader.exec_module(GOVERNANCE)


class GovernanceCliTests(unittest.TestCase):
    def run_cli(self, *args, expected=0, env=None):
        result = subprocess.run(
            [sys.executable, str(TOOL), *map(str, args)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def make_package(self, directory: Path):
        (directory / "references").mkdir(parents=True)
        (directory / "scripts").mkdir()
        (directory / "schemas").mkdir()
        (directory / "references" / "ok.md").write_text("ok\n", encoding="utf-8")
        (directory / "scripts" / "catalog_governance.py").write_text(TOOL.read_text(encoding="utf-8"), encoding="utf-8")
        for schema in SCHEMAS.glob("*.json"):
            (directory / "schemas" / schema.name).write_text(schema.read_text(encoding="utf-8"), encoding="utf-8")
        (directory / "SKILL.md").write_text(
            "---\nname: test\n---\nSee `references/ok.md`.\n", encoding="utf-8"
        )

    def test_version_guard_passes_on_current_interpreter(self):
        self.assertIsNone(GOVERNANCE.require_python_version())

    def test_version_guard_fails_cleanly_for_old_python(self):
        # Simulate running under Python 3.9: the module must emit the structured
        # FAIL JSON and exit 1, never a raw traceback.
        probe = (
            "import importlib.util, sys\n"
            f"spec = importlib.util.spec_from_file_location('cg', {str(TOOL)!r})\n"
            "m = importlib.util.module_from_spec(spec)\n"
            "sys.version_info = (3, 9, 0)\n"
            "try:\n"
            "    spec.loader.exec_module(m)\n"
            "except SystemExit as exc:\n"
            "    print('GUARD_EXIT', exc.code)\n"
            "    raise\n"
        )
        result = subprocess.run([sys.executable, "-c", probe], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn("GUARD_EXIT 1", result.stdout)
        report = json.loads(result.stdout.split("GUARD_EXIT")[0].strip())
        self.assertEqual(report["status"], "FAIL")
        self.assertIn("3.10", report["message"])
        self.assertIn("3.9", report["message"])

    def test_complete_package_passes(self):
        with tempfile.TemporaryDirectory() as raw:
            package = Path(raw) / "package"
            package.mkdir()
            self.make_package(package)
            report = self.run_cli("check-package", "--root", package)
            self.assertEqual(report["status"], "PASS")

    def test_missing_package_payload_fails(self):
        with tempfile.TemporaryDirectory() as raw:
            package = Path(raw) / "package"
            package.mkdir()
            (package / "SKILL.md").write_text("---\nname: test\n---\n", encoding="utf-8")
            report = self.run_cli("check-package", "--root", package, expected=1)
            self.assertEqual(report["status"], "FAIL")
            self.assertIn("scripts/catalog_governance.py", report["missing_files"])
            self.assertIn("schemas/council-verdict.schema.json", report["missing_files"])

    def make_catalog(self, raw: str):
        base = Path(raw)
        catalog = base / "catalog"
        archive = base / "archive"
        source = catalog / "skill-a"
        source.mkdir(parents=True)
        archive.mkdir()
        (source / "SKILL.md").write_text("# Skill A\n\nimportant content\n", encoding="utf-8")
        manifest = base / "manifest.json"
        manifest.write_text(
            json.dumps({"archive": {"skill-a": str(source)}, "merge": [], "merge_survivors": []}),
            encoding="utf-8",
        )
        return catalog, archive, source, manifest

    def test_move_plan_and_apply_are_hash_checked(self):
        with tempfile.TemporaryDirectory() as raw:
            catalog, archive, source, manifest = self.make_catalog(raw)
            plan = Path(raw) / "plan.json"
            planned = self.run_cli(
                "preflight-moves", "--root", catalog, "--archive", archive,
                "--manifest", manifest, "--plan", plan,
            )
            self.assertEqual(planned["status"], "PLANNED")
            applied = self.run_cli("apply-moves", "--plan", plan, "--apply", "--yes")
            self.assertEqual(applied["status"], "PASS")
            self.assertFalse(source.exists())
            self.assertTrue((archive / "skill-a" / "SKILL.md").is_file())

    def test_unsafe_move_shapes_fail_closed(self):
        with tempfile.TemporaryDirectory() as raw:
            catalog, archive, source, manifest = self.make_catalog(raw)
            nested_archive = catalog / "inside-archive"
            report = self.run_cli(
                "preflight-moves", "--root", catalog, "--archive", nested_archive,
                "--manifest", manifest, "--plan", Path(raw) / "bad.json", expected=1,
            )
            self.assertEqual(report["status"], "FAIL")
            self.assertTrue(any("sibling" in detail for detail in report["details"]))

            root_manifest = Path(raw) / "root.json"
            root_manifest.write_text(
                json.dumps({"archive": {"root": str(catalog)}, "merge": [], "merge_survivors": []}),
                encoding="utf-8",
            )
            report = self.run_cli(
                "preflight-moves", "--root", catalog, "--archive", archive,
                "--manifest", root_manifest, "--plan", Path(raw) / "root-plan.json", expected=1,
            )
            self.assertTrue(any("catalog root" in detail for detail in report["details"]))

    def test_apply_rejects_source_tampering_after_preflight(self):
        with tempfile.TemporaryDirectory() as raw:
            catalog, archive, source, manifest = self.make_catalog(raw)
            plan = Path(raw) / "plan.json"
            self.run_cli(
                "preflight-moves", "--root", catalog, "--archive", archive,
                "--manifest", manifest, "--plan", plan,
            )
            (source / "SKILL.md").write_text("tampered\n", encoding="utf-8")
            report = self.run_cli("apply-moves", "--plan", plan, "--apply", "--yes", expected=1)
            self.assertEqual(report["status"], "FAIL")
            self.assertTrue(source.exists())
            self.assertFalse((archive / "skill-a").exists())

    def test_loss_check_and_hash_bound_approval(self):
        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            source = base / "source.md"
            draft = base / "draft.md"
            content = "# Required\n\nkeep alpha beta\n```bash\nfind x\n```\n"
            source.write_text(content, encoding="utf-8")
            draft.write_text(content, encoding="utf-8")
            report = self.run_cli("loss-check", "--draft", draft, "--source", source)
            self.assertEqual(report["status"], "PASS")

            import hashlib
            digest = hashlib.sha256(draft.read_bytes()).hexdigest()
            approval = base / "approval.json"
            approval.write_text(
                json.dumps({
                    "draft": str(draft), "draft_sha256": digest, "reviewed_by": "tester",
                    "decision": "APPROVE", "approval_text": "Approved exact draft.",
                    "approved_at_utc": "2026-08-10T00:00:00Z",
                }),
                encoding="utf-8",
            )
            report = self.run_cli("verify-approval", "--draft", draft, "--approval", approval)
            self.assertEqual(report["status"], "PASS")
            invalid_approval = base / "invalid-approval.json"
            invalid_data = json.loads(approval.read_text(encoding="utf-8"))
            invalid_data["approved_at_utc"] = "not-a-timestamp"
            invalid_approval.write_text(json.dumps(invalid_data), encoding="utf-8")
            report = self.run_cli("verify-approval", "--draft", draft, "--approval", invalid_approval, expected=1)
            self.assertEqual(report["status"], "FAIL")
            self.assertIn("approved_at_utc", " ".join(report["errors"]))
            draft.write_text(content + "tampered\n", encoding="utf-8")
            report = self.run_cli("verify-approval", "--draft", draft, "--approval", approval, expected=1)
            self.assertEqual(report["status"], "FAIL")
            self.assertIn("hash", " ".join(report["errors"]))

    def make_approval(self, base: Path, draft: Path, content: str, reviewed_by="tester"):
        digest = hashlib.sha256(draft.read_bytes()).hexdigest()
        approval = base / "approval.json"
        approval.write_text(
            json.dumps({
                "draft": str(draft), "draft_sha256": digest, "reviewed_by": reviewed_by,
                "decision": "APPROVE", "approval_text": "Approved exact draft.",
                "approved_at_utc": "2026-08-10T00:00:00Z",
            }),
            encoding="utf-8",
        )
        return approval, digest

    def test_loss_report_binds_approval_to_live_state(self):
        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            source = base / "source.md"
            draft = base / "draft.md"
            content = "# Required\n\nkeep alpha beta\n```bash\nfind x\n```\n"
            source.write_text(content, encoding="utf-8")
            draft.write_text(content, encoding="utf-8")
            loss_report = base / "loss.json"
            self.run_cli("loss-check", "--draft", draft, "--source", source, "--output", loss_report)
            approval, _ = self.make_approval(base, draft, content)
            report = self.run_cli("verify-approval", "--draft", draft, "--approval", approval, "--loss-report", loss_report)
            self.assertEqual(report["status"], "PASS")
            self.assertEqual(report["reverified_count"], 1)
            self.assertEqual(report["reverified_checks"][0]["status"], "PASS")

    def test_loss_report_refuses_tampered_source(self):
        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            source = base / "source.md"
            draft = base / "draft.md"
            content = "# Required\n\nkeep alpha beta\n```bash\nfind x\n```\n"
            source.write_text(content, encoding="utf-8")
            draft.write_text(content, encoding="utf-8")
            loss_report = base / "loss.json"
            self.run_cli("loss-check", "--draft", draft, "--source", source, "--output", loss_report)
            approval, _ = self.make_approval(base, draft, content)
            source.write_text(content + "sneaked\n", encoding="utf-8")
            report = self.run_cli(
                "verify-approval", "--draft", draft, "--approval", approval,
                "--loss-report", loss_report, expected=1,
            )
            self.assertEqual(report["status"], "FAIL")
            self.assertTrue(any("changed since loss-check" in err for err in report["errors"]))

    def test_loss_report_refuses_unclean_review_status(self):
        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            source = base / "source.md"
            draft = base / "draft.md"
            source.write_text("# Required\n\n# Other section\n\nkeep alpha beta\n```bash\nfind x\n```\n", encoding="utf-8")
            draft.write_text("# Required\n\nkeep alpha beta\n```bash\nfind x\n```\n", encoding="utf-8")
            loss_report = base / "loss.json"
            self.run_cli("loss-check", "--draft", draft, "--source", source, "--output", loss_report, expected=1)
            approval, _ = self.make_approval(base, draft, draft.read_text(encoding="utf-8"))
            report = self.run_cli(
                "verify-approval", "--draft", draft, "--approval", approval,
                "--loss-report", loss_report, expected=1,
            )
            self.assertEqual(report["status"], "FAIL")
            self.assertTrue(any("every check PASS" in err for err in report["errors"]))

    def make_skill(self, store: Path, dirname="demo", content=None):
        skill = store / dirname
        skill.mkdir(parents=True)
        skill_file = skill / "SKILL.md"
        skill_file.write_bytes((content or "---\nname: Demo\ndescription: A demo skill\n---\nbody\n").encode("utf-8"))
        return skill_file

    def write_usage(self, store: Path, payload):
        usage_file = store / ".usage.json"
        usage_file.write_text(json.dumps(payload), encoding="utf-8")
        return usage_file

    def test_load_usage_counts_nested_objects(self):
        with tempfile.TemporaryDirectory() as raw:
            store = Path(raw)
            self.write_usage(store, {
                "skill-a": {"use_count": 7, "view_count": 3},
                "skill-b": {"use_count": 0},
            })
            result = self.run_usage_loader(store)
            self.assertEqual(result, {"skill-a": 7, "skill-b": 0})

    def test_load_usage_counts_flat_values_remain_supported(self):
        with tempfile.TemporaryDirectory() as raw:
            store = Path(raw)
            self.write_usage(store, {"skill-a": 7})
            result = self.run_usage_loader(store)
            self.assertEqual(result, {"skill-a": 7})

    def test_load_usage_counts_real_shape_fixture(self):
        with tempfile.TemporaryDirectory() as raw:
            store = Path(raw)
            self.write_usage(
                store,
                json.loads(FIXTURE_USAGE.read_text(encoding="utf-8")),
            )
            result = self.run_usage_loader(store)
            self.assertEqual(result, {
                "demo-skill-a": 39,
                "demo-skill-b": 0,
                "demo-skill-c": 131,
            })

    def test_load_usage_counts_skills_wrapper_supports_nested_objects(self):
        with tempfile.TemporaryDirectory() as raw:
            store = Path(raw)
            self.write_usage(store, {"skills": {
                "skill-a": {"use_count": 7, "view_count": 3},
                "skill-b": {"use_count": 0},
            }})
            result = self.run_usage_loader(store)
            self.assertEqual(result, {"skill-a": 7, "skill-b": 0})

    def test_load_usage_counts_missing_file_fails_open(self):
        with tempfile.TemporaryDirectory() as raw:
            self.assertEqual(self.run_usage_loader(Path(raw)), {})

    def test_load_usage_counts_invalid_json_fails_open(self):
        with tempfile.TemporaryDirectory() as raw:
            store = Path(raw)
            (store / ".usage.json").write_text("{not-json", encoding="utf-8")
            self.assertEqual(self.run_usage_loader(store), {})

    def run_usage_loader(self, store: Path):
        return GOVERNANCE.load_usage_counts(store)

    def verdict_file(self, directory: Path, frontmatter: str) -> Path:
        verdict = directory / "verdict.md"
        verdict.write_text(frontmatter + "\n# Council notes\n", encoding="utf-8")
        return verdict

    def test_validate_council_verdict_valid_frontmatter(self):
        with tempfile.TemporaryDirectory() as raw:
            verdict = self.verdict_file(Path(raw), """---
verdict: MERGE
survivors:
  - caveman-commit
recategorizations:
  - ce-commit
absorbed:
  - writing-commit-messages
gates_passed:
  - G0
  - G1
  - G3
---""")
            report = self.run_cli("validate-council-verdict", "--verdict", verdict)
            self.assertEqual(report["status"], "PASS")
            self.assertEqual(report["verdict"], "MERGE")
            self.assertEqual(report["survivors"], ["caveman-commit"])
            self.assertEqual(report["recategorizations"], ["ce-commit"])
            self.assertEqual(report["absorbed"], ["writing-commit-messages"])
            self.assertEqual(report["gates_passed"], ["G0", "G1", "G3"])

    def test_validate_council_verdict_missing_verdict(self):
        with tempfile.TemporaryDirectory() as raw:
            verdict = self.verdict_file(Path(raw), "---\nsurvivors:\n  - survivor\n---")
            report = self.run_cli("validate-council-verdict", "--verdict", verdict, expected=1)
            self.assertEqual(report["status"], "FAIL")
            self.assertIn("verdict", " ".join(report["errors"]))

    def test_validate_council_verdict_rejects_unknown_verdict(self):
        with tempfile.TemporaryDirectory() as raw:
            verdict = self.verdict_file(Path(raw), "---\nverdict: MAYBE\nsurvivors:\n  - survivor\n---")
            report = self.run_cli("validate-council-verdict", "--verdict", verdict, expected=1)
            self.assertEqual(report["status"], "FAIL")
            self.assertIn("MAYBE", " ".join(report["errors"]))

    def test_validate_council_verdict_requires_survivors(self):
        with tempfile.TemporaryDirectory() as raw:
            verdict = self.verdict_file(Path(raw), "---\nverdict: MERGE\n---")
            report = self.run_cli("validate-council-verdict", "--verdict", verdict, expected=1)
            self.assertEqual(report["status"], "FAIL")
            self.assertIn("survivors", " ".join(report["errors"]))

    def test_validate_council_verdict_rejects_empty_survivors(self):
        with tempfile.TemporaryDirectory() as raw:
            verdict = self.verdict_file(Path(raw), "---\nverdict: MERGE\nsurvivors:\n---")
            report = self.run_cli("validate-council-verdict", "--verdict", verdict, expected=1)
            self.assertEqual(report["status"], "FAIL")
            self.assertIn("survivors", " ".join(report["errors"]))

    def test_validate_council_verdict_rejects_malformed_frontmatter(self):
        with tempfile.TemporaryDirectory() as raw:
            verdict = self.verdict_file(Path(raw), "---\nverdict: MERGE\nnot valid\n---")
            report = self.run_cli("validate-council-verdict", "--verdict", verdict, expected=1)
            self.assertEqual(report["status"], "FAIL")
            self.assertIn("malformed", " ".join(report["errors"]))

    def test_validate_council_verdict_requires_frontmatter(self):
        with tempfile.TemporaryDirectory() as raw:
            verdict = self.verdict_file(Path(raw), "Council notes only")
            report = self.run_cli("validate-council-verdict", "--verdict", verdict, expected=1)
            self.assertEqual(report["status"], "FAIL")
            self.assertIn("no frontmatter block", " ".join(report["errors"]))

    def test_detect_skills_empty_store(self):
        with tempfile.TemporaryDirectory() as raw:
            store = Path(raw) / "empty"
            store.mkdir()
            report = self.run_cli("detect-skills", "--stores", store)
            self.assertEqual(report["status"], "PASS")
            self.assertEqual(report["counts"], {"external": 0})
            self.assertEqual(report["total"], 0)
            self.assertEqual(report["inventory"], [])

    def test_detect_skills_skips_junction_or_symlink_mirror(self):
        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            store = base / "store"
            store.mkdir()
            self.make_skill(store, "real")
            mirror = store / "mirror"
            try:
                mirror.symlink_to(store / "real", target_is_directory=True)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"directory links unavailable: {exc}")
            report = self.run_cli("detect-skills", "--stores", store)
            self.assertEqual(report["total"], 1)
            self.assertEqual(report["inventory"][0]["name"], "Demo")

    def test_detect_skills_parses_frontmatter_with_dir_fallback(self):
        with tempfile.TemporaryDirectory() as raw:
            store = Path(raw) / "store"
            store.mkdir()
            self.make_skill(store, "named", "---\nname: Parsed Name\ndescription: \'Useful description\'\n---\nbody\n")
            self.make_skill(store, "fallback", "body without frontmatter\n")
            report = self.run_cli("detect-skills", "--stores", store)
            by_name = {item["name"]: item for item in report["inventory"]}
            self.assertEqual(by_name["Parsed Name"]["description"], "Useful description")
            self.assertEqual(by_name["fallback"]["description"], "")

    def test_detect_skills_parses_multiline_description(self):
        with tempfile.TemporaryDirectory() as raw:
            store = Path(raw) / "store"
            store.mkdir()
            self.make_skill(
                store,
                "multiline",
                "---\nname: Multi-line skill\ndescription: First line\n  Use when: the second line continues the description.\n---\nbody\n",
            )
            report = self.run_cli("detect-skills", "--stores", store)
            self.assertEqual(report["status"], "PASS")
            entry = report["inventory"][0]
            self.assertEqual(
                entry["description"],
                "First line Use when: the second line continues the description.",
            )

    def test_detect_skills_parses_folded_and_literal_descriptions(self):
        with tempfile.TemporaryDirectory() as raw:
            store = Path(raw) / "store"
            store.mkdir()
            self.make_skill(
                store,
                "folded",
                "---\nname: Folded\ndescription: >\n  First line\n  Second line\n---\nbody\n",
            )
            self.make_skill(
                store,
                "literal",
                "---\nname: Literal\ndescription: |\n  First line\n  Second line\n---\nbody\n",
            )
            report = self.run_cli("detect-skills", "--stores", store)
            descriptions = {item["name"]: item["description"] for item in report["inventory"]}
            self.assertEqual(descriptions["Folded"], "First line Second line")
            self.assertEqual(descriptions["Literal"], "First line\nSecond line")

    def test_detect_skills_rejects_malformed_top_level_frontmatter(self):
        with tempfile.TemporaryDirectory() as raw:
            store = Path(raw) / "store"
            store.mkdir()
            self.make_skill(store, "malformed", "---\nname: Bad\nnot valid\n---\nbody\n")
            report = self.run_cli("detect-skills", "--stores", store, expected=1)
            self.assertEqual(report["status"], "FAIL")
            self.assertEqual(report["inventory"], [])
            self.assertEqual(len(report["errors"]), 1)

    def test_detect_skills_sha256_is_stable(self):
        with tempfile.TemporaryDirectory() as raw:
            store = Path(raw) / "store"
            store.mkdir()
            skill_file = self.make_skill(store)
            expected = hashlib.sha256(skill_file.read_bytes()).hexdigest()
            first = self.run_cli("detect-skills", "--stores", store)
            second = self.run_cli("detect-skills", "--stores", store)
            self.assertEqual(first["inventory"][0]["sha256"], expected)
            self.assertEqual(first["inventory"][0]["sha256"], second["inventory"][0]["sha256"])

    def test_detect_skills_explicit_stores_are_external_and_read_only(self):
        with tempfile.TemporaryDirectory() as raw:
            store = Path(raw) / "third-party"
            store.mkdir()
            self.make_skill(store)
            report = self.run_cli("detect-skills", "--stores", store)
            entry = report["inventory"][0]
            self.assertEqual(entry["store"], "external")
            self.assertTrue(entry["read_only"])

    def test_install_into_explicit_target(self):
        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw) / "skills"
            target.mkdir()
            report = self.run_cli("install", "--target", target)
            self.assertEqual(report["status"], "PASS")
            self.assertEqual(report["installed"], [{
                "harness": "custom",
                "target": str(target),
                "existed": False,
                "overwritten": False,
            }])
            self.assertTrue((target / "skills-catalog-governance" / "SKILL.md").is_file())
            self.assertEqual(report["check_package"]["status"], "PASS")

    def test_install_noninteractive_without_target_or_yes_fails_closed(self):
        with tempfile.TemporaryDirectory() as raw:
            home = Path(raw)
            (home / ".claude" / "skills").mkdir(parents=True)
            env = os.environ.copy()
            env["HOME"] = str(home)
            report = self.run_cli("install", expected=1, env=env)
            self.assertEqual(report["status"], "FAIL")
            self.assertIn("requires --target or --yes", " ".join(report["errors"]))
            self.assertFalse((home / ".claude" / "skills" / "skills-catalog-governance").exists())

    def test_install_fails_when_no_harness_is_detected(self):
        with tempfile.TemporaryDirectory() as raw:
            env = os.environ.copy()
            env["HOME"] = raw
            report = self.run_cli("install", expected=1, env=env)
            self.assertEqual(report["status"], "FAIL")
            self.assertIn("no supported harness detected", " ".join(report["errors"]))

    def test_install_rejects_missing_target(self):
        with tempfile.TemporaryDirectory() as raw:
            missing = Path(raw) / "does-not-exist"
            report = self.run_cli("install", "--target", missing, expected=1)
            self.assertEqual(report["status"], "FAIL")
            self.assertIn("does not exist", " ".join(report["errors"]))

    def test_install_existing_target_is_not_overwritten_without_yes(self):
        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw) / "skills"
            target.mkdir()
            destination = target / "skills-catalog-governance"
            destination.mkdir()
            marker = destination / "user-file.txt"
            marker.write_text("keep me", encoding="utf-8")
            report = self.run_cli("install", "--target", target, expected=1)
            self.assertEqual(report["status"], "FAIL")
            self.assertFalse(report["installed"][0]["overwritten"])
            self.assertTrue(marker.is_file())
            self.assertEqual(marker.read_text(encoding="utf-8"), "keep me")

    def test_install_yes_creates_timestamped_backup(self):
        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw) / "skills"
            target.mkdir()
            destination = target / "skills-catalog-governance"
            destination.mkdir()
            (destination / "old.txt").write_text("old", encoding="utf-8")
            report = self.run_cli("install", "--target", target, "--yes")
            self.assertEqual(report["status"], "PASS")
            self.assertTrue(report["installed"][0]["overwritten"])
            backups = list(target.glob("skills-catalog-governance.bak-*"))
            self.assertEqual(len(backups), 1)
            self.assertEqual((backups[0] / "old.txt").read_text(encoding="utf-8"), "old")
            self.assertTrue((destination / "SKILL.md").is_file())

    def test_install_detection_finds_harness_in_probe_order(self):
        with tempfile.TemporaryDirectory() as raw:
            home = Path(raw)
            harness_dir = home / ".claude" / "skills"
            harness_dir.mkdir(parents=True)
            env = os.environ.copy()
            env["HOME"] = str(home)
            report = self.run_cli("install", "--yes", env=env)
            self.assertEqual(report["status"], "PASS")
            self.assertEqual(report["installed"][0]["harness"], "claude")
            self.assertTrue((harness_dir / "skills-catalog-governance" / "SKILL.md").is_file())

    def write_inventory(self, directory: Path, entries):
        inventory = directory / "inventory.json"
        inventory.write_text(json.dumps({"status": "PASS", "inventory": entries}), encoding="utf-8")
        return inventory

    def make_inventory_entry(self, name, description, path="/skills"):
        return {
            "store": "master",
            "path": f"{path}/{name}",
            "name": name,
            "description": description,
            "sha256": "0" * 64,
        }

    def test_detect_groups_identical_descriptions_flag_both_signals(self):
        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            description = "shared testing workflow validation guidance " * 8
            inventory = self.write_inventory(base, [
                self.make_inventory_entry("alpha", description),
                self.make_inventory_entry("beta", description),
            ])
            report = self.run_cli("detect-groups", "--inventory", inventory)
            self.assertEqual(report["status"], "PASS")
            self.assertEqual(report["counts"], {"skills": 2, "pairs": 1, "candidates": 1, "groups": 1})
            pair = report["candidates"][0]
            self.assertAlmostEqual(pair["cosine"], 1.0, delta=0.05)
            self.assertGreaterEqual(pair["word_overlap"], 0.80)
            self.assertEqual(pair["flagged_by"], ["cosine", "overlap"])

    def test_detect_groups_different_descriptions_are_not_flagged(self):
        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            inventory = self.write_inventory(base, [
                self.make_inventory_entry("alpha", "database migration rollback procedure"),
                self.make_inventory_entry("beta", "painting watercolor landscapes outdoors"),
            ])
            report = self.run_cli("detect-groups", "--inventory", inventory)
            self.assertEqual(report["counts"]["pairs"], 1)
            self.assertEqual(report["counts"]["candidates"], 0)
            self.assertEqual(report["candidates"], [])
            self.assertEqual(report["suggested_groups"], [])

    def test_detect_groups_word_overlap_catches_near_duplicates(self):
        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            inventory = self.write_inventory(base, [
                self.make_inventory_entry("alpha", "testing workflow validation reliable repeatable checks"),
                self.make_inventory_entry("beta", "testing workflow validation reliable checks with automation"),
            ])
            report = self.run_cli("detect-groups", "--inventory", inventory, "--threshold", "0.99")
            pair = report["candidates"][0]
            self.assertGreaterEqual(pair["word_overlap"], 0.50)
            self.assertIn("overlap", pair["flagged_by"])

    def test_detect_groups_connected_components(self):
        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            inventory = self.write_inventory(base, [
                self.make_inventory_entry("alpha", "testing workflow validation checks"),
                self.make_inventory_entry("beta", "testing workflow validation checks automation"),
                self.make_inventory_entry("gamma", "testing workflow validation checks repeatable"),
            ])
            report = self.run_cli("detect-groups", "--inventory", inventory, "--threshold", "0.40")
            self.assertEqual(report["suggested_groups"], [["alpha", "beta", "gamma"]])

    def test_detect_groups_weak_single_signal_does_not_bridge_groups(self):
        # Two cohesive families (A: ios-*, B: ce-*) with one WEAK bridge pair
        # (ios-sync <-> ce-report-bug share a single generic word "process").
        # The bridge flags cosine-only (overlap < 0.50) and must NOT chain the
        # families into a mega-group (the v3.1 over-grouping fix).
        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            inventory = self.write_inventory(base, [
                self.make_inventory_entry("ios-clean", "ios app cleanup remove build artifacts"),
                self.make_inventory_entry("ios-sync", "ios app sync regenerate build artifacts process"),
                self.make_inventory_entry("ce-report-bug", "ce report bug tracker issue triage process"),
                self.make_inventory_entry("ce-release-notes", "ce report bug tracker assign owner"),
            ])
            report = self.run_cli("detect-groups", "--inventory", inventory, "--threshold", "0.20")
            self.assertEqual(report["counts"]["groups"], 2)
            self.assertEqual(report["suggested_groups"], [["ce-release-notes", "ce-report-bug"], ["ios-clean", "ios-sync"]])

    def test_apply_recovers_a_provably_stale_lock(self):
        with tempfile.TemporaryDirectory() as raw:
            catalog, archive, source, manifest = self.make_catalog(raw)
            plan = Path(raw) / "plan.json"
            self.run_cli("preflight-moves", "--root", catalog, "--archive", archive, "--manifest", manifest, "--plan", plan)
            lock = catalog.parent / f".{catalog.name}.catalog-governance.lock"
            lock.write_text("-1:stale-token\n", encoding="utf-8")
            report = self.run_cli("apply-moves", "--plan", plan, "--apply", "--yes", "--recover-stale-lock")
            self.assertEqual(report["status"], "PASS")
            self.assertFalse(lock.exists())
            self.assertFalse(source.exists())

    def test_apply_refuses_malformed_lock_even_with_recovery_requested(self):
        with tempfile.TemporaryDirectory() as raw:
            catalog, archive, source, manifest = self.make_catalog(raw)
            plan = Path(raw) / "plan.json"
            self.run_cli("preflight-moves", "--root", catalog, "--archive", archive, "--manifest", manifest, "--plan", plan)
            lock = catalog.parent / f".{catalog.name}.catalog-governance.lock"
            lock.write_text("not-a-lock\n", encoding="utf-8")
            report = self.run_cli("apply-moves", "--plan", plan, "--apply", "--yes", "--recover-stale-lock", expected=1)
            self.assertEqual(report["status"], "FAIL")
            self.assertTrue(lock.exists())
            self.assertTrue(source.exists())

    def test_apply_refuses_active_lock_even_with_recovery_requested(self):
        with tempfile.TemporaryDirectory() as raw:
            catalog, archive, source, manifest = self.make_catalog(raw)
            plan = Path(raw) / "plan.json"
            self.run_cli("preflight-moves", "--root", catalog, "--archive", archive, "--manifest", manifest, "--plan", plan)
            lock = catalog.parent / f".{catalog.name}.catalog-governance.lock"
            lock.write_text(f"{os.getpid()}:active-token\n", encoding="utf-8")
            report = self.run_cli("apply-moves", "--plan", plan, "--apply", "--yes", "--recover-stale-lock", expected=1)
            self.assertEqual(report["status"], "FAIL")
            self.assertTrue(lock.exists())
            self.assertTrue(source.exists())

    def test_move_tree_falls_back_after_cross_device_rename_error(self):
        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            source = base / "source"
            destination = base / "archive" / "source"
            source.mkdir()
            (source / "SKILL.md").write_text("content\n", encoding="utf-8")
            expected_digest = GOVERNANCE.tree_digest(source)
            original_rename = GOVERNANCE.os.rename
            calls = 0

            def raise_exdev_once(source_path, destination_path):
                nonlocal calls
                calls += 1
                if calls == 1:
                    raise OSError(errno.EXDEV, "cross-device link")
                return original_rename(source_path, destination_path)

            GOVERNANCE.os.rename = raise_exdev_once
            try:
                GOVERNANCE.move_tree(source, destination, expected_digest)
            finally:
                GOVERNANCE.os.rename = original_rename
            self.assertFalse(source.exists())
            self.assertEqual(GOVERNANCE.tree_digest(destination), expected_digest)

    def test_move_tree_refuses_when_source_changes_during_cross_device_copy(self):
        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            source = base / "source"
            destination = base / "archive" / "source"
            source.mkdir()
            (source / "SKILL.md").write_text("content\n", encoding="utf-8")
            original_rename = GOVERNANCE.os.rename
            original_digest = GOVERNANCE.tree_digest

            def raise_exdev(source_path, destination_path):
                raise OSError(errno.EXDEV, "cross-device link")

            def fake_digest(path):
                if path == source:
                    return "changed-during-copy"
                return original_digest(path)

            GOVERNANCE.os.rename = raise_exdev
            GOVERNANCE.tree_digest = fake_digest
            try:
                with self.assertRaisesRegex(RuntimeError, "source changed"):
                    GOVERNANCE.move_tree(source, destination, "expected")
            finally:
                GOVERNANCE.os.rename = original_rename
                GOVERNANCE.tree_digest = original_digest
            self.assertTrue(source.exists())
            self.assertFalse(destination.exists())
            self.assertEqual(list(destination.parent.glob(f".{destination.name}.tmp-*")), [])

    def test_move_tree_refuses_when_staged_copy_hash_mismatches(self):
        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            source = base / "source"
            destination = base / "archive" / "source"
            source.mkdir()
            (source / "SKILL.md").write_text("content\n", encoding="utf-8")
            expected_digest = GOVERNANCE.tree_digest(source)
            original_rename = GOVERNANCE.os.rename
            original_digest = GOVERNANCE.tree_digest
            digest_calls = 0

            def raise_exdev(source_path, destination_path):
                raise OSError(errno.EXDEV, "cross-device link")

            def fake_digest(path):
                nonlocal digest_calls
                digest_calls += 1
                if digest_calls == 1:
                    return expected_digest
                return "staging-corrupted"

            GOVERNANCE.os.rename = raise_exdev
            GOVERNANCE.tree_digest = fake_digest
            try:
                with self.assertRaisesRegex(RuntimeError, "hash mismatch"):
                    GOVERNANCE.move_tree(source, destination, expected_digest)
            finally:
                GOVERNANCE.os.rename = original_rename
                GOVERNANCE.tree_digest = original_digest
            self.assertTrue(source.exists())
            self.assertFalse(destination.exists())
            self.assertEqual(list(destination.parent.glob(f".{destination.name}.tmp-*")), [])

    def test_process_is_alive_distinguishes_live_from_dead_pids(self):
        self.assertTrue(GOVERNANCE.process_is_alive(os.getpid()))
        self.assertFalse(GOVERNANCE.process_is_alive(2**31 - 1))

    def test_apply_refuses_when_lock_is_recreated_during_recovery(self):
        with tempfile.TemporaryDirectory() as raw:
            catalog, archive, source, manifest = self.make_catalog(raw)
            plan = Path(raw) / "plan.json"
            self.run_cli(
                "preflight-moves", "--root", catalog, "--archive", archive,
                "--manifest", manifest, "--plan", plan,
            )
            lock = catalog.parent / f".{catalog.name}.catalog-governance.lock"
            lock.write_text("-1:stale-token\n", encoding="utf-8")
            original_create = GOVERNANCE.create_move_lock
            create_calls = {"n": 0}

            def racy_create(lock_path, token):
                create_calls["n"] += 1
                if create_calls["n"] > 1:
                    original_create(lock_path, token)
                    raise FileExistsError("lock recreated by a racer")
                return original_create(lock_path, token)

            GOVERNANCE.create_move_lock = racy_create
            try:
                code = GOVERNANCE.cmd_apply_moves(argparse.Namespace(
                    plan=str(plan), apply=True, yes=True, recover_stale_lock=True, journal=None,
                ))
            finally:
                GOVERNANCE.create_move_lock = original_create
            self.assertEqual(code, 1)
            self.assertTrue(lock.exists())
            self.assertTrue(source.exists())

    def test_detect_groups_empty_inventory_passes(self):
        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            inventory = self.write_inventory(base, [])
            report = self.run_cli("detect-groups", "--inventory", inventory)
            self.assertEqual(report["status"], "PASS")
            self.assertEqual(report["counts"], {"skills": 0, "pairs": 0, "candidates": 0, "groups": 0})
            self.assertEqual(report["candidates"], [])
            self.assertEqual(report["suggested_groups"], [])
            self.assertEqual(report["oversized_groups"], [])

    def test_detect_groups_multiline_description_tokenizes(self):
        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            store = base / "store"
            store.mkdir()
            self.make_skill(
                store,
                "alpha",
                "---\nname: alpha\ndescription: |\n  first line\n  second validation workflow\n---\nbody\n",
            )
            self.make_skill(
                store,
                "beta",
                "---\nname: beta\ndescription: first line second validation workflow\n---\nbody\n",
            )
            inventory = base / "inventory.json"
            self.run_cli("detect-skills", "--stores", store, "--output", inventory)
            report = self.run_cli("detect-groups", "--inventory", inventory)
            self.assertEqual(report["counts"]["candidates"], 1)

    def test_detect_groups_overlap_threshold_is_configurable(self):
        with tempfile.TemporaryDirectory() as raw:
            inventory = self.write_inventory(Path(raw), [
                self.make_inventory_entry("alpha", "shared workflow validation checks extra"),
                self.make_inventory_entry("beta", "shared workflow validation checks different"),
            ])
            report = self.run_cli("detect-groups", "--inventory", inventory, "--threshold", "0.99", "--overlap-threshold", "0.80")
            self.assertEqual(report["overlap_threshold"], 0.80)
            self.assertEqual(report["counts"]["candidates"], 0)
            relaxed = self.run_cli("detect-groups", "--inventory", inventory, "--threshold", "0.99", "--overlap-threshold", "0.50")
            self.assertEqual(relaxed["counts"]["candidates"], 1)

    def test_detect_groups_rejects_invalid_overlap_threshold(self):
        with tempfile.TemporaryDirectory() as raw:
            inventory = self.write_inventory(Path(raw), [])
            report = self.run_cli("detect-groups", "--inventory", inventory, "--overlap-threshold", "1.1", expected=1)
            self.assertIn("overlap-threshold", report["message"])

    def test_detect_groups_stricter_threshold_reduces_cosine_candidates(self):
        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            inventory = self.write_inventory(base, [
                self.make_inventory_entry("alpha", "validation validation validation validation validation alpha beta gamma delta epsilon"),
                self.make_inventory_entry("beta", "validation validation validation validation validation zeta eta theta iota kappa"),
            ])
            default = self.run_cli("detect-groups", "--inventory", inventory, "--threshold", "0.30")
            strict = self.run_cli("detect-groups", "--inventory", inventory, "--threshold", "0.99")
            self.assertGreaterEqual(default["counts"]["candidates"], strict["counts"]["candidates"])

    def test_detect_groups_rejects_failed_inventory_report(self):
        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            inventory = base / "inventory.json"
            inventory.write_text(
                json.dumps({"status": "FAIL", "errors": ["scan failed"], "inventory": []}),
                encoding="utf-8",
            )
            report = self.run_cli("detect-groups", "--inventory", inventory, expected=1)
            self.assertEqual(report["status"], "FAIL")
            self.assertIn("PASS", report["message"])

    def test_detect_groups_rejects_invalid_json(self):
        with tempfile.TemporaryDirectory() as raw:
            inventory = Path(raw) / "inventory.json"
            inventory.write_text("{not-json", encoding="utf-8")
            report = self.run_cli("detect-groups", "--inventory", inventory, expected=1)
            self.assertEqual(report["status"], "FAIL")

    def test_detect_groups_rejects_non_object_entry(self):
        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            inventory = self.write_inventory(base, ["not-an-entry"])
            report = self.run_cli("detect-groups", "--inventory", inventory, expected=1)
            self.assertEqual(report["status"], "FAIL")
            self.assertIn("object", report["message"])

    def test_detect_groups_rejects_malformed_inventory_entry(self):
        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            inventory = base / "inventory.json"
            inventory.write_text(
                json.dumps({"status": "PASS", "inventory": [{"name": "missing-path"}]}),
                encoding="utf-8",
            )
            report = self.run_cli("detect-groups", "--inventory", inventory, expected=1)
            self.assertEqual(report["status"], "FAIL")
            self.assertIn("path", report.get("message", "") + " " + " ".join(report.get("details", [])))


    def test_validate_council_verdict_accepts_inline_empty_list(self):
        # Acceptance F1: `absorbed: []` must be a true empty list, not the string "[]".
        with tempfile.TemporaryDirectory() as raw:
            verdict = self.verdict_file(Path(raw), """---
verdict: MERGE
survivors:
  - survivor
absorbed: []
gates_passed:
  - loss-check
---""")
            report = self.run_cli("validate-council-verdict", "--verdict", verdict)
            self.assertEqual(report["status"], "PASS")
            self.assertEqual(report["absorbed"], [])
            self.assertEqual(report["gates_passed"], ["loss-check"])

    def test_validate_council_verdict_no_frontmatter_hints_machine_format(self):
        # Acceptance F2: the no-frontmatter error must point at the machine-readable
        # declaration contract, not leave the user guessing why a prose file failed.
        with tempfile.TemporaryDirectory() as raw:
            verdict = Path(raw) / "prose.md"
            verdict.write_text("# Council transcript\n\nThe council decided to merge.\n", encoding="utf-8")
            report = self.run_cli("validate-council-verdict", "--verdict", verdict, expected=1)
            self.assertEqual(report["status"], "FAIL")
            joined = " ".join(report["errors"])
            self.assertIn("no frontmatter block", joined)
            self.assertIn("council-verdict.schema.json", joined)

    def test_check_package_rejects_corrupted_schema_content(self):
        # Acceptance F3: check-package must fail when a bundled schema exists but
        # its content is not valid JSON (presence-only checking missed this).
        with tempfile.TemporaryDirectory() as raw:
            package = Path(raw) / "package"
            package.mkdir()
            self.make_package(package)
            (package / "schemas" / "manifest.schema.json").write_text("{invalid json", encoding="utf-8")
            report = self.run_cli("check-package", "--root", package, expected=1)
            self.assertEqual(report["status"], "FAIL")
            self.assertIn("schemas/manifest.schema.json", report["invalid_files"])
            self.assertEqual(report["missing_files"], [])
    def test_check_master_valid_passes(self):
        with tempfile.TemporaryDirectory() as raw:
            skill_dir = Path(raw) / "good-master"
            (skill_dir / "references").mkdir(parents=True)
            (skill_dir / "references" / "format.md").write_text("rules\n", encoding="utf-8")
            (skill_dir / "SKILL.md").write_text(
                "---\nname: good-master\ndescription: Deterministic report generator with a fixed template.\nversion: \"1.0.0\"\n---\n"
                "# good-master\nSee `references/format.md`.\n",
                encoding="utf-8",
            )
            report = self.run_cli("check-master", "--draft", skill_dir / "SKILL.md")
            self.assertEqual(report["status"], "PASS")
            self.assertEqual(report["gates"]["G0"]["status"], "PASS")
            self.assertEqual(report["gates"]["G1"]["status"], "PASS")
            self.assertEqual(report["gates"]["G3"]["status"], "PASS")

    def test_check_master_rejects_name_mismatch_unquoted_version_and_long_desc(self):
        with tempfile.TemporaryDirectory() as raw:
            skill_dir = Path(raw) / "dir-name"
            skill_dir.mkdir()
            long_desc = "x" * 1100
            (skill_dir / "SKILL.md").write_text(
                f"---\nname: Different-Name\ndescription: {long_desc}\nversion: 1.0.0\n---\n# body\n",
                encoding="utf-8",
            )
            report = self.run_cli("check-master", "--draft", skill_dir / "SKILL.md", expected=1)
            self.assertEqual(report["status"], "FAIL")
            g0 = " ".join(report["gates"]["G0"]["details"])
            self.assertIn("name ('Different-Name') != directory name ('dir-name')", g0)
            self.assertIn("longer than 1024", g0)
            self.assertIn("QUOTED string", " ".join(report["gates"]["G3"]["details"]))

    def test_check_master_rejects_missing_reference_and_xml_description(self):
        with tempfile.TemporaryDirectory() as raw:
            skill_dir = Path(raw) / "bad-ref"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                "---\nname: bad-ref\ndescription: has <xml> angle brackets.\nversion: \"1.0.0\"\n---\n# bad-ref\nSee `references/missing.md`.\n",
                encoding="utf-8",
            )
            report = self.run_cli("check-master", "--draft", skill_dir / "SKILL.md", expected=1)
            self.assertEqual(report["status"], "FAIL")
            g0 = " ".join(report["gates"]["G0"]["details"])
            self.assertIn("XML angle brackets", g0)
            self.assertIn("referenced file missing", g0)

    def test_golden_gate_all_cells_match_passes(self):
        with tempfile.TemporaryDirectory() as raw:
            work = Path(raw) / "work"
            (work / "master").mkdir(parents=True)
            (work / "src-a").mkdir(parents=True)
            (work / "master" / "gen.py").write_text(
                "import sys\nargs=dict(zip(sys.argv[1::2],sys.argv[2::2]))\nprint(args.get('--owner','?'), args.get('--sprint','?'))\n",
                encoding="utf-8",
            )
            (work / "src-a" / "gen.py").write_text(
                "import sys\nargs=dict(zip(sys.argv[1::2],sys.argv[2::2]))\nprint(args.get('--owner','?'), args.get('--sprint','?'))\n",
                encoding="utf-8",
            )
            manifest = Path(raw) / "golden.json"
            manifest.write_text(json.dumps({
                "schema": "skills-catalog-golden-1",
                "master": {"name": "master", "runner": [sys.executable, "master/gen.py"]},
                "sources": [{"name": "src-a", "runner": [sys.executable, "src-a/gen.py"]}],
                "inputs": [{"id": "c1", "args": ["--owner", "alice", "--sprint", "S1"]}],
                "allow_runners": True,
                "timeout_seconds": 30,
            }), encoding="utf-8")
            report = self.run_cli("golden-gate", "--manifest", manifest, "--workdir", work)
            self.assertEqual(report["status"], "PASS")
            self.assertTrue(report["absorption_authorized"])
            self.assertEqual(report["matched"], 1)
            self.assertEqual(report["total"], 1)

    def test_golden_gate_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as raw:
            work = Path(raw) / "work"
            (work / "master").mkdir(parents=True)
            (work / "src-b").mkdir(parents=True)
            (work / "master" / "gen.py").write_text("print('MASTER OUTPUT')\n", encoding="utf-8")
            (work / "src-b" / "gen.py").write_text("print('DIFFERENT OUTPUT')\n", encoding="utf-8")
            manifest = Path(raw) / "golden.json"
            manifest.write_text(json.dumps({
                "schema": "skills-catalog-golden-1",
                "master": {"name": "master", "runner": [sys.executable, "master/gen.py"]},
                "sources": [{"name": "src-b", "runner": [sys.executable, "src-b/gen.py"]}],
                "inputs": [{"id": "c1", "args": []}],
                "allow_runners": True,
                "timeout_seconds": 30,
            }), encoding="utf-8")
            report = self.run_cli("golden-gate", "--manifest", manifest, "--workdir", work, expected=1)
            self.assertEqual(report["status"], "FAIL")
            self.assertFalse(report["absorption_authorized"])
            self.assertEqual(report["matched"], 0)

    def test_golden_gate_refuses_shell_metachar_runner(self):
        with tempfile.TemporaryDirectory() as raw:
            work = Path(raw) / "work"
            work.mkdir()
            manifest = Path(raw) / "golden.json"
            manifest.write_text(json.dumps({
                "schema": "skills-catalog-golden-1",
                "master": {"name": "master", "runner": [sys.executable, "master/gen.py"]},
                "sources": [{"name": "evil", "runner": [sys.executable, "gen.py; rm -rf x"]}],
                "inputs": [{"id": "c1", "args": []}],
                "allow_runners": True,
                "timeout_seconds": 30,
            }), encoding="utf-8")
            report = self.run_cli("golden-gate", "--manifest", manifest, "--workdir", work, expected=1)
            self.assertEqual(report["status"], "FAIL")
            self.assertEqual(report["total"], 0)
            self.assertIn("shell metacharacters", " ".join(report["errors"]))

    def test_benchmark_go_passes(self):
        with tempfile.TemporaryDirectory() as raw:
            bundle = Path(raw) / "b.json"
            bundle.write_text(json.dumps({
                "schema": "skills-catalog-benchmark-1",
                "runs_per_cell": 3,
                "cells": [
                    {"id": "p1", "kind": "master_vs_source", "source": "src-a", "runs": 3, "verdict": "WIN"},
                    {"id": "p2", "kind": "master_vs_source", "source": "src-a", "runs": 3, "verdict": "TIE"},
                    {"id": "b1", "kind": "master_vs_baseline", "runs": 3, "verdict": "WIN"},
                ],
            }), encoding="utf-8")
            report = self.run_cli("benchmark", "--bundle", bundle)
            self.assertEqual(report["status"], "PASS")
            self.assertEqual(report["verdict"], "GO")

    def test_benchmark_no_go_on_loss(self):
        with tempfile.TemporaryDirectory() as raw:
            bundle = Path(raw) / "b.json"
            bundle.write_text(json.dumps({
                "schema": "skills-catalog-benchmark-1",
                "runs_per_cell": 3,
                "cells": [
                    {"id": "p1", "kind": "master_vs_source", "source": "src-a", "runs": 3, "verdict": "LOSS"},
                    {"id": "b1", "kind": "master_vs_baseline", "runs": 3, "verdict": "WIN"},
                ],
            }), encoding="utf-8")
            report = self.run_cli("benchmark", "--bundle", bundle, expected=1)
            self.assertEqual(report["status"], "FAIL")
            self.assertEqual(report["verdict"], "NO-GO")
            self.assertIn("promotion blocked", " ".join(report["errors"]))

    def test_benchmark_no_go_when_source_beats_master(self):
        with tempfile.TemporaryDirectory() as raw:
            bundle = Path(raw) / "b.json"
            bundle.write_text(json.dumps({
                "schema": "skills-catalog-benchmark-1",
                "runs_per_cell": 3,
                "cells": [
                    {"id": "p1", "kind": "master_vs_source", "source": "src-a", "runs": 3, "verdict": "LOSS"},
                    {"id": "p2", "kind": "master_vs_source", "source": "src-a", "runs": 3, "verdict": "LOSS"},
                    {"id": "b1", "kind": "master_vs_baseline", "runs": 3, "verdict": "WIN"},
                ],
            }), encoding="utf-8")
            report = self.run_cli("benchmark", "--bundle", bundle, expected=1)
            self.assertEqual(report["status"], "FAIL")
            self.assertIn("does not beat the best source", " ".join(report["errors"]))

    def test_benchmark_rejects_runs_lt_3(self):
        with tempfile.TemporaryDirectory() as raw:
            bundle = Path(raw) / "b.json"
            bundle.write_text(json.dumps({
                "schema": "skills-catalog-benchmark-1",
                "runs_per_cell": 2,
                "cells": [{"id": "p1", "kind": "master_vs_source", "source": "src-a", "runs": 2, "verdict": "WIN"}],
            }), encoding="utf-8")
            report = self.run_cli("benchmark", "--bundle", bundle, expected=1)
            self.assertEqual(report["status"], "FAIL")
            self.assertIn("runs_per_cell", " ".join(report["errors"]))


    def test_golden_gate_refuses_without_allow_runners(self):
        # fail-closed: runner execution is DISABLED by default until the manifest
        # explicitly opts in with allow_runners: true.
        with tempfile.TemporaryDirectory() as raw:
            work = Path(raw) / "work"
            work.mkdir()
            manifest = Path(raw) / "golden.json"
            manifest.write_text(json.dumps({
                "schema": "skills-catalog-golden-1",
                "master": {"name": "master", "runner": [sys.executable, "master/gen.py"]},
                "sources": [{"name": "src-a", "runner": [sys.executable, "src-a/gen.py"]}],
                "inputs": [{"id": "c1", "args": []}],
                "timeout_seconds": 30,
            }), encoding="utf-8")
            report = self.run_cli("golden-gate", "--manifest", manifest, "--workdir", work, expected=1)
            self.assertEqual(report["status"], "FAIL")
            self.assertEqual(report["total"], 0)
            self.assertIn("DISABLED by default", " ".join(report["errors"]))

    def test_golden_gate_rejects_inline_code_runner(self):
        # a benign argv such as ["python", "-c", "..."] would run arbitrary code
        # with no shell metacharacters; inline-code executor args are refused.
        with tempfile.TemporaryDirectory() as raw:
            work = Path(raw) / "work"
            work.mkdir()
            manifest = Path(raw) / "golden.json"
            manifest.write_text(json.dumps({
                "schema": "skills-catalog-golden-1",
                "allow_runners": True,
                "master": {"name": "master", "runner": [sys.executable, "master/gen.py"]},
                "sources": [{"name": "evil", "runner": [sys.executable, "-c", "import os; os.system('x')"]}],
                "inputs": [{"id": "c1", "args": []}],
                "timeout_seconds": 30,
            }), encoding="utf-8")
            report = self.run_cli("golden-gate", "--manifest", manifest, "--workdir", work, expected=1)
            self.assertEqual(report["status"], "FAIL")
            self.assertEqual(report["total"], 0)
            self.assertIn("inline-code executor argument", " ".join(report["errors"]))


class RepairCliTests(unittest.TestCase):
    def setUp(self):
        self.raw = tempfile.mkdtemp()
        self.env = dict(os.environ)
        # Speed up polling loop in cmd_repair so tests don't hang
        self.env["CATALOG_GOVERNANCE_REPAIR_POLL_SECONDS"] = "0.5"
        self.base = Path(self.raw)

    def tearDown(self):
        shutil.rmtree(self.raw, ignore_errors=True)

    def run_repair(self, *args, expected=0, timeout=20):
        result = subprocess.run(
            [sys.executable, str(TOOL), "repair", *map(str, args)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
            env=self.env,
            timeout=timeout,
        )
        self.assertEqual(
            result.returncode,
            expected,
            "stdout=%s stderr=%s" % (result.stdout, result.stderr),
        )
        return json.loads(result.stdout)

    def write_loss_report(self, draft: Path, sources: list[dict]):
        loss_report = self.base / "loss.json"
        loss_report.write_text(json.dumps({
            "schema": "skills-catalog-loss-check-1",
            "draft": str(draft),
            "checks": sources,
            "status": "REVIEW",
            "manual_review_required": True,
        }), encoding="utf-8")
        return loss_report

    def test_repair_all_defects_fixed_after_round_1_passes(self):
        # Initial state: defect present (missing heading). Fix it before repair runs.
        source = self.base / "source.md"
        draft = self.base / "draft.md"
        full_content = "# Required Heading\n\nkeep alpha beta\n```bash\nfind x\n```\n"
        bad_content = "# Required Heading\n\nkeep alpha beta\n```bash\nsomething else\n```\n"
        source.write_text(full_content, encoding="utf-8")
        draft.write_text(bad_content, encoding="utf-8")

        # We want the FIRST round to PASS, so pre-fix the draft to be identical to source
        draft.write_text(full_content, encoding="utf-8")

        loss_report = self.write_loss_report(draft, [{
            "source": str(source),
            "draft_sha256": hashlib.sha256(draft.read_text(encoding="utf-8").encode("utf-8")).hexdigest(),
            "minimum_overlap": 0.35,
        }])

        report = self.run_repair("--loss-report", loss_report, "--draft", draft, "--source", source)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["rounds_run"], 1)
        self.assertEqual(report["schema"], "skills-catalog-repair-1")

    def test_repair_one_defect_persists_escalates_after_3_rounds(self):
        source = self.base / "source.md"
        draft = self.base / "draft.md"
        full_content = "# Required Heading\n\nkeep alpha beta\n```bash\nfind x\n```\n"
        bad_content = "# Required Heading\n\nkeep missing stuff\n```bash\nwrong\n```\n"
        source.write_text(full_content, encoding="utf-8")
        draft.write_text(bad_content, encoding="utf-8")

        loss_report = self.write_loss_report(draft, [{
            "source": str(source),
            "draft_sha256": hashlib.sha256(draft.read_text(encoding="utf-8").encode("utf-8")).hexdigest(),
            "minimum_overlap": 0.35,
        }])

        report = self.run_repair("--loss-report", loss_report, "--draft", draft, "--source", source, timeout=30)
        self.assertEqual(report["status"], "ESCALATE")
        self.assertEqual(report["rounds_run"], 3)
        # Ensure round 4 never executed
        for c in report["checks"]:
            self.assertLessEqual(len(c["verdicts"]), 3)
        self.assertGreater(len(report["defects"]), 0)

    def test_repair_recovers_after_modification_round_2(self):
        source = self.base / "source.md"
        draft = self.base / "draft.md"
        full_content = "# Required Heading\n\nkeep alpha beta\n```bash\nfind x\n```\n"
        bad_content = "# Required Heading\n\nkeep missing stuff\n```bash\nwrong\n```\n"
        source.write_text(full_content, encoding="utf-8")
        draft.write_text(bad_content, encoding="utf-8")

        loss_report = self.write_loss_report(draft, [{
            "source": str(source),
            "draft_sha256": hashlib.sha256(bad_content.encode("utf-8")).hexdigest(),
            "minimum_overlap": 0.35,
        }])

        # Prepare arguments for direct function call
        args = argparse.Namespace(
            loss_report=str(loss_report),
            draft=str(draft),
            source=[str(source)],
            allow_draft_change=False,
            output=None
        )

        # We mock Path.read_text to return:
        # 1. bad_content (initial check in cmd_repair)
        # 2. bad_content (Round 1 execution)
        # 3. full_content (Poll in Round 1 sees change)
        # 4. full_content (Round 2 execution)
        
        # We need to mock Path.read_text *only* for our target files
        original_read_text = Path.read_text
        def side_effect(self_obj, *args, **kwargs):
            p_str = str(self_obj)
            if p_str.endswith("draft.md"):
                call_count[p_str] = call_count.get(p_str, 0) + 1
                if call_count[p_str] <= 2:
                    return bad_content
                return full_content
            return original_read_text(self_obj, *args, **kwargs)

        call_count = {}
        with patch("scripts.catalog_governance.Path.read_text", autospec=True, side_effect=side_effect):
            with patch("time.sleep"):  # Skip actual sleeping
                # Capture stdout to parse JSON result
                import io
                from contextlib import redirect_stdout
                f = io.StringIO()
                with redirect_stdout(f):
                    status_code = GOVERNANCE.cmd_repair(args)
                
                report = json.loads(f.getvalue())
                self.assertEqual(status_code, 0)
                self.assertEqual(report["status"], "PASS")
                self.assertEqual(report["rounds_run"], 2)

    def test_repair_refuses_when_draft_hash_changed_without_flag(self):
        source = self.base / "source.md"
        draft = self.base / "draft.md"
        full_content = "# Required Heading\n\nkeep alpha beta\n```bash\nfind x\n```\n"
        source.write_text(full_content, encoding="utf-8")
        draft.write_text(full_content, encoding="utf-8")

        loss_report = self.write_loss_report(draft, [{
            "source": str(source),
            "draft_sha256": "deadbeef" * 8,  # wrong hash to trigger refusal
            "minimum_overlap": 0.35,
        }])

        report = self.run_repair("--loss-report", loss_report, "--draft", draft, "--source", source, expected=1)
        self.assertEqual(report["status"], "FAIL")
        self.assertIn("draft hash changed", " ".join(report.get("errors", [])))

    def test_repair_allows_draft_change_with_flag(self):
        source = self.base / "source.md"
        draft = self.base / "draft.md"
        full_content = "# Required Heading\n\nkeep alpha beta\n```bash\nfind x\n```\n"
        source.write_text(full_content, encoding="utf-8")
        draft.write_text(full_content, encoding="utf-8")

        loss_report = self.write_loss_report(draft, [{
            "source": str(source),
            "draft_sha256": "deadbeef" * 8,
            "minimum_overlap": 0.35,
        }])

        report = self.run_repair(
            "--loss-report", loss_report, "--draft", draft, "--source", source,
            "--allow-draft-change",
        )
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["rounds_run"], 1)

    def test_repair_malformed_loss_report_fails(self):
        draft = self.base / "draft.md"
        draft.write_text("anything", encoding="utf-8")
        bad = self.base / "bad.json"
        bad.write_text("not json {{{", encoding="utf-8")
        report = self.run_repair("--loss-report", bad, "--draft", draft, expected=1)
        self.assertEqual(report["status"], "FAIL")
        self.assertIn("malformed loss-report", " ".join(report.get("errors", [])))

    def test_repair_empty_checks_fails(self):
        draft = self.base / "draft.md"
        draft.write_text("anything", encoding="utf-8")
        empty = self.base / "empty.json"
        empty.write_text(json.dumps({"schema": "skills-catalog-loss-check-1", "checks": []}), encoding="utf-8")
        report = self.run_repair("--loss-report", empty, "--draft", draft, expected=1)
        self.assertEqual(report["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()
