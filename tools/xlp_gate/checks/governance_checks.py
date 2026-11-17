"""Governance meta-schema, hooks/CI infrastructure, audited waivers, and anti-tampering checks (GOV-001..GOV-004)."""

from __future__ import annotations

import datetime
import os
import stat
from pathlib import Path

from tools.xlp_gate.models import Finding, GateContext, RuleSpec, Severity
from tools.xlp_gate.policy import load_json_file
from tools.xlp_gate.registry import RuleRegistry
from tools.xlp_gate.schema_validator import validate_schema

# Hardcoded constitutional floor invariants that cannot be weakened solely by editing policy.json.
HARD_MIN_RESEARCH_CITATIONS = 3
HARD_MIN_PLUGIN_MOD_SURFACES = 2
HARD_MIN_PLUGIN_EXTENSION_POINTS = 2
HARD_MAX_SOURCE_LINES_CEILING = 800
HARD_REQUIRED_NON_WAIVABLE = {
    "MOD-003",
    "SCA-001",
    "MDD-002",
    "TST-003",
    "GOV-001",
    "GOV-002",
    "GOV-003",
    "GOV-004",
}


def _today(ctx: GateContext) -> datetime.date:
    if ctx.today_iso:
        return datetime.date.fromisoformat(ctx.today_iso)
    return datetime.date.today()


def check_gov_001(ctx: GateContext) -> list[Finding]:
    """Validate all core governance JSON documents against their meta-schemas."""
    findings: list[Finding] = []
    targets = [
        ("governance/policy.json", "policy"),
        ("governance/brand.json", "brand"),
        ("governance/waivers.json", "waivers"),
        ("governance/traceability.json", "traceability"),
    ]
    for rel, schema_key in targets:
        path = ctx.repo_root / rel
        data, err = load_json_file(path)
        if err or not isinstance(data, dict):
            findings.append(
                Finding(
                    rule_id="GOV-001",
                    severity=Severity.ERROR,
                    message=f"Governance file '{rel}' missing or unreadable: {err}",
                    path=rel,
                    remediation=f"Restore valid JSON at '{rel}'.",
                )
            )
            continue
        schema = ctx.schemas.get(schema_key)
        if schema is None:
            findings.append(
                Finding(
                    rule_id="GOV-001",
                    severity=Severity.ERROR,
                    message=f"Missing governance meta-schema 'governance/schemas/{schema_key}.schema.json'.",
                    path=f"governance/schemas/{schema_key}.schema.json",
                    remediation="Restore all governance JSON schemas.",
                )
            )
            continue
        for serr in validate_schema(data, schema):
            findings.append(
                Finding(
                    rule_id="GOV-001",
                    severity=Severity.ERROR,
                    message=f"Governance meta-schema violation: {serr}",
                    path=rel,
                    remediation=f"Fix '{rel}' to conform to governance/schemas/{schema_key}.schema.json.",
                )
            )
    return findings


def _is_executable(path: Path) -> bool:
    try:
        mode = os.stat(path).st_mode
        return bool(mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH))
    except OSError:
        return False


