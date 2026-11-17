"""Ruthless testing, required test categories, live execution, and traceability checks (TST-001..TST-004)."""

from __future__ import annotations

import os
import re
import shlex
import subprocess
from pathlib import Path

from tools.xlp_gate.markdown_utils import extract_heading_slugs, parse_frontmatter
from tools.xlp_gate.models import Finding, GateContext, RuleSpec, Severity
from tools.xlp_gate.registry import RuleRegistry
from tools.xlp_gate.schema_validator import validate_schema

TEST_FILE_RE = re.compile(r"(^test_.*\.(py|cpp|cc|c|rs|js|ts)$|.*(_test|Tests?)\.(py|cpp|cc|c|rs|js|ts)$)")
CATEGORY_TAG_RE = re.compile(r"@category:\s*([a-z0-9_]+)")


def _discover_test_files(test_dir: Path) -> list[Path]:
    if not test_dir.is_dir():
        return []
    return [p for p in sorted(test_dir.rglob("*")) if p.is_file() and TEST_FILE_RE.match(p.name)]


def check_tst_001(ctx: GateContext) -> list[Finding]:
    """Every component must declare a valid test suite directory, runnable command, and test files."""
    findings: list[Finding] = []
    for comp in ctx.components:
        if not comp.manifest:
            continue
        rel = ctx.relpath(comp.manifest_path)
        testing = comp.manifest.get("testing")
        if not isinstance(testing, dict):
            findings.append(
                Finding(
                    rule_id="TST-001",
                    severity=Severity.ERROR,
                    message=f"Component '{comp.name}' is missing required 'testing' declaration.",
                    path=rel,
                    remediation="Declare testing.directory, testing.command, and testing.categories in manifest.",
                )
            )
            continue

        tdir_rel = testing.get("directory", "tests")
        tdir = comp.directory / tdir_rel
        if not tdir.is_dir():
            findings.append(
                Finding(
                    rule_id="TST-001",
                    severity=Severity.ERROR,
                    message=f"Component '{comp.name}' test directory '{tdir_rel}' does not exist.",
                    path=ctx.relpath(tdir),
                    remediation=f"Create '{tdir_rel}/' and add automated tests for '{comp.name}'.",
                )
            )
            continue

        test_files = _discover_test_files(tdir)
        if not test_files:
            findings.append(
                Finding(
                    rule_id="TST-001",
                    severity=Severity.ERROR,
                    message=f"Component '{comp.name}' test directory '{tdir_rel}' contains zero recognized test files.",
                    path=ctx.relpath(tdir),
                    remediation="Add test files named 'test_*.py', '*_test.cpp', '*Tests.cpp', etc.",
                )
            )

        cmd = testing.get("command", "")
        if not isinstance(cmd, str) or len(cmd.strip()) < 3:
            findings.append(
                Finding(
                    rule_id="TST-001",
                    severity=Severity.ERROR,
                    message=f"Component '{comp.name}' declares an empty or invalid testing.command.",
                    path=rel,
                    remediation="Provide a real executable test command in manifest testing.command.",
                )
            )

    return findings


