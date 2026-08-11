import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "scripts" / "catalog_governance.py"
SCHEMAS = ROOT / "schemas"
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


if __name__ == "__main__":
    unittest.main()