def check_gov_002(ctx: GateContext) -> list[Finding]:
    """Verify defense-in-depth enforcement infrastructure: CI workflow, Git hooks, CLI, AGENTS.md, CONTRIBUTING.md."""
    findings: list[Finding] = []

    # 1. CLI entrypoint
    cli_wrapper = ctx.repo_root / "xlp-gate"
    if not cli_wrapper.is_file() or not _is_executable(cli_wrapper):
        findings.append(
            Finding(
                rule_id="GOV-002",
                severity=Severity.ERROR,
                message="Executable root entrypoint './xlp-gate' is missing or not executable.",
                path="xlp-gate",
                remediation="Ensure './xlp-gate' exists and has executable permissions (chmod +x).",
            )
        )

    # 2. Versioned Git hooks + installer
    required_execs = [
        ".githooks/pre-commit",
        ".githooks/commit-msg",
        ".githooks/pre-push",
        "scripts/install-hooks.sh",
    ]
    for rel in required_execs:
        p = ctx.repo_root / rel
        if not p.is_file():
            findings.append(
                Finding(
                    rule_id="GOV-002",
                    severity=Severity.ERROR,
                    message=f"Missing versioned enforcement hook/script '{rel}'.",
                    path=rel,
                    remediation=f"Restore '{rel}' and mark executable.",
                )
            )
        elif not _is_executable(p):
            findings.append(
                Finding(
                    rule_id="GOV-002",
                    severity=Severity.ERROR,
                    message=f"Hook/script '{rel}' must be executable.",
                    path=rel,
                    remediation=f"Run 'chmod +x {rel}'.",
                )
            )

    # Verify hooks actually invoke xlp-gate.
    for hook_rel, expected_fragment in (
        (".githooks/pre-commit", "xlp-gate"),
        (".githooks/pre-push", "--run-tests"),
    ):
        hp = ctx.repo_root / hook_rel
        if hp.is_file():
            content = hp.read_text(encoding="utf-8", errors="replace")
            if expected_fragment not in content:
                findings.append(
                    Finding(
                        rule_id="GOV-002",
                        severity=Severity.ERROR,
                        message=f"Hook '{hook_rel}' does not invoke expected enforcement fragment '{expected_fragment}'.",
                        path=hook_rel,
                        remediation=f"Ensure '{hook_rel}' runs './xlp-gate check --strict' properly.",
                    )
                )

    # 3. GitHub Actions CI workflow
    ci_rel = ".github/workflows/xlp-gate.yml"
    ci_path = ctx.repo_root / ci_rel
    if not ci_path.is_file():
        findings.append(
            Finding(
                rule_id="GOV-002",
                severity=Severity.ERROR,
                message=f"Missing mandatory CI enforcement workflow '{ci_rel}'.",
                path=ci_rel,
                remediation="Create '.github/workflows/xlp-gate.yml' executing './xlp-gate check --strict --run-tests'.",
            )
        )
    else:
        ci_text = ci_path.read_text(encoding="utf-8", errors="replace")
        if "xlp-gate" not in ci_text or "--run-tests" not in ci_text or "--strict" not in ci_text:
            findings.append(
                Finding(
                    rule_id="GOV-002",
                    severity=Severity.ERROR,
                    message=f"CI workflow '{ci_rel}' must run './xlp-gate check --strict --run-tests'.",
                    path=ci_rel,
                    remediation="Invoke './xlp-gate check --strict --run-tests' in CI.",
                )
            )
        if "continue-on-error: true" in ci_text.lower():
            findings.append(
                Finding(
                    rule_id="GOV-002",
                    severity=Severity.ERROR,
                    message=f"CI workflow '{ci_rel}' contains forbidden 'continue-on-error: true' bypass.",
                    path=ci_rel,
                    remediation="Remove 'continue-on-error: true' so CI strictly blocks non-compliant changes.",
                )
            )

    # 4. Agent & Contributor governance guides
    for doc_rel in ("AGENTS.md", "CONTRIBUTING.md", "README.md"):
        dp = ctx.repo_root / doc_rel
        if not dp.is_file():
            findings.append(
                Finding(
                    rule_id="GOV-002",
                    severity=Severity.ERROR,
                    message=f"Missing root governance document '{doc_rel}'.",
                    path=doc_rel,
                    remediation=f"Create '{doc_rel}' documenting the XLP architecture and xlp-gate protocol.",
                )
            )
        elif "xlp-gate" not in dp.read_text(encoding="utf-8", errors="replace"):
            findings.append(
                Finding(
                    rule_id="GOV-002",
                    severity=Severity.ERROR,
                    message=f"Root governance document '{doc_rel}' must explicitly document 'xlp-gate'.",
                    path=doc_rel,
                    remediation=f"Reference './xlp-gate check --strict --run-tests' in '{doc_rel}'.",
                )
            )

    return findings


