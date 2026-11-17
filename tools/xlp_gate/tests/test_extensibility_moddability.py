"""Positive and adversarial tests for Extensibility (EXT-001..004) and Moddability (MDD-001..004) rules.

@category: unit
@category: adversarial
"""

from __future__ import annotations

import unittest

from tools.xlp_gate.tests.helpers import (
    check_rule,
    create_compliant_workspace,
    read_json,
    rule_ids_in,
    write_json,
)


class TestExtensibilityAndModdabilityRules(unittest.TestCase):
    def test_ext_001_positive(self) -> None:
        tmp, root = create_compliant_workspace(with_plugin=True, with_module=True)
        with tmp:
            rep = check_rule(root, "EXT-001")
            self.assertTrue(rep.passed, rep.findings)

    def test_ext_001_adversarial_invalid_semver_and_abi(self) -> None:
        tmp, root = create_compliant_workspace(with_module=True)
        with tmp:
            mpath = root / "core" / "dsp_core" / "module.manifest.json"
            data = read_json(mpath)
            data["api_version"] = "v1"
            data["abi_version"] = 0
            write_json(mpath, data)
            rep = check_rule(root, "EXT-001")
            self.assertIn("EXT-001", rule_ids_in(rep))
            self.assertGreaterEqual(len(rep.findings), 2)

    def test_ext_002_positive(self) -> None:
        tmp, root = create_compliant_workspace(with_plugin=True)
        with tmp:
            rep = check_rule(root, "EXT-002")
            self.assertTrue(rep.passed, rep.findings)

    def test_ext_002_adversarial_insufficient_and_duplicate_extension_points(self) -> None:
        tmp, root = create_compliant_workspace(with_plugin=True)
        with tmp:
            mpath = root / "plugins" / "xlp_filter_one" / "plugin.manifest.json"
            data = read_json(mpath)
            data["extension_points"] = [data["extension_points"][0]]
            write_json(mpath, data)
            rep = check_rule(root, "EXT-002")
            self.assertIn("EXT-002", rule_ids_in(rep))

    def test_ext_003_positive(self) -> None:
        tmp, root = create_compliant_workspace(with_plugin=True)
        with tmp:
            rep = check_rule(root, "EXT-003")
            self.assertTrue(rep.passed, rep.findings)

    def test_ext_003_adversarial_duplicate_uid_and_bad_bounds(self) -> None:
        tmp, root = create_compliant_workspace(with_plugin=True)
        with tmp:
            ppath = root / "plugins" / "xlp_filter_one" / "params.json"
            pdata = read_json(ppath)
            pdata["parameters"].append(
                {
                    "id": "filter.cutoff_hz",
                    "uid": 1001,  # Duplicate UID!
                    "name": "Cutoff",
                    "type": "float",
                    "min": 100.0,
                    "max": 1000.0,
                    "default": 5000.0,  # Out of range!
                    "unit": "Hz",
                    "automatable": True,
                    "modulatable": True,
                    "description": "Filter cutoff frequency with deliberately invalid default value.",
                }
            )
            write_json(ppath, pdata)
            rep = check_rule(root, "EXT-003")
            self.assertIn("EXT-003", rule_ids_in(rep))
            self.assertGreaterEqual(len(rep.findings), 2)

    def test_ext_004_positive_baseline_compatible_addition(self) -> None:
        tmp, root = create_compliant_workspace(with_plugin=True)
        with tmp:
            ppath = root / "plugins" / "xlp_filter_one" / "params.json"
            baseline = read_json(ppath)
            write_json(root / "governance" / "baselines" / "xlp.filter_one.params.json", baseline)
            # Adding a new parameter while preserving existing ID/UID is valid.
            current = read_json(ppath)
            current["parameters"].append(
                {
                    "id": "output.mix",
                    "uid": 1002,
                    "name": "Dry/Wet Mix",
                    "type": "float",
                    "min": 0.0,
                    "max": 1.0,
                    "default": 1.0,
                    "unit": "%",
                    "automatable": True,
                    "modulatable": True,
                    "description": "Wet and dry signal blend ratio.",
                }
            )
            write_json(ppath, current)
            rep = check_rule(root, "EXT-004")
            self.assertTrue(rep.passed, rep.findings)

    def test_ext_004_adversarial_breaking_param_removal_and_uid_change(self) -> None:
        tmp, root = create_compliant_workspace(with_plugin=True)
        with tmp:
            ppath = root / "plugins" / "xlp_filter_one" / "params.json"
            baseline = read_json(ppath)
            write_json(root / "governance" / "baselines" / "xlp.filter_one.params.json", baseline)
            current = read_json(ppath)
            current["parameters"][0]["uid"] = 9999
            write_json(ppath, current)
            rep = check_rule(root, "EXT-004")
            self.assertIn("EXT-004", rule_ids_in(rep))

    def test_mdd_001_positive(self) -> None:
        tmp, root = create_compliant_workspace(with_plugin=True)
        with tmp:
            rep = check_rule(root, "MDD-001")
            self.assertTrue(rep.passed, rep.findings)

    def test_mdd_001_adversarial_disabled_modding(self) -> None:
        tmp, root = create_compliant_workspace(with_plugin=True)
        with tmp:
            mpath = root / "plugins" / "xlp_filter_one" / "plugin.manifest.json"
            data = read_json(mpath)
            data["modding"]["enabled"] = False
            data["modding"]["surfaces"] = [data["modding"]["surfaces"][0]]
            write_json(mpath, data)
            rep = check_rule(root, "MDD-001")
            self.assertIn("MDD-001", rule_ids_in(rep))
            self.assertGreaterEqual(len(rep.findings), 2)

    def test_mdd_002_positive(self) -> None:
        tmp, root = create_compliant_workspace(with_plugin=True)
        with tmp:
            rep = check_rule(root, "MDD-002")
            self.assertTrue(rep.passed, rep.findings)

    def test_mdd_002_adversarial_privileged_mod_surface_and_unsafe_fallback(self) -> None:
        tmp, root = create_compliant_workspace(with_plugin=True)
        with tmp:
            mpath = root / "plugins" / "xlp_filter_one" / "plugin.manifest.json"
            data = read_json(mpath)
            data["modding"]["surfaces"][0]["allow_network"] = True
            data["modding"]["surfaces"][0]["allow_filesystem"] = True
            data["modding"]["surfaces"][0]["fallback_on_error"] = "crash_host"
            write_json(mpath, data)
            rep = check_rule(root, "MDD-002")
            self.assertIn("MDD-002", rule_ids_in(rep))
            self.assertGreaterEqual(len(rep.findings), 3)

    def test_mdd_003_positive(self) -> None:
        tmp, root = create_compliant_workspace(with_plugin=True)
        with tmp:
            rep = check_rule(root, "MDD-003")
            self.assertTrue(rep.passed, rep.findings)

    def test_mdd_003_adversarial_path_traversal_and_network_mod(self) -> None:
        tmp, root = create_compliant_workspace(with_plugin=True)
        with tmp:
            mod_path = root / "mods" / "hostile_mod" / "mod.manifest.json"
            write_json(
                mod_path,
                {
                    "schema_version": "1.0.0",
                    "id": "rogue.hostile",
                    "name": "Hostile Mod Pack",
                    "version": "1.0.0",
                    "author": "attacker",
                    "target_plugin": "xlp.filter_one",
                    "target_mod_api_version": "1.0.0",
                    "priority": 10,
                    "description": "Adversarial mod requesting illegal network access and path traversal.",
                    "surfaces": ["nonexistent.surface"],
                    "requested_capabilities": {"filesystem": True, "network": True, "max_memory_kb": 9999},
                    "entry_files": ["../../etc/passwd"],
                },
            )
            rep = check_rule(root, "MDD-003")
            self.assertIn("MDD-003", rule_ids_in(rep))
            self.assertGreaterEqual(len(rep.findings), 3)

    def test_mdd_004_positive(self) -> None:
        tmp, root = create_compliant_workspace(with_plugin=True)
        with tmp:
            rep = check_rule(root, "MDD-004")
            self.assertTrue(rep.passed, rep.findings)

    def test_mdd_004_adversarial_stub_modding_doc(self) -> None:
        tmp, root = create_compliant_workspace(with_plugin=True)
        with tmp:
            (root / "plugins" / "xlp_filter_one" / "docs" / "modding.md").write_text(
                "# Modding\n\nShort stub.\n", encoding="utf-8"
            )
            rep = check_rule(root, "MDD-004")
            self.assertIn("MDD-004", rule_ids_in(rep))


if __name__ == "__main__":
    unittest.main()
