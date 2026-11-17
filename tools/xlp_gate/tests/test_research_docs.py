"""Positive and adversarial tests for Research (RES-001..004) and Documentation (DOC-001..006) rules.

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


class TestResearchAndDocumentationRules(unittest.TestCase):
    def test_res_001_positive(self) -> None:
        tmp, root = create_compliant_workspace()
        with tmp:
            rep = check_rule(root, "RES-001")
            self.assertTrue(rep.passed, rep.findings)

    def test_res_001_adversarial_missing_section(self) -> None:
        tmp, root = create_compliant_workspace()
        with tmp:
            bad = root / "docs" / "research" / "RES-0099-incomplete.md"
            bad.write_text(
                "---\nid: RES-0099\ntitle: Incomplete\nstatus: draft\ndate: 2026-11-15\n"
                "scope: test\nconfidence: low\nlast_verified: 2026-11-15\n"
                "related_adrs:\n  - ADR-0001\nrelated_components:\n  - xlp.tools.xlp_gate\n---\n\n"
                "# RES-0099\n\n## Problem & Research Questions\n\nOnly one section.\n",
                encoding="utf-8",
            )
            rep = check_rule(root, "RES-001")
            self.assertIn("RES-001", rule_ids_in(rep))

    def test_res_002_positive(self) -> None:
        tmp, root = create_compliant_workspace()
        with tmp:
            rep = check_rule(root, "RES-002")
            self.assertTrue(rep.passed, rep.findings)

    def test_res_002_adversarial_uncited_and_dangling_citations(self) -> None:
        tmp, root = create_compliant_workspace()
        with tmp:
            res = root / "docs" / "research" / "RES-0001-vst3-clap-plugin-architecture.md"
            text = res.read_text(encoding="utf-8")
            # Append a fake uncited bibliography item and a dangling citation [99]
            text = text.replace(
                "## Problem & Research Questions\n",
                "## Problem & Research Questions\n\nUnsupported claim [99].\n",
            )
            text += "\n7. Fake Uncited Source — https://example.org/never-cited\n"
            res.write_text(text, encoding="utf-8")
            rep = check_rule(root, "RES-002")
            self.assertIn("RES-002", rule_ids_in(rep))
            self.assertGreaterEqual(len(rep.findings), 2)

    def test_res_003_positive(self) -> None:
        tmp, root = create_compliant_workspace()
        with tmp:
            rep = check_rule(root, "RES-003")
            self.assertTrue(rep.passed, rep.findings)

    def test_res_003_adversarial_stub_section(self) -> None:
        tmp, root = create_compliant_workspace()
        with tmp:
            stub = root / "docs" / "research" / "RES-0098-stub.md"
            stub.write_text(
                "---\nid: RES-0098\ntitle: Stub\nstatus: draft\ndate: 2026-11-15\n"
                "scope: test\nconfidence: low\nlast_verified: 2026-11-15\n"
                "related_adrs:\n  - ADR-0001\nrelated_components:\n  - xlp.tools.xlp_gate\n---\n\n"
                "# Stub\n\n"
                "## Problem & Research Questions\n\nToo short [1].\n\n"
                "## Prior Art & Industry Standards\n\nToo short [2].\n\n"
                "## Technical Deep Dive\n\nToo short [3].\n\n"
                "## Comparative Trade-offs\n\nToo short.\n\n"
                "## Benchmarks & Empirical Evidence\n\nToo short.\n\n"
                "## Risks, Edge Cases & Failure Modes\n\nToo short.\n\n"
                "## Recommendations & Architectural Implications\n\nToo short.\n\n"
                "## References\n\n1. https://a.test\n2. https://b.test\n3. https://c.test\n",
                encoding="utf-8",
            )
            rep = check_rule(root, "RES-003")
            self.assertIn("RES-003", rule_ids_in(rep))

    def test_res_004_positive(self) -> None:
        tmp, root = create_compliant_workspace(with_plugin=True)
        with tmp:
            rep = check_rule(root, "RES-004")
            self.assertTrue(rep.passed, rep.findings)

    def test_res_004_adversarial_missing_research_target(self) -> None:
        tmp, root = create_compliant_workspace(with_plugin=True)
        with tmp:
            mpath = root / "plugins" / "xlp_filter_one" / "plugin.manifest.json"
            data = read_json(mpath)
            data["research_refs"] = ["RES-9999"]
            write_json(mpath, data)
            rep = check_rule(root, "RES-004")
            self.assertIn("RES-004", rule_ids_in(rep))

    def test_doc_001_positive(self) -> None:
        tmp, root = create_compliant_workspace()
        with tmp:
            rep = check_rule(root, "DOC-001")
            self.assertTrue(rep.passed, rep.findings)

    def test_doc_001_adversarial_misfiled_adr_in_quadrant(self) -> None:
        tmp, root = create_compliant_workspace()
        with tmp:
            (root / "docs" / "explanation" / "ADR-0099-misfiled.md").write_text(
                "# Misfiled ADR\n", encoding="utf-8"
            )
            rep = check_rule(root, "DOC-001")
            self.assertIn("DOC-001", rule_ids_in(rep))

    def test_doc_002_positive(self) -> None:
        tmp, root = create_compliant_workspace()
        with tmp:
            rep = check_rule(root, "DOC-002")
            self.assertTrue(rep.passed, rep.findings)

    def test_doc_002_adversarial_accepted_adr_with_phantom_rule(self) -> None:
        tmp, root = create_compliant_workspace()
        with tmp:
            adr = root / "docs" / "adr" / "ADR-0001-xlp-governance-enforcement-gate.md"
            adr.write_text(
                adr.read_text(encoding="utf-8").replace("GOV-001", "PHANTOM-999"),
                encoding="utf-8",
            )
            rep = check_rule(root, "DOC-002")
            self.assertIn("DOC-002", rule_ids_in(rep))

    def test_doc_003_positive(self) -> None:
        tmp, root = create_compliant_workspace(with_module=True)
        with tmp:
            rep = check_rule(root, "DOC-003")
            self.assertTrue(rep.passed, rep.findings)

    def test_doc_003_adversarial_missing_component_doc(self) -> None:
        tmp, root = create_compliant_workspace(with_module=True)
        with tmp:
            (root / "core" / "dsp_core" / "docs" / "api.md").unlink()
            rep = check_rule(root, "DOC-003")
            self.assertIn("DOC-003", rule_ids_in(rep))

    def test_doc_004_positive(self) -> None:
        tmp, root = create_compliant_workspace()
        with tmp:
            rep = check_rule(root, "DOC-004")
            self.assertTrue(rep.passed, rep.findings)

    def test_doc_004_adversarial_undocumented_rule_and_orphan_heading(self) -> None:
        tmp, root = create_compliant_workspace()
        with tmp:
            ref = root / "docs" / "reference" / "enforcement-rules.md"
            text = ref.read_text(encoding="utf-8").replace("### BRD-001", "### ZZZ-999")
            ref.write_text(text, encoding="utf-8")
            rep = check_rule(root, "DOC-004")
            self.assertIn("DOC-004", rule_ids_in(rep))
            self.assertGreaterEqual(len(rep.findings), 2)

    def test_doc_005_positive(self) -> None:
        tmp, root = create_compliant_workspace()
        with tmp:
            rep = check_rule(root, "DOC-005")
            self.assertTrue(rep.passed, rep.findings)

    def test_doc_005_adversarial_broken_file_link_and_bad_anchor(self) -> None:
        tmp, root = create_compliant_workspace()
        with tmp:
            readme = root / "docs" / "README.md"
            readme.write_text(
                readme.read_text(encoding="utf-8")
                + "\n- [Missing](does-not-exist.md)\n"
                + "- [Bad Anchor](reference/cli-reference.md#nonexistent-heading)\n",
                encoding="utf-8",
            )
            rep = check_rule(root, "DOC-005")
            self.assertIn("DOC-005", rule_ids_in(rep))
            self.assertGreaterEqual(len(rep.findings), 2)

    def test_doc_006_positive(self) -> None:
        tmp, root = create_compliant_workspace()
        with tmp:
            rep = check_rule(root, "DOC-006")
            self.assertTrue(rep.passed, rep.findings)

    def test_doc_006_adversarial_placeholder_debt(self) -> None:
        tmp, root = create_compliant_workspace()
        with tmp:
            guide = root / "docs" / "explanation" / "architecture-pillars.md"
            guide.write_text(
                guide.read_text(encoding="utf-8")
                + "\n\nTBD finish this section later.\n"
                + "PLACEHOLDER text here.\n"
                + "Coming soon in v2.\n"
                + "Lorem ipsum dolor sit amet.\n",
                encoding="utf-8",
            )
            rep = check_rule(root, "DOC-006")
            self.assertIn("DOC-006", rule_ids_in(rep))
            self.assertGreaterEqual(len(rep.findings), 4)


if __name__ == "__main__":
    unittest.main()
