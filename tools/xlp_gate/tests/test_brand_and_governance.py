"""Positive and adversarial tests for Brand (BRD-001..003) and Governance (GOV-001..004) rules.

@category: unit
@category: adversarial
"""

from __future__ import annotations

import os
import unittest

from tools.xlp_gate.runner import run_gate
from tools.xlp_gate.scaffold import scaffold_plugin
from tools.xlp_gate.tests.helpers import (
    check_rule,
    create_compliant_workspace,
    read_json,
    rule_ids_in,
    write_json,
)


class TestBrandAndGovernanceRules(unittest.TestCase):
    def test_brd_001_positive(self) -> None:
        tmp, root = create_compliant_workspace()
        with tmp:
            rep = check_rule(root, "BRD-001")
            self.assertTrue(rep.passed, rep.findings)

    def test_brd_001_adversarial_wrong_brand(self) -> None:
        tmp, root = create_compliant_workspace()
        with tmp:
            bpath = root / "governance" / "brand.json"
            data = read_json(bpath)
            data["brand_name"] = "wrongbrand"
            write_json(bpath, data)
            rep = check_rule(root, "BRD-001")
            self.assertIn("BRD-001", rule_ids_in(rep))

    def test_brd_002_positive(self) -> None:
        tmp, root = create_compliant_workspace(with_plugin=True)
        with tmp:
            rep = check_rule(root, "BRD-002")
            self.assertTrue(rep.passed, rep.findings)

    def test_brd_002_adversarial_duplicate_code_and_uid(self) -> None:
        tmp, root = create_compliant_workspace(with_plugin=True, plugin_slug="delay_alpha")
        with tmp:
            p2 = scaffold_plugin(root, "delay_beta")
            m1 = read_json(root / "plugins" / "xlp_delay_alpha" / "plugin.manifest.json")
            m2 = read_json(p2 / "plugin.manifest.json")
            m2["plugin_code"] = m1["plugin_code"]
            m2["vst3_controller_uid"] = m2["vst3_component_uid"]
            write_json(p2 / "plugin.manifest.json", m2)
            rep = check_rule(root, "BRD-002")
            self.assertIn("BRD-002", rule_ids_in(rep))
            self.assertGreaterEqual(len(rep.findings), 2)

    def test_brd_003_positive(self) -> None:
        tmp, root = create_compliant_workspace(with_module=True)
        with tmp:
            rep = check_rule(root, "BRD-003")
            self.assertTrue(rep.passed, rep.findings)

    def test_brd_003_adversarial_bad_module_id(self) -> None:
        tmp, root = create_compliant_workspace(with_module=True)
        with tmp:
            mpath = root / "core" / "dsp_core" / "module.manifest.json"
            data = read_json(mpath)
            data["id"] = "other.core.dsp_core"
            write_json(mpath, data)
            rep = check_rule(root, "BRD-003")
            self.assertIn("BRD-003", rule_ids_in(rep))

    def test_gov_001_positive(self) -> None:
        tmp, root = create_compliant_workspace()
        with tmp:
            rep = check_rule(root, "GOV-001")
            self.assertTrue(rep.passed, rep.findings)

    def test_gov_001_adversarial_corrupt_policy_schema(self) -> None:
        tmp, root = create_compliant_workspace()
        with tmp:
            ppath = root / "governance" / "policy.json"
            pol = read_json(ppath)
            pol["unexpected_rogue_field"] = True
            write_json(ppath, pol)
            rep = check_rule(root, "GOV-001")
            self.assertIn("GOV-001", rule_ids_in(rep))

    def test_gov_002_positive(self) -> None:
        tmp, root = create_compliant_workspace()
        with tmp:
            rep = check_rule(root, "GOV-002")
            self.assertTrue(rep.passed, rep.findings)

    def test_gov_002_adversarial_ci_continue_on_error_and_nonexec_hook(self) -> None:
        tmp, root = create_compliant_workspace()
        with tmp:
            ci = root / ".github" / "workflows" / "xlp-gate.yml"
            ci.write_text(ci.read_text(encoding="utf-8") + "\n      continue-on-error: true\n", encoding="utf-8")
            os.chmod(root / ".githooks" / "pre-commit", 0o644)
            rep = check_rule(root, "GOV-002")
            self.assertIn("GOV-002", rule_ids_in(rep))
            self.assertGreaterEqual(len(rep.findings), 2)

    def test_gov_003_positive_valid_waiver_waives_waivable_rule(self) -> None:
        tmp, root = create_compliant_workspace(with_module=True)
        with tmp:
            # Deliberately exceed MOD-006 line limit and waive with a legal ADR-backed waiver.
            big_file = root / "core" / "dsp_core" / "include" / "dsp_core.hpp"
            big_file.write_text("// line\n" * 650, encoding="utf-8")
            write_json(
                root / "governance" / "waivers.json",
                {
                    "schema_version": "1.0.0",
                    "waivers": [
                        {
                            "id": "WAV-0001",
                            "rule_id": "MOD-006",
                            "target_path": "core/dsp_core/include/dsp_core.hpp",
                            "adr_id": "ADR-0002",
                            "justification": "Temporary 30-day transition while splitting SIMD lookup tables into smaller headers.",
                            "created_on": "2026-11-01",
                            "expires_on": "2026-12-01",
                            "owner": "xlp-dsp",
                        }
                    ],
                },
            )
            rep = run_gate(root, only_rules={"GOV-003", "MOD-006"}, today_iso="2026-11-15")
            self.assertTrue(rep.passed, rep.findings)
            self.assertEqual(len(rep.waived_findings), 1)
            self.assertEqual(rep.waived_findings[0].waived_by, "WAV-0001")

    def test_gov_003_adversarial_expired_and_non_waivable_rule(self) -> None:
        tmp, root = create_compliant_workspace()
        with tmp:
            write_json(
                root / "governance" / "waivers.json",
                {
                    "schema_version": "1.0.0",
                    "waivers": [
                        {
                            "id": "WAV-0001",
                            "rule_id": "SCA-001",
                            "target_path": "core/dsp_core",
                            "adr_id": "ADR-0003",
                            "justification": "Attempting to waive a non-waivable real-time safety invariant illegally.",
                            "created_on": "2026-01-01",
                            "expires_on": "2026-02-01",
                            "owner": "rogue",
                        }
                    ],
                },
            )
            rep = check_rule(root, "GOV-003", today_iso="2026-11-15")
            self.assertIn("GOV-003", rule_ids_in(rep))
            self.assertGreaterEqual(len(rep.findings), 2)

    def test_gov_004_positive(self) -> None:
        tmp, root = create_compliant_workspace()
        with tmp:
            rep = check_rule(root, "GOV-004")
            self.assertTrue(rep.passed, rep.findings)

    def test_gov_004_adversarial_weakened_constitutional_floors(self) -> None:
        tmp, root = create_compliant_workspace()
        with tmp:
            ppath = root / "governance" / "policy.json"
            pol = read_json(ppath)
            pol["research"]["min_citations"] = 0
            pol["modularity"]["allow_circular_dependencies"] = True
            pol["realtime_safety"]["require_rt_safety_check"] = False
            pol["waivers"]["non_waivable_rules"] = ["GOV-001"]
            write_json(ppath, pol)
            rep = check_rule(root, "GOV-004")
            self.assertIn("GOV-004", rule_ids_in(rep))
            self.assertGreaterEqual(len(rep.findings), 4)


if __name__ == "__main__":
    unittest.main()
