"""Gate runner, waiver matcher, and report renderers for xlp-gate."""

from __future__ import annotations

import datetime
import json
import time
from pathlib import Path

from tools.xlp_gate.checks.governance_checks import HARD_REQUIRED_NON_WAIVABLE
from tools.xlp_gate.checks.testing_checks import execute_component_tests
from tools.xlp_gate.models import Finding, GateContext, GateReport, Severity
from tools.xlp_gate.policy import build_context
from tools.xlp_gate.registry import RuleRegistry, build_default_registry


def _valid_active_waivers(ctx: GateContext) -> list[dict]:
    waiver_cfg = ctx.policy.get("waivers", {})
    non_waivable = set(waiver_cfg.get("non_waivable_rules", [])) | HARD_REQUIRED_NON_WAIVABLE
    max_days = int(waiver_cfg.get("max_duration_days", 90))
    min_just = int(waiver_cfg.get("min_justification_length", 40))
    today = (
        datetime.date.fromisoformat(ctx.today_iso) if ctx.today_iso else datetime.date.today()
    )

    adr_dir = ctx.repo_root / ctx.policy.get("documentation", {}).get("adr_directory", "docs/adr")
    existing_adrs = {p.name[:8] for p in adr_dir.glob("ADR-*.md")} if adr_dir.is_dir() else set()

    active: list[dict] = []
    for w in ctx.waivers:
        if not isinstance(w, dict):
            continue
        rid = w.get("rule_id")
        if rid not in ctx.registered_rules or rid in non_waivable:
            continue
        if w.get("adr_id") not in existing_adrs:
            continue
        just = w.get("justification", "")
        if not isinstance(just, str) or len(just.strip()) < min_just:
            continue
        try:
            created = datetime.date.fromisoformat(str(w.get("created_on", "")))
            expires = datetime.date.fromisoformat(str(w.get("expires_on", "")))
        except ValueError:
            continue
        if expires < created or (expires - created).days > max_days or expires < today:
            continue
        active.append(w)
    return active


def _match_waiver(finding: Finding, active_waivers: list[dict]) -> str | None:
    for w in active_waivers:
        if w.get("rule_id") != finding.rule_id:
            continue
        target = str(w.get("target_path", "")).rstrip("/")
        if not target:
            continue
        if finding.path == target or finding.path.startswith(target + "/"):
            return str(w.get("id", "WAIVED"))
    return None


def run_gate(
    repo_root: Path,
    *,
    strict: bool = True,
    run_tests: bool = False,
    only_rules: set[str] | None = None,
    only_domains: set[str] | None = None,
    registry: RuleRegistry | None = None,
    today_iso: str | None = None,
) -> GateReport:
    """Execute all selected enforcement rules against `repo_root` and return a `GateReport`."""
    started = time.monotonic()
    reg = registry or build_default_registry()
    ctx = build_context(
        repo_root=repo_root,
        registered_rules=reg.specs_map(),
        run_tests=run_tests,
        strict=strict,
        today_iso=today_iso,
    )

    active_waivers = _valid_active_waivers(ctx)
    evaluated: list[str] = []
    raw_findings: list[Finding] = []
    executed_tests: list[dict] = []

    for entry in reg.all_rules():
        spec = entry.spec
        if only_rules and spec.rule_id not in only_rules:
            continue
        if only_domains and spec.domain not in only_domains:
            continue
        if spec.requires_test_execution and not run_tests:
            continue

        evaluated.append(spec.rule_id)
        if spec.rule_id == "TST-003":
            f_list, exec_info = execute_component_tests(ctx)
            raw_findings.extend(f_list)
            executed_tests.extend(exec_info)
        else:
            raw_findings.extend(entry.checker(ctx))

    findings: list[Finding] = []
    waived_findings: list[Finding] = []
    for f in raw_findings:
        waiver_id = _match_waiver(f, active_waivers)
        if waiver_id:
            f.waived_by = waiver_id
            waived_findings.append(f)
        else:
            findings.append(f)

    findings.sort(key=lambda item: (item.rule_id, item.path, item.line or 0, item.message))
    elapsed_ms = int((time.monotonic() - started) * 1000)

    has_error = any(f.severity == Severity.ERROR for f in findings)
    has_warning = any(f.severity == Severity.WARNING for f in findings)
    passed = not has_error and (not strict or not has_warning)

    return GateReport(
        passed=passed,
        strict=strict,
        run_tests=run_tests,
        rules_evaluated=evaluated,
        findings=findings,
        waived_findings=waived_findings,
        duration_ms=elapsed_ms,
        executed_test_commands=executed_tests,
    )


def format_text_report(report: GateReport) -> str:
    status = "PASS" if report.passed else "FAIL"
    lines = [
        f"XLP Enforcement Gate: {status}",
        (
            f"Rules evaluated: {len(report.rules_evaluated)} | "
            f"Errors: {report.error_count} | Warnings: {report.warning_count} | "
            f"Waived: {len(report.waived_findings)} | Duration: {report.duration_ms}ms"
        ),
    ]
    if report.executed_test_commands:
        lines.append("Executed test suites:")
        for item in report.executed_test_commands:
            ok = "OK" if item["exit_code"] == 0 else f"FAIL({item['exit_code']})"
            lines.append(f"  - [{ok}] {item['component']}: {item['command']}")
    if report.findings:
        lines.append("")
        lines.append("Violations:")
        for f in report.findings:
            loc = f"{f.path}:{f.line}" if f.line else f.path
            lines.append(f"  [{f.severity.value.upper()}] {f.rule_id} ({loc}): {f.message}")
            if f.remediation:
                lines.append(f"      Fix: {f.remediation}")
    if report.waived_findings:
        lines.append("")
        lines.append("Waived findings:")
        for f in report.waived_findings:
            lines.append(f"  [WAIVED:{f.waived_by}] {f.rule_id} ({f.path}): {f.message}")
    return "\n".join(lines)


def format_markdown_report(report: GateReport) -> str:
    status = "PASS" if report.passed else "FAIL"
    lines = [
        f"# XLP Enforcement Gate Report — {status}",
        "",
        f"- **Mode**: {'strict' if report.strict else 'standard'}",
        f"- **Run Tests**: {'yes' if report.run_tests else 'no'}",
        f"- **Rules Evaluated**: {len(report.rules_evaluated)}",
        f"- **Errors**: {report.error_count}",
        f"- **Warnings**: {report.warning_count}",
        f"- **Waived**: {len(report.waived_findings)}",
        f"- **Duration**: {report.duration_ms} ms",
        "",
    ]
    if report.findings:
        lines.append("## Violations")
        lines.append("")
        lines.append("| Rule | Severity | Location | Message | Remediation |")
        lines.append("| --- | --- | --- | --- | --- |")
        for f in report.findings:
            loc = f"`{f.path}:{f.line}`" if f.line else f"`{f.path}`"
            lines.append(f"| `{f.rule_id}` | {f.severity.value} | {loc} | {f.message} | {f.remediation} |")
    else:
        lines.append("## Result")
        lines.append("")
        lines.append("All evaluated XLP architectural, research, testing, and documentation checks passed.")
    return "\n".join(lines)


def format_json_report(report: GateReport) -> str:
    return json.dumps(report.to_dict(), indent=2) + "\n"
