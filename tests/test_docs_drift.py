import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "scripts" / "check_docs_drift.py"
TOOL = ROOT / "scripts" / "catalog_governance.py"

CHECKER_SPEC = importlib.util.spec_from_file_location("check_docs_drift", CHECKER)
assert CHECKER_SPEC is not None and CHECKER_SPEC.loader is not None
DRIFT = importlib.util.module_from_spec(CHECKER_SPEC)
CHECKER_SPEC.loader.exec_module(DRIFT)

FAKE_CMD = "definitely-not-a-real-command"


class CheckDocsDriftTests(unittest.TestCase):
    def run_checker(self, *args, cwd=None, expected=0):
        result = subprocess.run(
            [sys.executable, str(CHECKER), *map(str, args)],
            cwd=cwd or ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result

    def make_repo(self, directory: Path, skill_text: str) -> Path:
        """Build a minimal repo that passes the checker's layout checks."""
        (directory / "scripts").mkdir(parents=True)
        (directory / "scripts" / "catalog_governance.py").write_text(
            TOOL.read_text(encoding="utf-8"), encoding="utf-8"
        )
        (directory / "SKILL.md").write_text(skill_text, encoding="utf-8")
        return directory

    def make_clone_with_skill(self, skill_text: str) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self._tmpdirs = getattr(self, "_tmpdirs", [])
        self._tmpdirs.append(tmp)
        return self.make_repo(Path(tmp.name), skill_text)

    def tearDown(self):
        for tmp in getattr(self, "_tmpdirs", []):
            tmp.cleanup()

    # --- clean repo case (post-resolution): the current HEAD must PASS ---
    def test_clean_repo_passes(self):
        result = self.run_checker("--json", ".")
        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["undocumented"], [])
        self.assertEqual(report["reported_but_not_implemented"], [])
        self.assertGreaterEqual(len(report["skipped_exempt"]), 10)

    def test_cli_commands_extraction_is_ast_based_and_complete(self):
        cmds = DRIFT.cli_commands(TOOL)
        for name in ("detect-skills", "check-package", "scan-security", "grade-skill"):
            self.assertIn(name, cmds)
        self.assertTrue(len(cmds) >= 26)

    def test_documented_commands_matches_actual_invocation_convention(self):
        text = (
            "Run `python3 scripts/catalog_governance.py check-package --root .` before.\n"
            "```bash\n"
            "python scripts/catalog_governance.py detect-skills --output inventory.json\n"
            "```\n"
            "Also `scripts/catalog_governance.py preflight-moves` is used."
        )
        self.assertEqual(
            DRIFT.documented_commands(text),
            ["check-package", "detect-skills", "preflight-moves"],
        )

    def test_prose_mentions_are_not_counted_as_cli_invocations(self):
        # "install"/"repair"/"benchmark" appear as prose words but not as
        # `catalog_governance.py <cmd>` invocations -- must NOT be counted.
        text = (
            "The install step runs after benchmark. repair is invoked by the dispatch loop.\n"
            "decide on the next action; rollback on failure."
        )
        self.assertEqual(DRIFT.documented_commands(text), [])

    # --- drift detection: documented-but-unimplemented ---
    def test_catches_documented_but_unimplemented_command(self):
        skill = (
            "## Reference\n\n"
            "```bash\n"
            "python scripts/catalog_governance.py check-package --root .\n"
            f"python scripts/catalog_governance.py {FAKE_CMD} --output out.json\n"
            "```\n"
        )
        root = self.make_clone_with_skill(skill)
        result = self.run_checker("--json", ".", cwd=str(root), expected=1)
        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "FAIL")
        # The invented command must be caught as documented-but-unimplemented.
        self.assertIn(FAKE_CMD, report["reported_but_not_implemented"])
        # The temp SKILL.md only documents check-package, so the other real
        # commands legitimately show up as undocumented too -- that is correct.
        self.assertIn("scan-security", report["undocumented"])

    # --- drift detection: implemented-but-undocumented ---
    def test_catches_undocumented_command_without_allowlist(self):
        # A SKILL.md that documents NOTHING. Every non-exempt command becomes undocumented.
        root = self.make_clone_with_skill("no invocation present\n")
        result = self.run_checker("--json", ".", cwd=str(root), expected=1)
        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(len(report["undocumented"]) > 0)
        # A genuinely user-facing command must NOT be silently allowed.
        self.assertIn("scan-security", report["undocumented"])

    def test_allowlist_exemption_respected(self):
        # v2-lifecycle plumbing is exempted; the check must not report it as undocumented.
        root = self.make_clone_with_skill("nothing here\n")
        result = self.run_checker("--json", ".", cwd=str(root), expected=1)
        report = json.loads(result.stdout)
        for cmd in DRIFT.DOC_EXEMPT_COMMANDS:
            self.assertNotIn(cmd, report["undocumented"], cmd)

    def test_layout_missing_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            result = subprocess.run(
                [sys.executable, str(CHECKER), "--json", str(root)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 1)
            report = json.loads(result.stdout)
            self.assertEqual(report["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()