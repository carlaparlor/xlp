"""Positive and adversarial tests for Modularity rules (MOD-001..MOD-006).

@category: unit
@category: adversarial
"""

from __future__ import annotations

import shutil
import unittest

from tools.xlp_gate.scaffold import scaffold_module, scaffold_plugin
from tools.xlp_gate.tests.helpers import (
    check_rule,
    create_compliant_workspace,
    read_json,
    rule_ids_in,
    write_json,
)


class TestModularityRules(unittest.TestCase):
    def test_mod_001_positive(self) -> None:
        tmp, root = create_compliant_workspace(with_plugin=True, with_module=True)
        with tmp:
            rep = check_rule(root, "MOD-001")
            self.assertTrue(rep.passed, rep.findings)

    def test_mod_001_adversarial_missing_manifest(self) -> None:
        tmp, root = create_compliant_workspace()
        with tmp:
            (root / "modules" / "rogue_unmanifested").mkdir(parents=True)
            rep = check_rule(root, "MOD-001")
            self.assertIn("MOD-001", rule_ids_in(rep))

    def test_mod_002_positive(self) -> None:
        tmp, root = create_compliant_workspace(with_plugin=True, with_module=True)
        with tmp:
            # Plugin legally depending on core/dsp_core
            pmanifest = root / "plugins" / "xlp_filter_one" / "plugin.manifest.json"
            data = read_json(pmanifest)
            data["dependencies"] = ["xlp.core.dsp_core"]
            write_json(pmanifest, data)
            (root / "plugins" / "xlp_filter_one" / "dsp" / "processor.hpp").write_text(
                '#include "core/dsp_core/include/dsp_core.hpp"\n', encoding="utf-8"
            )
            rep = check_rule(root, "MOD-002")
            self.assertTrue(rep.passed, rep.findings)

    def test_mod_002_adversarial_core_imports_plugin_and_cross_plugin_import(self) -> None:
        tmp, root = create_compliant_workspace(with_plugin=True, with_module=True, plugin_slug="alpha")
        with tmp:
            scaffold_plugin(root, "beta")
            # Illegal upward import from core -> plugins
            (root / "core" / "dsp_core" / "include" / "dsp_core.hpp").write_text(
                '#include "plugins/xlp_alpha/dsp/processor.hpp"\n', encoding="utf-8"
            )
            # Illegal cross-plugin import from beta -> alpha
            (root / "plugins" / "xlp_beta" / "dsp" / "processor.hpp").write_text(
                '#include "plugins/xlp_alpha/dsp/processor.hpp"\n', encoding="utf-8"
            )
            rep = check_rule(root, "MOD-002")
            self.assertIn("MOD-002", rule_ids_in(rep))
            self.assertGreaterEqual(len(rep.findings), 2)

    def test_mod_003_positive(self) -> None:
        tmp, root = create_compliant_workspace(with_module=True)
        with tmp:
            scaffold_module(root, "modules", "filter_bank", kind="dsp")
            mpath = root / "modules" / "filter_bank" / "module.manifest.json"
            data = read_json(mpath)
            data["dependencies"] = ["xlp.core.dsp_core"]
            write_json(mpath, data)
            rep = check_rule(root, "MOD-003")
            self.assertTrue(rep.passed, rep.findings)

    def test_mod_003_adversarial_circular_dependency(self) -> None:
        tmp, root = create_compliant_workspace()
        with tmp:
            scaffold_module(root, "modules", "mod_a", kind="dsp")
            scaffold_module(root, "modules", "mod_b", kind="dsp")
            ma = root / "modules" / "mod_a" / "module.manifest.json"
            mb = root / "modules" / "mod_b" / "module.manifest.json"
            da = read_json(ma)
            db = read_json(mb)
            da["dependencies"] = ["xlp.modules.mod_b"]
            db["dependencies"] = ["xlp.modules.mod_a"]
            write_json(ma, da)
            write_json(mb, db)
            rep = check_rule(root, "MOD-003")
            self.assertIn("MOD-003", rule_ids_in(rep))

    def test_mod_003_adversarial_three_node_source_cycle(self) -> None:
        tmp, root = create_compliant_workspace()
        with tmp:
            scaffold_module(root, "modules", "node_a", kind="dsp")
            scaffold_module(root, "modules", "node_b", kind="dsp")
            scaffold_module(root, "modules", "node_c", kind="dsp")
            (root / "modules" / "node_a" / "include" / "node_a.hpp").write_text(
                '#include "modules/node_b/include/node_b.hpp"\n', encoding="utf-8"
            )
            (root / "modules" / "node_b" / "include" / "node_b.hpp").write_text(
                '#include "modules/node_c/include/node_c.hpp"\n', encoding="utf-8"
            )
            (root / "modules" / "node_c" / "include" / "node_c.hpp").write_text(
                '#include "modules/node_a/include/node_a.hpp"\n', encoding="utf-8"
            )
            rep = check_rule(root, "MOD-003")
            self.assertIn("MOD-003", rule_ids_in(rep))

    def test_mod_004_positive(self) -> None:
        tmp, root = create_compliant_workspace(with_plugin=True, with_module=True)
        with tmp:
            pmanifest = root / "plugins" / "xlp_filter_one" / "plugin.manifest.json"
            data = read_json(pmanifest)
            data["dependencies"] = ["xlp.core.dsp_core"]
            write_json(pmanifest, data)
            (root / "plugins" / "xlp_filter_one" / "dsp" / "processor.hpp").write_text(
                '#include "core/dsp_core/include/dsp_core.hpp"\n', encoding="utf-8"
            )
            rep = check_rule(root, "MOD-004")
            self.assertTrue(rep.passed, rep.findings)

    def test_mod_004_adversarial_undeclared_source_import(self) -> None:
        tmp, root = create_compliant_workspace(with_plugin=True, with_module=True)
        with tmp:
            # Imports core/dsp_core without listing it in plugin.manifest.json dependencies
            (root / "plugins" / "xlp_filter_one" / "dsp" / "processor.hpp").write_text(
                '#include "core/dsp_core/include/dsp_core.hpp"\n', encoding="utf-8"
            )
            rep = check_rule(root, "MOD-004")
            self.assertIn("MOD-004", rule_ids_in(rep))

    def test_mod_005_positive(self) -> None:
        tmp, root = create_compliant_workspace(with_plugin=True)
        with tmp:
            rep = check_rule(root, "MOD-005")
            self.assertTrue(rep.passed, rep.findings)

    def test_mod_005_adversarial_dsp_includes_gui_and_missing_ui_dir(self) -> None:
        tmp, root = create_compliant_workspace(with_plugin=True)
        with tmp:
            (root / "plugins" / "xlp_filter_one" / "dsp" / "processor.hpp").write_text(
                '#include <juce_gui_basics/juce_gui_basics.h>\n', encoding="utf-8"
            )
            shutil.rmtree(root / "plugins" / "xlp_filter_one" / "ui")
            rep = check_rule(root, "MOD-005")
            self.assertIn("MOD-005", rule_ids_in(rep))
            self.assertGreaterEqual(len(rep.findings), 2)

    def test_mod_006_positive(self) -> None:
        tmp, root = create_compliant_workspace(with_module=True)
        with tmp:
            rep = check_rule(root, "MOD-006")
            self.assertTrue(rep.passed, rep.findings)

    def test_mod_006_adversarial_oversized_monolith_file(self) -> None:
        tmp, root = create_compliant_workspace(with_module=True)
        with tmp:
            big = root / "core" / "dsp_core" / "include" / "dsp_core.hpp"
            big.write_text("int x = 0;\n" * 650, encoding="utf-8")
            rep = check_rule(root, "MOD-006")
            self.assertIn("MOD-006", rule_ids_in(rep))


if __name__ == "__main__":
    unittest.main()