def check_tst_002(ctx: GateContext) -> list[Finding]:
    """Verify every component declares and tags all mandatory test categories for its layer."""
    findings: list[Finding] = []
    layers_cfg = ctx.policy.get("layers", {})

    for comp in ctx.components:
        if not comp.manifest:
            continue
        rel = ctx.relpath(comp.manifest_path)
        testing = comp.manifest.get("testing")
        if not isinstance(testing, dict):
            continue

        required_cats = set(layers_cfg.get(comp.layer, {}).get("required_test_categories", []))
        declared_cats = set(testing.get("categories", []))
        missing_declared = sorted(required_cats - declared_cats)
        if missing_declared:
            findings.append(
                Finding(
                    rule_id="TST-002",
                    severity=Severity.ERROR,
                    message=(
                        f"Component '{comp.name}' ({comp.layer}) manifest missing required test categories: "
                        f"{missing_declared}."
                    ),
                    path=rel,
                    remediation=f"Implement and declare required test categories: {missing_declared}.",
                )
            )

        tdir = comp.directory / testing.get("directory", "tests")
        found_tags: set[str] = set()
        for tfile in _discover_test_files(tdir):
            text = tfile.read_text(encoding="utf-8", errors="replace")
            found_tags.update(CATEGORY_TAG_RE.findall(text))

        missing_tags = sorted(required_cats - found_tags)
        if missing_tags:
            findings.append(
                Finding(
                    rule_id="TST-002",
                    severity=Severity.ERROR,
                    message=(
                        f"Component '{comp.name}' test files lack verified '@category: <name>' coverage tags "
                        f"for required categories: {missing_tags}."
                    ),
                    path=ctx.relpath(tdir),
                    remediation=(
                        "Add real test cases for every required category and annotate each test file/class "
                        "with '@category: <category>'."
                    ),
                )
            )

    return findings


