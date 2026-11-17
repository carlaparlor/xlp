"""Live dogfood self-test running xlp-gate strictly against the real XLP repository.

@category: integration
@category: schema
"""

from __future__ import annotations

import unittest

from tools.xlp_gate.registry import build_default_registry
from tools.xlp_gate.runner import run_gate
from tools.xlp_gate.tests.helpers import REAL_REPO_ROOT


class TestSelfDogfood(unittest.TestCase):
    def test_real_repository_passes_strict_gate_with_zero_findings(self) -> None:
        report = run_gate(REAL_REPO_ROOT, strict=True, run_tests=False)
        self.assertTrue(
            report.passed,
            f"Real repository failed xlp-gate:\n"
            + "\n".join(f"  {f.rule_id} ({f.path}): {f.message}" for f in report.findings),
        )
        self.assertEqual(report.error_count, 0)
        self.assertEqual(report.warning_count, 0)
        self.assertEqual(len(report.waived_findings), 0)

    def test_all_39_rules_registered(self) -> None:
        registry = build_default_registry()
        self.assertEqual(len(registry.rule_ids()), 39)


if __name__ == "__main__":
    unittest.main()