def check_gov_003(ctx: GateContext) -> list[Finding]:
    """Validate audited waivers: real rule, waivable, ADR-backed, bounded duration, non-expired."""
    findings: list[Finding] = []
    waivers_rel = ctx.policy.get("waivers_file", "governance/waivers.json")
    waiver_cfg = ctx.policy.get("waivers", {})
    non_waivable = set(waiver_cfg.get("non_waivable_rules", [])) | HARD_REQUIRED_NON_WAIVABLE
    max_days = int(waiver_cfg.get("max_duration_days", 90))
    min_just = int(waiver_cfg.get("min_justification_length", 40))
    today = _today(ctx)

    adr_dir = ctx.repo_root / ctx.policy.get("documentation", {}).get("adr_directory", "docs/adr")
    existing_adrs = {p.name[:8] for p in adr_dir.glob("ADR-*.md")} if adr_dir.is_dir() else set()

    seen_ids: set[str] = set()
    for waiver in ctx.waivers:
        if not isinstance(waiver, dict):
            continue
        wid = str(waiver.get("id", "UNKNOWN"))
        if wid in seen_ids:
            findings.append(
                Finding(
                    rule_id="GOV-003",
                    severity=Severity.ERROR,
                    message=f"Duplicate waiver id '{wid}'.",
                    path=waivers_rel,
                    remediation="Assign unique WAV-XXXX IDs.",
                )
            )
        seen_ids.add(wid)

        rid = waiver.get("rule_id")
        if rid not in ctx.registered_rules:
            findings.append(
                Finding(
                    rule_id="GOV-003",
                    severity=Severity.ERROR,
                    message=f"Waiver '{wid}' targets unknown rule '{rid}'.",
                    path=waivers_rel,
                    remediation="Specify a valid registered xlp-gate rule_id.",
                )
            )
        elif rid in non_waivable:
            findings.append(
                Finding(
                    rule_id="GOV-003",
                    severity=Severity.ERROR,
                    message=f"Waiver '{wid}' illegally attempts to waive non-waivable constitutional rule '{rid}'.",
                    path=waivers_rel,
                    remediation=f"Remove waiver for '{rid}' and fix the underlying violation.",
                )
            )

        adr_id = waiver.get("adr_id")
        if adr_id not in existing_adrs:
            findings.append(
                Finding(
                    rule_id="GOV-003",
                    severity=Severity.ERROR,
                    message=f"Waiver '{wid}' references non-existent ADR '{adr_id}'.",
                    path=waivers_rel,
                    remediation="Link every waiver to an existing ADR in docs/adr/.",
                )
            )

        justification = waiver.get("justification", "")
        if not isinstance(justification, str) or len(justification.strip()) < min_just:
            findings.append(
                Finding(
                    rule_id="GOV-003",
                    severity=Severity.ERROR,
                    message=f"Waiver '{wid}' justification is shorter than {min_just} characters.",
                    path=waivers_rel,
                    remediation="Provide a detailed technical justification explaining scope and remediation plan.",
                )
            )

        try:
            created = datetime.date.fromisoformat(str(waiver.get("created_on", "")))
            expires = datetime.date.fromisoformat(str(waiver.get("expires_on", "")))
        except ValueError:
            findings.append(
                Finding(
                    rule_id="GOV-003",
                    severity=Severity.ERROR,
                    message=f"Waiver '{wid}' has invalid ISO dates (created_on/expires_on).",
                    path=waivers_rel,
                    remediation="Use ISO-8601 dates (YYYY-MM-DD).",
                )
            )
            continue

        if expires < created:
            findings.append(
                Finding(
                    rule_id="GOV-003",
                    severity=Severity.ERROR,
                    message=f"Waiver '{wid}' expires_on ({expires}) precedes created_on ({created}).",
                    path=waivers_rel,
                    remediation="Fix waiver dates so expires_on >= created_on.",
                )
            )
        elif (expires - created).days > max_days:
            findings.append(
                Finding(
                    rule_id="GOV-003",
                    severity=Severity.ERROR,
                    message=f"Waiver '{wid}' duration {(expires - created).days}d exceeds maximum {max_days}d.",
                    path=waivers_rel,
                    remediation=f"Shorten waiver duration to <= {max_days} days.",
                )
            )

        if expires < today:
            findings.append(
                Finding(
                    rule_id="GOV-003",
                    severity=Severity.ERROR,
                    message=f"Waiver '{wid}' for '{rid}' expired on {expires} (today: {today}).",
                    path=waivers_rel,
                    remediation="Resolve the waived issue and remove the expired waiver.",
                )
            )

    return findings