def execute_component_tests(ctx: GateContext) -> tuple[list[Finding], list[dict]]:
    """Run every component's declared test command live when `--run-tests` is active."""
    findings: list[Finding] = []
    executed: list[dict] = []

    if not ctx.run_tests:
        return findings, executed

    if os.environ.get("XLP_GATE_IN_TEST_EXEC") == "1":
        return findings, executed

    env = dict(os.environ)
    env["XLP_GATE_IN_TEST_EXEC"] = "1"

    for comp in ctx.components:
        if not comp.manifest:
            continue
        testing = comp.manifest.get("testing")
        if not isinstance(testing, dict):
            continue
        cmd_str = testing.get("command")
        if not isinstance(cmd_str, str) or not cmd_str.strip():
            continue

        rel = ctx.relpath(comp.manifest_path)
        args = shlex.split(cmd_str)
        try:
            proc = subprocess.run(
                args,
                cwd=ctx.repo_root,
                env=env,
                capture_output=True,
                text=True,
                timeout=180,
                check=False,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            executed.append({"component": comp.component_id or comp.name, "command": cmd_str, "exit_code": -1})
            findings.append(
                Finding(
                    rule_id="TST-003",
                    severity=Severity.ERROR,
                    message=f"Failed to launch test command '{cmd_str}': {exc}",
                    path=rel,
                    remediation="Ensure testing.command is valid and runnable from the repository root.",
                )
            )
            continue

        combined = f"{proc.stdout}\n{proc.stderr}"
        executed.append(
            {
                "component": comp.component_id or comp.name,
                "command": cmd_str,
                "exit_code": proc.returncode,
            }
        )
        if proc.returncode != 0:
            tail = "\n".join(combined.strip().splitlines()[-12:])
            findings.append(
                Finding(
                    rule_id="TST-003",
                    severity=Severity.ERROR,
                    message=f"Test suite failed for '{comp.name}' (exit {proc.returncode}): {tail}",
                    path=rel,
                    remediation="Fix all failing tests before committing or merging.",
                )
            )
        elif re.search(r"Ran 0 tests|collected 0 items|0 tests ran", combined):
            findings.append(
                Finding(
                    rule_id="TST-003",
                    severity=Severity.ERROR,
                    message=f"Test suite for '{comp.name}' executed 0 tests (vacuous pass rejected).",
                    path=rel,
                    remediation="Ensure testing.command discovers and runs real test cases.",
                )
            )

    return findings, executed


def check_tst_003(ctx: GateContext) -> list[Finding]:
    """Rule wrapper for TST-003 (actual execution orchestrated via execute_component_tests)."""
    findings, _ = execute_component_tests(ctx)
    return findings


def check_tst_004(ctx: GateContext) -> list[Finding]:
    """Verify 100% rule traceability across ADRs, research, docs, and real positive/adversarial tests."""
    findings: list[Finding] = []
    trace_rel = ctx.policy.get("traceability_file", "governance/traceability.json")
    if ctx.traceability is None:
        return [
            Finding(
                rule_id="TST-004",
                severity=Severity.ERROR,
                message=f"Missing or unreadable traceability matrix '{trace_rel}'.",
                path=trace_rel,
                remediation="Create governance/traceability.json mapping every rule to ADRs, research, docs, and tests.",
            )
        ]

    schema = ctx.schemas.get("traceability")
    if schema:
        for err in validate_schema(ctx.traceability, schema):
            findings.append(
                Finding(
                    rule_id="TST-004",
                    severity=Severity.ERROR,
                    message=f"Traceability schema violation: {err}",
                    path=trace_rel,
                    remediation="Fix governance/traceability.json to conform to traceability.schema.json.",
                )
            )

    entries = ctx.traceability.get("rules", [])
    traced_ids: set[str] = set()
    adr_dir = ctx.repo_root / ctx.policy.get("documentation", {}).get("adr_directory", "docs/adr")
    res_dir = ctx.repo_root / ctx.policy.get("research", {}).get("directory", "docs/research")

    existing_adrs: dict[str, set[str]] = {}
    if adr_dir.is_dir():
        for p in adr_dir.glob("ADR-*.md"):
            fm, _, err = parse_frontmatter(p.read_text(encoding="utf-8", errors="replace"))
            enforced = fm.get("enforced_by", []) if (not err and fm) else []
            if isinstance(enforced, str):
                enforced = [enforced]
            existing_adrs[p.name[:8]] = set(enforced) if isinstance(enforced, list) else set()
    existing_res = {p.name[:8] for p in res_dir.glob("RES-*.md")} if res_dir.is_dir() else set()

    rules_ref_rel = ctx.policy.get("documentation", {}).get(
        "rules_reference_doc", "docs/reference/enforcement-rules.md"
    )
    rules_ref_path = ctx.repo_root / rules_ref_rel
    doc_slugs = (
        extract_heading_slugs(rules_ref_path.read_text(encoding="utf-8", errors="replace"))
        if rules_ref_path.is_file()
        else set()
    )

    # Build index of test function/method names inside tools/xlp_gate/tests for real verification.
    gate_tests_dir = ctx.repo_root / "tools" / "xlp_gate" / "tests"
    discovered_test_symbols: set[str] = set()
    if gate_tests_dir.is_dir():
        for tf in gate_tests_dir.glob("test_*.py"):
            content = tf.read_text(encoding="utf-8", errors="replace")
            for m in re.finditer(r"def\s+(test_[A-Za-z0-9_]+)\s*\(", content):
                discovered_test_symbols.add(f"{tf.stem}.{m.group(1)}")
                discovered_test_symbols.add(m.group(1))

    for entry in entries:
        if not isinstance(entry, dict):
            continue
        rid = entry.get("rule_id")
        if not isinstance(rid, str):
            continue
        if rid in traced_ids:
            findings.append(
                Finding(
                    rule_id="TST-004",
                    severity=Severity.ERROR,
                    message=f"Duplicate traceability entry for rule '{rid}'.",
                    path=trace_rel,
                    remediation="Maintain exactly one traceability entry per rule_id.",
                )
            )
        traced_ids.add(rid)

        if rid not in ctx.registered_rules:
            findings.append(
                Finding(
                    rule_id="TST-004",
                    severity=Severity.ERROR,
                    message=f"Traceability matrix references unregistered rule '{rid}'.",
                    path=trace_rel,
                    remediation="Register the rule in tools/xlp_gate or remove the stale traceability entry.",
                )
            )

        for adr_id in entry.get("adr_ids", []):
            if adr_id not in existing_adrs:
                findings.append(
                    Finding(
                        rule_id="TST-004",
                        severity=Severity.ERROR,
                        message=f"Traceability entry '{rid}' references missing ADR '{adr_id}'.",
                        path=trace_rel,
                        remediation="Reference an existing ADR under docs/adr/.",
                    )
                )
            elif rid not in existing_adrs[adr_id]:
                findings.append(
                    Finding(
                        rule_id="TST-004",
                        severity=Severity.ERROR,
                        message=(
                            f"Bidirectional binding mismatch: traceability links '{rid}' to '{adr_id}', "
                            f"but '{adr_id}' does not list '{rid}' in 'enforced_by'."
                        ),
                        path=trace_rel,
                        remediation=f"Add '{rid}' to 'enforced_by' in '{adr_id}' or fix traceability adr_ids.",
                    )
                )

        doc_anchor = entry.get("doc_anchor", "")
        if doc_slugs and isinstance(doc_anchor, str) and doc_anchor not in doc_slugs:
            findings.append(
                Finding(
                    rule_id="TST-004",
                    severity=Severity.ERROR,
                    message=f"Traceability doc_anchor '#{doc_anchor}' not found in '{rules_ref_rel}'.",
                    path=trace_rel,
                    remediation=f"Ensure '### {rid}' exists in '{rules_ref_rel}'.",
                )
            )

        for res_id in entry.get("research_ids", []):
            if res_id not in existing_res:
                findings.append(
                    Finding(
                        rule_id="TST-004",
                        severity=Severity.ERROR,
                        message=f"Traceability entry '{rid}' references missing Research Dossier '{res_id}'.",
                        path=trace_rel,
                        remediation="Reference an existing RES-XXXX dossier under docs/research/.",
                    )
                )

        check_mod = entry.get("check_module", "")
        if isinstance(check_mod, str) and not (ctx.repo_root / check_mod).is_file():
            findings.append(
                Finding(
                    rule_id="TST-004",
                    severity=Severity.ERROR,
                    message=f"Traceability entry '{rid}' points to missing check_module '{check_mod}'.",
                    path=trace_rel,
                    remediation="Update check_module to the exact workspace file path.",
                )
            )

        if discovered_test_symbols:
            for field_name in ("positive_tests", "adversarial_tests"):
                for test_ref in entry.get(field_name, []):
                    if test_ref not in discovered_test_symbols:
                        findings.append(
                            Finding(
                                rule_id="TST-004",
                                severity=Severity.ERROR,
                                message=(
                                    f"Traceability entry '{rid}' references non-existent test "
                                    f"'{test_ref}' in '{field_name}'."
                                ),
                                path=trace_rel,
                                remediation=f"Implement test '{test_ref}' in tools/xlp_gate/tests/ or fix its name.",
                            )
                        )

    missing_rules = sorted(set(ctx.registered_rules.keys()) - traced_ids)
    for rid in missing_rules:
        findings.append(
            Finding(
                rule_id="TST-004",
                severity=Severity.ERROR,
                message=f"Registered rule '{rid}' is missing from governance/traceability.json.",
                path=trace_rel,
                remediation=f"Add full ADR, research, doc, positive, and adversarial test traceability for '{rid}'.",
            )
        )

    return findings


def register(registry: RuleRegistry) -> None:
    registry.register(
        RuleSpec(
            rule_id="TST-001",
            domain="testing",
            title="Universal Component Test Suite Requirement",
            summary="Every component must declare a valid testing command, existing test directory, and test files.",
        ),
        check_tst_001,
    )
    registry.register(
        RuleSpec(
            rule_id="TST-002",
            domain="testing",
            title="Layer-Specific Required Test Categories",
            summary="Every component must implement and tag all required test categories for its architectural layer.",
        ),
        check_tst_002,
    )
    registry.register(
        RuleSpec(
            rule_id="TST-003",
            domain="testing",
            title="Live Test Suite Execution Gate",
            summary="When --run-tests is enabled (CI & pre-push), every component test suite must execute and pass with >0 tests.",
            requires_test_execution=True,
        ),
        check_tst_003,
    )
    registry.register(
        RuleSpec(
            rule_id="TST-004",
            domain="testing",
            title="End-to-End Rule Traceability & Adversarial Coverage",
            summary="100% of enforcement rules must trace to ADRs, research, docs, and verified positive + adversarial tests.",
        ),
        check_tst_004,
    )
