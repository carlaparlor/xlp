"""Brand identity and naming consistency checks (BRD-001..BRD-003)."""

from __future__ import annotations

import re

from tools.xlp_gate.models import Finding, GateContext, RuleSpec, Severity
from tools.xlp_gate.registry import RuleRegistry
from tools.xlp_gate.schema_validator import validate_schema

PLUGIN_DIR_RE = re.compile(r"^xlp_[a-z][a-z0-9_]*$")
MODULE_ID_RE = re.compile(r"^xlp\.(core|modules|adapters|tools)\.[a-z][a-z0-9_]*$")


def check_brd_001(ctx: GateContext) -> list[Finding]:
    findings: list[Finding] = []
    brand_rel = ctx.policy.get("brand_file", "governance/brand.json")
    if ctx.brand is None:
        return [
            Finding(
                rule_id="BRD-001",
                severity=Severity.ERROR,
                message=f"Missing or unreadable brand specification file '{brand_rel}'.",
                path=brand_rel,
                remediation="Create a valid governance/brand.json conforming to governance/schemas/brand.schema.json.",
            )
        ]

    schema = ctx.schemas.get("brand")
    if schema is None:
        return [
            Finding(
                rule_id="BRD-001",
                severity=Severity.ERROR,
                message="Missing brand JSON schema 'governance/schemas/brand.schema.json'.",
                path="governance/schemas/brand.schema.json",
                remediation="Restore governance/schemas/brand.schema.json.",
            )
        ]

    for err in validate_schema(ctx.brand, schema):
        findings.append(
            Finding(
                rule_id="BRD-001",
                severity=Severity.ERROR,
                message=f"Brand specification schema violation: {err}",
                path=brand_rel,
                remediation="Update governance/brand.json to satisfy brand.schema.json.",
            )
        )
    return findings


def check_brd_002(ctx: GateContext) -> list[Finding]:
    findings: list[Finding] = []
    seen_codes: dict[str, str] = {}
    seen_uids: dict[str, str] = {}

    for comp in ctx.components:
        if comp.layer != "plugins":
            continue
        rel = ctx.relpath(comp.manifest_path)
        if not PLUGIN_DIR_RE.match(comp.name):
            findings.append(
                Finding(
                    rule_id="BRD-002",
                    severity=Severity.ERROR,
                    message=f"Plugin directory '{comp.name}' must match 'xlp_<snake_slug>'.",
                    path=ctx.relpath(comp.directory),
                    remediation="Rename plugin directory to start with 'xlp_' using lowercase snake_case.",
                )
            )
        if not comp.manifest:
            continue

        expected_slug = comp.name.removeprefix("xlp_")
        expected_id = f"xlp.{expected_slug}"
        actual_id = comp.manifest.get("id")
        if actual_id != expected_id:
            findings.append(
                Finding(
                    rule_id="BRD-002",
                    severity=Severity.ERROR,
                    message=f"Plugin id '{actual_id}' must match directory slug '{expected_id}'.",
                    path=rel,
                    remediation=f"Set manifest 'id' to '{expected_id}'.",
                )
            )

        if comp.manifest.get("brand") != "xlp":
            findings.append(
                Finding(
                    rule_id="BRD-002",
                    severity=Severity.ERROR,
                    message=f"Plugin brand must be 'xlp', found '{comp.manifest.get('brand')}'.",
                    path=rel,
                    remediation="Set manifest 'brand' to 'xlp'.",
                )
            )

        code = comp.manifest.get("plugin_code")
        if isinstance(code, str):
            if code in seen_codes:
                findings.append(
                    Finding(
                        rule_id="BRD-002",
                        severity=Severity.ERROR,
                        message=f"Duplicate 4-char plugin_code '{code}' collides with '{seen_codes[code]}'.",
                        path=rel,
                        remediation="Assign a globally unique 4-character alphanumeric plugin_code.",
                    )
                )
            else:
                seen_codes[code] = rel

        comp_uid = comp.manifest.get("vst3_component_uid")
        ctrl_uid = comp.manifest.get("vst3_controller_uid")
        if isinstance(comp_uid, str) and isinstance(ctrl_uid, str) and comp_uid.lower() == ctrl_uid.lower():
            findings.append(
                Finding(
                    rule_id="BRD-002",
                    severity=Severity.ERROR,
                    message="vst3_component_uid and vst3_controller_uid must be distinct UUIDs.",
                    path=rel,
                    remediation="Generate separate UUID v4 identifiers for VST3 component and controller.",
                )
            )

        for label, uid in (("vst3_component_uid", comp_uid), ("vst3_controller_uid", ctrl_uid)):
            if isinstance(uid, str):
                key = uid.lower()
                if key in seen_uids:
                    findings.append(
                        Finding(
                            rule_id="BRD-002",
                            severity=Severity.ERROR,
                            message=f"Duplicate {label} '{uid}' collides with '{seen_uids[key]}'.",
                            path=rel,
                            remediation="Generate a unique UUID v4 not used by any other XLP plugin.",
                        )
                    )
                else:
                    seen_uids[key] = f"{rel}:{label}"

    return findings


