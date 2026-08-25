"""V2.2 grade-skill tests: grade-skill command and helpers."""
import json
import tempfile
import unittest
from pathlib import Path

import test_catalog_governance as base  # reuses ROOT/TOOL/GOVERNANCE harness

GOVERNANCE = base.GOVERNANCE
ROOT = base.ROOT
TOOL = base.TOOL


class GradeSkillUnitTests(unittest.TestCase):
    def test_normalization_crlf_and_trailing_ws(self):
        # Test normalize_text helper directly
        import sys
        sys.path.insert(0, str(ROOT / "scripts"))
        from catalog_governance import normalize_text
        self.assertEqual(normalize_text("Hello\r\nWorld  \n"), "Hello\nWorld")
        self.assertEqual(normalize_text("Line1  \nLine2  \r\n"), "Line1\nLine2")

    def test_fenced_block_extraction(self):
        import sys
        sys.path.insert(0, str(ROOT / "scripts"))
        from catalog_governance import extract_output_block
        skill = """---
name: test
---
# Skill
```output
Exact content
```
"""
        # extraction works
        self.assertEqual(extract_output_block(skill), "Exact content")

    def test_unclosed_fence_fails(self):
        import sys
        sys.path.insert(0, str(ROOT / "scripts"))
        from catalog_governance import extract_output_block
        skill = """---
name: test
---
```output
No closing
"""
        with self.assertRaises(ValueError) as cm:
            extract_output_block(skill)
        self.assertEqual(str(cm.exception), "unclosed_fence")

    def test_nested_fence_fails(self):
        import sys
        sys.path.insert(0, str(ROOT / "scripts"))
        from catalog_governance import extract_output_block
        skill = """---
name: test
---
```output
```nested
```
"""
        with self.assertRaises(ValueError) as cm:
            extract_output_block(skill)
        self.assertEqual(str(cm.exception), "nested_fence")

    def test_no_output_block_fails(self):
        import sys
        sys.path.insert(0, str(ROOT / "scripts"))
        from catalog_governance import extract_output_block
        skill = """---
name: test
---
```other
content
```
"""
        with self.assertRaises(ValueError) as cm:
            extract_output_block(skill)
        self.assertEqual(str(cm.exception), "no_output_block")


