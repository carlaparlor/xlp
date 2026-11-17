"""Integration and adversarial tests for Testing rules (TST-001..004), CLI, scaffolding, and Git hooks.

@category: integration
@category: adversarial
"""

from __future__ import annotations

import json
import os
import subprocess
import unittest
from pathlib import Path

from tools.xlp_gate.cli import main as cli_main
from tools.xlp_gate.runner import run_gate
from tools.xlp_gate.scaffold import scaffold_doc_artifact, scaffold_module, scaffold_plugin
from tools.xlp_gate.tests.helpers import (
    check_rule,
    create_compliant_workspace,
    read_json,
    rule_ids_in,
    write_json,
)


class TestTestingRulesCliAndGitHooks(unittest.TestCase):
    def test_tst_001_positive(self) -> None:
        tmp, root = create_compliant_workspace(with_plugin=True)
        with tmp:
            rep = check_rule(root, "TST-001")
            self.assertTrue(rep.passed, rep.findings)

    def test_tst_001_adversarial_empty_test_dir(self) -> None:
        tmp, root = create_compliant_workspace(with_plugin=True)
        with tmp:
            for f in (root / "plugins" / "xlp_filter_one" / "tests").glob("*.py"):
                f.unlink()
            rep = check_rule(root, "TST-001")
            self.assertIn("TST-001", rule_ids_in(rep))

    def test_tst_002_positive(self) -> None:
        tmp, root = create_compliant_workspace(with_plugin=True)
        with tmp:
            rep = check_rule(root, "TST-002")
            self.assertTrue(rep.passed, rep.findings)

    def test_tst_002_adversarial_missing_category_tag(self) -> None:
        tmp, root = create_compliant_workspace(with_plugin=True)
        with tmp:
            tfile = root / "plugins" / "xlp_filter_one" / "tests" / "test_plugin_contract.py"
            tfile.write_text(
                tfile.read_text(encoding="utf-8").replace("@category: rt_safety", ""),
                encoding="utf-8",
            )
            rep = check_rule(root, "TST-002")
            self.assertIn("TST-002", rule_ids_in(rep))

    def test_tst_003_positive_runs_plugin_test_suite(self) -> None:
        tmp, root = create_compliant_workspace(with_plugin=True)
        with tmp:
            # Remove tools/xlp_gate recursive execution in this isolated check by testing only the new plugin
            # after clearing XLP_GATE_IN_TEST_EXEC temporarily.
            old_flag = os.environ.pop("XLP_GATE_IN_TEST_EXEC", None)
            try:
                # Simplify tools/xlp_gate test command inside temp workspace so execution stays fast and isolated.
                tm = root / "tools" / "xlp_gate" / "module.manifest.json"
                td = read_json(tm)
                td["testing"]["command"] = "python3 -m unittest discover -s tools/xlp_gate/tests -p test_schema_validator.py"
                write_json(tm, td)
                rep = run_gate(root, only_rules={"TST-003"}, run_tests=True)
                self.assertTrue(rep.passed, rep.findings)
                self.assertEqual(len(rep.executed_test_commands), 2)
            finally:
                if old_flag is not None:
                    os.environ["XLP_GATE_IN_TEST_EXEC"] = old_flag

    def test_tst_003_adversarial_failing_test_and_zero_test_vacuous_run(self) -> None:
        tmp, root = create_compliant_workspace(with_plugin=True)
        with tmp:
            old_flag = os.environ.pop("XLP_GATE_IN_TEST_EXEC", None)
            try:
                tm = root / "tools" / "xlp_gate" / "module.manifest.json"
                td = read_json(tm)
                td["testing"]["command"] = "python3 -m unittest discover -s tools/xlp_gate/tests -p test_schema_validator.py"
                write_json(tm, td)

                # 1. Failing test suite must fail TST-003
                tfile = root / "plugins" / "xlp_filter_one" / "tests" / "test_plugin_contract.py"
                tfile.write_text(
                    "import unittest\nclass Bad(unittest.TestCase):\n    def test_fail(self):\n        self.fail('boom')\n",
                    encoding="utf-8",
                )
                rep = run_gate(root, only_rules={"TST-003"}, run_tests=True)
                self.assertIn("TST-003", rule_ids_in(rep))

                # 2. Vacuous 0-test run exiting 0 must ALSO fail TST-003
                pmanifest = root / "plugins" / "xlp_filter_one" / "plugin.manifest.json"
                pdata = read_json(pmanifest)
                pdata["testing"]["command"] = "python3 -m unittest discover -s plugins/xlp_filter_one/tests -p nonexistent_*.py"
                write_json(pmanifest, pdata)
                rep_zero = run_gate(root, only_rules={"TST-003"}, run_tests=True)
                self.assertIn("TST-003", rule_ids_in(rep_zero))
                self.assertTrue(any("0 tests" in f.message for f in rep_zero.findings))
            finally:
                if old_flag is not None:
                    os.environ["XLP_GATE_IN_TEST_EXEC"] = old_flag

    def test_tst_004_positive(self) -> None:
        tmp, root = create_compliant_workspace()
        with tmp:
            rep = check_rule(root, "TST-004")
            self.assertTrue(rep.passed, rep.findings)

    def test_tst_004_adversarial_missing_rule_traceability(self) -> None:
        tmp, root = create_compliant_workspace()
        with tmp:
            tpath = root / "governance" / "traceability.json"
            data = read_json(tpath)
            data["rules"] = [r for r in data["rules"] if r["rule_id"] != "BRD-001"]
            write_json(tpath, data)
            rep = check_rule(root, "TST-004")
            self.assertIn("TST-004", rule_ids_in(rep))

    def test_scaffold_plugin_and_module_pass_entire_strict_gate(self) -> None:
        tmp, root = create_compliant_workspace()
        with tmp:
            scaffold_module(root, "core", "math_utils", kind="dsp")
            scaffold_module(root, "adapters", "vst3_shell", kind="adapter")
            scaffold_plugin(root, "tape_sat", category="effect")
            adr = scaffold_doc_artifact(root, "adr", "sample-draft", "Sample Draft Decision")
            res = scaffold_doc_artifact(root, "research", "sample-study", "Sample Study")
            self.assertTrue(adr.is_file())
            self.assertTrue(res.is_file())

            # Remove draft doc scaffolds before full gate check (since draft templates have short text),
            # and verify scaffolded core module + adapter + plugin pass all 38 static rules immediately!
            adr.unlink()
            res.unlink()
            rep = run_gate(root, strict=True, run_tests=False)
            self.assertTrue(rep.passed, rep.findings)

    def test_cli_json_output_and_real_git_hooks_enforcement(self) -> None:
        tmp, root = create_compliant_workspace()
        with tmp:
            # 1. CLI check with JSON report
            json_out = root / "out-report.json"
            rc = cli_main(["--root", str(root), "check", "--strict", "--format", "json", "--json-out", str(json_out)])
            self.assertEqual(rc, 0)
            payload = json.loads(json_out.read_text(encoding="utf-8"))
            self.assertTrue(payload["passed"])
            self.assertEqual(payload["error_count"], 0)

            # 2. Initialize real Git repo and install hooks
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.email", "test@xlp.audio"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "XLP Test"], cwd=root, check=True)
            subprocess.run(["./scripts/install-hooks.sh"], cwd=root, check=True, capture_output=True)
            self.assertEqual(cli_main(["--root", str(root), "verify-hooks"]), 0)

            # 3. Bad commit message MUST be rejected by commit-msg hook
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            bad_msg = subprocess.run(
                ["git", "commit", "-m", "bad non conventional message"],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(bad_msg.returncode, 0)
            self.assertIn("Conventional Commits", bad_msg.stderr)

            # 4. Compliant commit MUST pass pre-commit + commit-msg and append Arena trailer
            good_commit = subprocess.run(
                ["git", "commit", "-m", "arch(gate): initialize xlp enforcement gate"],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(good_commit.returncode, 0, good_commit.stdout + good_commit.stderr)
            log_msg = subprocess.run(
                ["git", "log", "-1", "--pretty=%B"], cwd=root, capture_output=True, text=True, check=True
            ).stdout
            self.assertIn("Co-authored-by: arena-agent", log_msg)

            # 5. Breaking a rule MUST be blocked by pre-commit hook
            (root / "docs" / "explanation" / "architecture-pillars.md").write_text(
                "# Broken\n\nTBD placeholder debt.\n", encoding="utf-8"
            )
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            blocked = subprocess.run(
                ["git", "commit", "-m", "docs(explanation): introduce forbidden placeholder"],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(blocked.returncode, 0)
            self.assertIn("DOC-006", blocked.stdout + blocked.stderr)


if __name__ == "__main__":
    unittest.main()