def check_brd_003(ctx: GateContext) -> list[Finding]:
    findings: list[Finding] = []
    seen_ids: dict[str, str] = {}

    for comp in ctx.components:
        if comp.layer not in ("core", "modules", "adapters", "tools"):
            continue
        if not comp.manifest:
            continue
        rel = ctx.relpath(comp.manifest_path)
        comp_id = comp.manifest.get("id")
        expected_id = f"xlp.{comp.layer}.{comp.name}"
        if not isinstance(comp_id, str) or not MODULE_ID_RE.match(comp_id) or comp_id != expected_id:
            findings.append(
                Finding(
                    rule_id="BRD-003",
                    severity=Severity.ERROR,
                    message=f"Module id '{comp_id}' must match canonical XLP identifier '{expected_id}'.",
                    path=rel,
                    remediation=f"Set manifest 'id' to '{expected_id}'.",
                )
            )
        if comp.manifest.get("brand") != "xlp":
            findings.append(
                Finding(
                    rule_id="BRD-003",
                    severity=Severity.ERROR,
                    message=f"Module brand must be 'xlp', found '{comp.manifest.get('brand')}'.",
                    path=rel,
                    remediation="Set manifest 'brand' to 'xlp'.",
                )
            )
        if isinstance(comp_id, str):
            if comp_id in seen_ids:
                findings.append(
                    Finding(
                        rule_id="BRD-003",
                        severity=Severity.ERROR,
                        message=f"Duplicate component id '{comp_id}' collides with '{seen_ids[comp_id]}'.",
                        path=rel,
                        remediation="Ensure every XLP component has a unique canonical identifier.",
                    )
                )
            else:
                seen_ids[comp_id] = rel

    return findings


def register(registry: RuleRegistry) -> None:
    registry.register(
        RuleSpec(
            rule_id="BRD-001",
            domain="brand",
            title="XLP Brand Specification Validity",
            summary="governance/brand.json must exist and satisfy brand.schema.json with brand 'xlp'.",
        ),
        check_brd_001,
    )
    registry.register(
        RuleSpec(
            rule_id="BRD-002",
            domain="brand",
            title="XLP Plugin Identity & UID Uniqueness",
            summary="Every plugin must follow xlp_<slug> naming, brand 'xlp', unique 4-char code, and distinct VST3 UUIDs.",
        ),
        check_brd_002,
    )
    registry.register(
        RuleSpec(
            rule_id="BRD-003",
            domain="brand",
            title="XLP Module Canonical Identifier Convention",
            summary="Every non-plugin component must use canonical 'xlp.<layer>.<name>' ID and brand 'xlp'.",
        ),
        check_brd_003,
    )