def check_gov_004(ctx: GateContext) -> list[Finding]:
    """Anti-tampering check: prevent weakening constitutional policy floors."""
    findings: list[Finding] = []
    pol = ctx.policy
    rel = "governance/policy.json"

    if not pol:
        return findings

    if pol.get("modularity", {}).get("allow_circular_dependencies") is not False:
        findings.append(
            Finding(
                rule_id="GOV-004",
                severity=Severity.ERROR,
                message="Constitutional violation: modularity.allow_circular_dependencies must remain false.",
                path=rel,
                remediation="Set modularity.allow_circular_dependencies to false.",
            )
        )

    if pol.get("modularity", {}).get("allow_cross_plugin_imports") is not False:
        findings.append(
            Finding(
                rule_id="GOV-004",
                severity=Severity.ERROR,
                message="Constitutional violation: modularity.allow_cross_plugin_imports must remain false.",
                path=rel,
                remediation="Set modularity.allow_cross_plugin_imports to false.",
            )
        )

    max_lines = pol.get("modularity", {}).get("max_source_file_lines", 9999)
    if not isinstance(max_lines, int) or max_lines > HARD_MAX_SOURCE_LINES_CEILING:
        findings.append(
            Finding(
                rule_id="GOV-004",
                severity=Severity.ERROR,
                message=(
                    f"Constitutional violation: max_source_file_lines ({max_lines}) exceeds hard ceiling "
                    f"{HARD_MAX_SOURCE_LINES_CEILING}."
                ),
                path=rel,
                remediation=f"Keep max_source_file_lines <= {HARD_MAX_SOURCE_LINES_CEILING}.",
            )
        )

    if pol.get("realtime_safety", {}).get("require_rt_safety_check") is not True:
        findings.append(
            Finding(
                rule_id="GOV-004",
                severity=Severity.ERROR,
                message="Constitutional violation: realtime_safety.require_rt_safety_check must remain true.",
                path=rel,
                remediation="Set realtime_safety.require_rt_safety_check to true.",
            )
        )

    if pol.get("moddability", {}).get("require_modding_for_plugins") is not True:
        findings.append(
            Finding(
                rule_id="GOV-004",
                severity=Severity.ERROR,
                message="Constitutional violation: moddability.require_modding_for_plugins must remain true.",
                path=rel,
                remediation="Set moddability.require_modding_for_plugins to true.",
            )
        )

    min_cites = pol.get("research", {}).get("min_citations", 0)
    if not isinstance(min_cites, int) or min_cites < HARD_MIN_RESEARCH_CITATIONS:
        findings.append(
            Finding(
                rule_id="GOV-004",
                severity=Severity.ERROR,
                message=(
                    f"Constitutional violation: research.min_citations ({min_cites}) cannot drop below "
                    f"{HARD_MIN_RESEARCH_CITATIONS}."
                ),
                path=rel,
                remediation=f"Restore research.min_citations >= {HARD_MIN_RESEARCH_CITATIONS}.",
            )
        )

    min_surfaces = pol.get("moddability", {}).get("min_plugin_mod_surfaces", 0)
    if not isinstance(min_surfaces, int) or min_surfaces < HARD_MIN_PLUGIN_MOD_SURFACES:
        findings.append(
            Finding(
                rule_id="GOV-004",
                severity=Severity.ERROR,
                message=(
                    f"Constitutional violation: min_plugin_mod_surfaces ({min_surfaces}) cannot drop below "
                    f"{HARD_MIN_PLUGIN_MOD_SURFACES}."
                ),
                path=rel,
                remediation=f"Restore min_plugin_mod_surfaces >= {HARD_MIN_PLUGIN_MOD_SURFACES}.",
            )
        )

    min_eps = pol.get("extensibility", {}).get("min_plugin_extension_points", 0)
    if not isinstance(min_eps, int) or min_eps < HARD_MIN_PLUGIN_EXTENSION_POINTS:
        findings.append(
            Finding(
                rule_id="GOV-004",
                severity=Severity.ERROR,
                message=(
                    f"Constitutional violation: min_plugin_extension_points ({min_eps}) cannot drop below "
                    f"{HARD_MIN_PLUGIN_EXTENSION_POINTS}."
                ),
                path=rel,
                remediation=f"Restore min_plugin_extension_points >= {HARD_MIN_PLUGIN_EXTENSION_POINTS}.",
            )
        )

    non_waivable = set(pol.get("waivers", {}).get("non_waivable_rules", []))
    missing_nw = sorted(HARD_REQUIRED_NON_WAIVABLE - non_waivable)
    if missing_nw:
        findings.append(
            Finding(
                rule_id="GOV-004",
                severity=Severity.ERROR,
                message=f"Constitutional violation: required non-waivable rules removed from policy: {missing_nw}.",
                path=rel,
                remediation=f"Restore {missing_nw} to waivers.non_waivable_rules.",
            )
        )

    return findings


def register(registry: RuleRegistry) -> None:
    registry.register(
        RuleSpec(
            rule_id="GOV-001",
            domain="governance",
            title="Governance Meta-Schema Validation",
            summary="policy.json, brand.json, waivers.json, and traceability.json must satisfy their JSON schemas.",
        ),
        check_gov_001,
    )
    registry.register(
        RuleSpec(
            rule_id="GOV-002",
            domain="governance",
            title="Enforcement Infrastructure Integrity (CI, Hooks, Docs)",
            summary="CLI wrapper, Git hooks, CI workflow (without continue-on-error), AGENTS.md, and CONTRIBUTING.md must stay intact.",
        ),
        check_gov_002,
    )
    registry.register(
        RuleSpec(
            rule_id="GOV-003",
            domain="governance",
            title="Audited Waiver Validity & Expiration Enforcement",
            summary="Waivers must target waivable rules, cite an existing ADR, provide justification, and remain unexpired.",
        ),
        check_gov_003,
    )
    registry.register(
        RuleSpec(
            rule_id="GOV-004",
            domain="governance",
            title="Constitutional Floor Anti-Tampering Protection",
            summary="Core architectural, RT-safety, moddability, and research minimums in policy.json cannot be silently lowered.",
        ),
        check_gov_004,
    )