class GradeSkillCliTests(base.GovernanceCliTests):
    def _run_grade(self, skill_text: str, fixtures: list[dict], expected=0):
        with tempfile.TemporaryDirectory() as td:
            skill_dir = Path(td) / "skill"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(skill_text, encoding="utf-8")
            fixtures_path = Path(td) / "fixtures.json"
            fixtures_path.write_text(json.dumps(fixtures), encoding="utf-8")
            return self.run_cli("grade-skill", "--path", skill_dir, "--fixtures", fixtures_path, expected=expected)

    def test_exact_output_pass(self):
        skill = """---
name: test-skill
allowed-tools: [read]
---
# Test Skill
```output
Hello, world!
```
"""
        fixtures = [{
            "fixture_id": "f1",
            "input": {"prompt": "say hello"},
            "expect_exact_output": "Hello, world!",
        }]
        report = self._run_grade(skill, fixtures)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["verdict"], "GO")
        self.assertEqual(report["summary"]["passed"], 1)

    def test_exact_output_fail_mismatch(self):
        skill = """---
name: test-skill
---
# Test Skill
```output
Hello, world!
```
"""
        fixtures = [{
            "fixture_id": "f1",
            "input": {"prompt": "say hello"},
            "expect_exact_output": "Goodbye!",
        }]
        report = self._run_grade(skill, fixtures, expected=1)
        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(report["verdict"], "NO-GO")
        self.assertEqual(report["fixtures"][0]["reason"], "output_mismatch")

    def test_normalization_crlf_trailing_ws(self):
        skill = """---
name: test-skill
---
# Test Skill
```output
Line1  
Line2
```
"""
        # Fixture uses LF and no trailing spaces; trailing newline from fenced block is preserved
        fixtures = [{
            "fixture_id": "f1",
            "input": {"prompt": "x"},
            "expect_exact_output": "Line1\nLine2\n",
        }]
        report = self._run_grade(skill, fixtures)
        self.assertEqual(report["status"], "PASS")

    def test_case_insensitive_flag(self):
        skill = """---
name: test-skill
---
# Test Skill
```output
HELLO WORLD
```
"""
        fixtures = [{
            "fixture_id": "f1",
            "input": {"prompt": "x"},
            "expect_exact_output": "hello world",
            "case_sensitive": False,
        }]
        report = self._run_grade(skill, fixtures)
        self.assertEqual(report["status"], "PASS")

    def test_expected_tools_pass(self):
        skill = """---
name: test-skill
allowed-tools: [read, write, bash]
---
# Test Skill
```output
ignored
```
"""
        fixtures = [{
            "fixture_id": "t1",
            "input": {"prompt": "x"},
            "expected_tools": ["read", "write"],
        }]
        report = self._run_grade(skill, fixtures)
        self.assertEqual(report["status"], "PASS")

    def test_expected_tools_empty_intersection_fails(self):
        skill = """---
name: test-skill
allowed-tools: [read]
---
# Test Skill
```output
ignored
```
"""
        fixtures = [{
            "fixture_id": "t1",
            "input": {"prompt": "x"},
            "expected_tools": ["write"],
        }]
        report = self._run_grade(skill, fixtures, expected=1)
        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(report["fixtures"][0]["reason"], "empty_intersection")

    def test_expected_tools_missing_tools_fails(self):
        skill = """---
name: test-skill
allowed-tools: [read]
---
# Test Skill
```output
ignored
```
"""
        fixtures = [{
            "fixture_id": "t1",
            "input": {"prompt": "x"},
            "expected_tools": ["read", "write"],
        }]
        report = self._run_grade(skill, fixtures, expected=1)
        self.assertEqual(report["status"], "FAIL")
        self.assertIn("missing_tools", report["fixtures"][0]["reason"])

    def test_no_tools_declared_fails(self):
        skill = """---
name: test-skill
---
# Test Skill
```output
ignored
```
"""
        fixtures = [{
            "fixture_id": "t1",
            "input": {"prompt": "x"},
            "expected_tools": ["read"],
        }]
        report = self._run_grade(skill, fixtures, expected=1)
        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(report["fixtures"][0]["reason"], "no_tools_declared")

    def test_unclosed_fence_fails_fixture(self):
        skill = """---
name: test-skill
---
# Test Skill
```output
unclosed
"""
        fixtures = [{
            "fixture_id": "f1",
            "input": {"prompt": "x"},
            "expect_exact_output": "anything",
        }]
        report = self._run_grade(skill, fixtures, expected=1)
        self.assertEqual(report["status"], "FAIL")
        self.assertIn("skill_output_extraction_failed: unclosed_fence", report["fixtures"][0]["reason"])

    def test_nested_fence_fails_fixture(self):
        skill = """---
name: test-skill
---
# Test Skill
```output
```nested
```
"""
        fixtures = [{
            "fixture_id": "f1",
            "input": {"prompt": "x"},
            "expect_exact_output": "anything",
        }]
        report = self._run_grade(skill, fixtures, expected=1)
        self.assertEqual(report["status"], "FAIL")
        self.assertIn("nested_fence", report["fixtures"][0]["reason"])

    def test_no_output_block_fails_fixture(self):
        skill = """---
name: test-skill
---
# Test Skill
```other
content
```
"""
        fixtures = [{
            "fixture_id": "f1",
            "input": {"prompt": "x"},
            "expect_exact_output": "anything",
        }]
        report = self._run_grade(skill, fixtures, expected=1)
        self.assertEqual(report["status"], "FAIL")
        self.assertIn("no_output_block", report["fixtures"][0]["reason"])

    def test_fixture_schema_validation_rejects_both_modes(self):
        fixtures = [{
            "fixture_id": "f1",
            "input": {"prompt": "x"},
            "expect_exact_output": "a",
            "expected_tools": ["read"],
        }]
        report = self._run_grade("""---
name: t
---
```output
a
```
""", fixtures, expected=1)
        self.assertEqual(report["status"], "FAIL")
        self.assertIn("both expect_exact_output and expected_tools", " ".join(report["errors"]))

    def test_fixture_schema_validation_rejects_missing_mode(self):
        fixtures = [{
            "fixture_id": "f1",
            "input": {"prompt": "x"},
        }]
        report = self._run_grade("""---
name: t
---
```output
a
```
""", fixtures, expected=1)
        self.assertEqual(report["status"], "FAIL")
        self.assertIn("neither expect_exact_output nor expected_tools", " ".join(report["errors"]))

    def test_deterministic_report(self):
        skill = """---
name: test-skill
---
# Test Skill
```output
Same output
```
"""
        fixtures = [{
            "fixture_id": "f1",
            "input": {"prompt": "x"},
            "expect_exact_output": "Same output",
        }]
        r1 = self._run_grade(skill, fixtures)
        r2 = self._run_grade(skill, fixtures)
        # Remove skill_sha256 which is same anyway, compare rest
        r1.pop("skill_sha256", None)
        r2.pop("skill_sha256", None)
        self.assertEqual(r1, r2)

    def test_report_labeling_present(self):
        skill = """---
name: test-skill
---
# Test Skill
```output
x
```
"""
        fixtures = [{
            "fixture_id": "f1",
            "input": {"prompt": "x"},
            "expect_exact_output": "x",
        }]
        report = self._run_grade(skill, fixtures)
        self.assertIn("labeling", report)
        self.assertEqual(report["labeling"]["scope"], "structural grading only")
        self.assertEqual(report["labeling"]["behavioral_claims"], "advisory")


if __name__ == "__main__":
    unittest.main()