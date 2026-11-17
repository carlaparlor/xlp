"""Moddability, mod sandboxing, reference mod, and modding docs checks (MDD-001..MDD-004)."""

from __future__ import annotations

from pathlib import Path

from tools.xlp_gate.markdown_utils import word_count
from tools.xlp_gate.models import Finding, GateContext, RuleSpec, Severity
from tools.xlp_gate.policy import load_json_file
from tools.xlp_gate.registry import RuleRegistry
from tools.xlp_gate.schema_validator import validate_schema

AUDIO_SENSITIVE_SURFACES = {"dsp_graph", "scripts", "modulation_curves"}


def check_mdd_001(ctx: GateContext) -> list[Finding]:
    """Every XLP plugin must enable moddability with >= 2 surfaces and deterministic conflict resolution."""
    findings: list[Finding] = []
    mdd_cfg = ctx.policy.get("moddability", {})
    min_surfaces = int(mdd_cfg.get("min_plugin_mod_surfaces", 2))
    allowed_conflicts = set(
        mdd_cfg.get("allowed_conflict_resolutions", ["deterministic_priority", "explicit_load_order"])
    )

    for comp in ctx.components:
        if comp.layer != "plugins" or not comp.manifest:
            continue
        rel = ctx.relpath(comp.manifest_path)
        modding = comp.manifest.get("modding")
        if not isinstance(modding, dict):
            findings.append(
                Finding(
                    rule_id="MDD-001",
                    severity=Severity.ERROR,
                    message=f"Plugin '{comp.name}' is missing required 'modding' specification.",
                    path=rel,
                    remediation="Declare a complete 'modding' block in plugin.manifest.json.",
                )
            )
            continue

        if modding.get("enabled") is not True:
            findings.append(
                Finding(
                    rule_id="MDD-001",
                    severity=Severity.ERROR,
                    message=f"Plugin '{comp.name}' has modding.enabled != true; every XLP plugin must be moddable.",
                    path=rel,
                    remediation="Enable modding (modding.enabled = true) and define supported mod surfaces.",
                )
            )

        surfaces = modding.get("surfaces", [])
        if not isinstance(surfaces, list) or len(surfaces) < min_surfaces:
            findings.append(
                Finding(
                    rule_id="MDD-001",
                    severity=Severity.ERROR,
                    message=(
                        f"Plugin '{comp.name}' declares {len(surfaces) if isinstance(surfaces, list) else 0} "
                        f"mod surface(s); minimum required is {min_surfaces}."
                    ),
                    path=rel,
                    remediation=f"Expose at least {min_surfaces} mod surfaces (e.g., themes, presets, macros, scripts).",
                )
            )

        conflict = modding.get("conflict_resolution")
        if conflict not in allowed_conflicts:
            findings.append(
                Finding(
                    rule_id="MDD-001",
                    severity=Severity.ERROR,
                    message=(
                        f"Plugin '{comp.name}' uses invalid modding.conflict_resolution '{conflict}' "
                        f"(allowed: {sorted(allowed_conflicts)})."
                    ),
                    path=rel,
                    remediation=f"Set conflict_resolution to one of {sorted(allowed_conflicts)}.",
                )
            )

    return findings


def check_mdd_002(ctx: GateContext) -> list[Finding]:
    """Enforce mod sandbox isolation, zero filesystem/network privileges, and non-crashing fallbacks."""
    findings: list[Finding] = []
    mdd_cfg = ctx.policy.get("moddability", {})
    allowed_fallbacks = set(
        mdd_cfg.get(
            "allowed_fallback_strategies",
            ["bypass_mod_and_warn", "revert_default", "disable_mod_safely"],
        )
    )

    for comp in ctx.components:
        if comp.layer != "plugins" or not comp.manifest:
            continue
        rel = ctx.relpath(comp.manifest_path)
        modding = comp.manifest.get("modding")
        if not isinstance(modding, dict):
            continue

        seen_ids: set[str] = set()
        for idx, surf in enumerate(modding.get("surfaces", [])):
            if not isinstance(surf, dict):
                continue
            sid = surf.get("id", f"surface[{idx}]")
            if isinstance(surf.get("id"), str):
                if surf["id"] in seen_ids:
                    findings.append(
                        Finding(
                            rule_id="MDD-002",
                            severity=Severity.ERROR,
                            message=f"Duplicate mod surface id '{surf['id']}'.",
                            path=rel,
                            remediation="Ensure every mod surface ID is unique within the plugin.",
                        )
                    )
                seen_ids.add(surf["id"])

            if surf.get("allow_filesystem") is not False:
                findings.append(
                    Finding(
                        rule_id="MDD-002",
                        severity=Severity.ERROR,
                        message=f"Mod surface '{sid}' must enforce allow_filesystem=false.",
                        path=rel,
                        remediation="Disable direct filesystem access for sandboxed user mods.",
                    )
                )
            if surf.get("allow_network") is not False:
                findings.append(
                    Finding(
                        rule_id="MDD-002",
                        severity=Severity.ERROR,
                        message=f"Mod surface '{sid}' must enforce allow_network=false.",
                        path=rel,
                        remediation="Disable network access for sandboxed user mods.",
                    )
                )

            kind = surf.get("kind")
            if kind in AUDIO_SENSITIVE_SURFACES and surf.get("rt_safe_enforced") is not True:
                findings.append(
                    Finding(
                        rule_id="MDD-002",
                        severity=Severity.ERROR,
                        message=f"Audio-sensitive mod surface '{sid}' ({kind}) must set rt_safe_enforced=true.",
                        path=rel,
                        remediation="Enforce real-time execution budgets and non-blocking isolation on audio mod surfaces.",
                    )
                )

            fallback = surf.get("fallback_on_error")
            if fallback not in allowed_fallbacks:
                findings.append(
                    Finding(
                        rule_id="MDD-002",
                        severity=Severity.ERROR,
                        message=(
                            f"Mod surface '{sid}' declares unsupported fallback_on_error '{fallback}' "
                            f"(allowed: {sorted(allowed_fallbacks)})."
                        ),
                        path=rel,
                        remediation=f"Set fallback_on_error to a safe non-crashing strategy: {sorted(allowed_fallbacks)}.",
                    )
                )

    return findings


def _validate_mod_pack(
    mod_manifest_path: Path,
    ctx: GateContext,
    plugin_map: dict[str, dict],
) -> list[Finding]:
    findings: list[Finding] = []
    rel = ctx.relpath(mod_manifest_path)
    data, err = load_json_file(mod_manifest_path)
    if err or not isinstance(data, dict):
        return [
            Finding(
                rule_id="MDD-003",
                severity=Severity.ERROR,
                message=f"Invalid or missing mod pack manifest: {err}",
                path=rel,
                remediation="Provide a valid mod.manifest.json conforming to mod.manifest.schema.json.",
            )
        ]

    schema = ctx.schemas.get("mod.manifest")
    if schema:
        for serr in validate_schema(data, schema):
            findings.append(
                Finding(
                    rule_id="MDD-003",
                    severity=Severity.ERROR,
                    message=f"Mod manifest schema violation: {serr}",
                    path=rel,
                    remediation="Update mod.manifest.json to satisfy governance/schemas/mod.manifest.schema.json.",
                )
            )

    caps = data.get("requested_capabilities", {})
    if isinstance(caps, dict):
        if caps.get("filesystem") is True or caps.get("network") is True:
            findings.append(
                Finding(
                    rule_id="MDD-003",
                    severity=Severity.ERROR,
                    message="Mod pack requests forbidden privileged capabilities (filesystem or network).",
                    path=rel,
                    remediation="Set requested_capabilities.filesystem and .network to false.",
                )
            )

    mod_dir = mod_manifest_path.parent
    for entry in data.get("entry_files", []):
        if not isinstance(entry, str):
            continue
        if ".." in Path(entry).parts or Path(entry).is_absolute():
            findings.append(
                Finding(
                    rule_id="MDD-003",
                    severity=Severity.ERROR,
                    message=f"Mod pack entry_file '{entry}' attempts unsafe path traversal.",
                    path=rel,
                    remediation="Use relative paths contained strictly within the mod pack directory.",
                )
            )
        elif not (mod_dir / entry).exists():
            findings.append(
                Finding(
                    rule_id="MDD-003",
                    severity=Severity.ERROR,
                    message=f"Mod pack entry_file '{entry}' does not exist.",
                    path=rel,
                    remediation="Include all declared entry_files inside the mod pack directory.",
                )
            )

    target = data.get("target_plugin")
    if isinstance(target, str) and target != "xlp.*" and target in plugin_map:
        plugin_manifest = plugin_map[target]
        allowed_surfaces = {
            s.get("id")
            for s in plugin_manifest.get("modding", {}).get("surfaces", [])
            if isinstance(s, dict)
        }
        max_mem_allowed = max(
            (
                int(s.get("memory_limit_kb", 0))
                for s in plugin_manifest.get("modding", {}).get("surfaces", [])
                if isinstance(s, dict)
            ),
            default=0,
        )
        for surf_id in data.get("surfaces", []):
            if surf_id not in allowed_surfaces:
                findings.append(
                    Finding(
                        rule_id="MDD-003",
                        severity=Severity.ERROR,
                        message=(
                            f"Mod targets undeclared surface '{surf_id}' on plugin '{target}' "
                            f"(supported: {sorted(allowed_surfaces)})."
                        ),
                        path=rel,
                        remediation="Target only surfaces declared in the plugin's modding.surfaces.",
                    )
                )
        if isinstance(caps, dict) and isinstance(caps.get("max_memory_kb"), int):
            if max_mem_allowed > 0 and caps["max_memory_kb"] > max_mem_allowed:
                findings.append(
                    Finding(
                        rule_id="MDD-003",
                        severity=Severity.ERROR,
                        message=(
                            f"Mod requests {caps['max_memory_kb']} KB memory, exceeding plugin limit "
                            f"{max_mem_allowed} KB."
                        ),
                        path=rel,
                        remediation="Reduce requested_capabilities.max_memory_kb within the plugin's sandbox ceiling.",
                    )
                )

    return findings


def check_mdd_003(ctx: GateContext) -> list[Finding]:
    """Validate all mod packs under mods/ and every plugin's required reference mod pack."""
    findings: list[Finding] = []
    plugin_map = {
        comp.manifest["id"]: comp.manifest
        for comp in ctx.components
        if comp.layer == "plugins" and comp.manifest and isinstance(comp.manifest.get("id"), str)
    }

    checked_paths: set[Path] = set()

    # 1. Every plugin MUST provide a valid reference mod fixture.
    for comp in ctx.components:
        if comp.layer != "plugins" or not comp.manifest:
            continue
        modding = comp.manifest.get("modding")
        if not isinstance(modding, dict):
            continue
        ref_rel = modding.get("reference_mod_path")
        if not isinstance(ref_rel, str) or not ref_rel.strip():
            findings.append(
                Finding(
                    rule_id="MDD-003",
                    severity=Severity.ERROR,
                    message=f"Plugin '{comp.name}' must declare modding.reference_mod_path.",
                    path=ctx.relpath(comp.manifest_path),
                    remediation="Create a bundled reference mod pack and reference it via modding.reference_mod_path.",
                )
            )
            continue

        ref_path = (comp.directory / ref_rel).resolve()
        if ref_path.is_dir():
            ref_manifest = ref_path / "mod.manifest.json"
        else:
            ref_manifest = ref_path

        if not ref_manifest.exists():
            findings.append(
                Finding(
                    rule_id="MDD-003",
                    severity=Severity.ERROR,
                    message=f"Plugin '{comp.name}' reference mod manifest not found at '{ctx.relpath(ref_manifest)}'.",
                    path=ctx.relpath(comp.manifest_path),
                    remediation="Add a working reference mod pack with mod.manifest.json.",
                )
            )
        else:
            checked_paths.add(ref_manifest.resolve())
            findings.extend(_validate_mod_pack(ref_manifest, ctx, plugin_map))

    # 2. Validate every standalone mod pack in mods/.
    mods_dir = ctx.repo_root / ctx.policy.get("moddability", {}).get("mods_dir", "mods")
    if mods_dir.is_dir():
        for child in sorted(mods_dir.iterdir()):
            if not child.is_dir() or child.name.startswith("."):
                continue
            mod_manifest = (child / "mod.manifest.json").resolve()
            if mod_manifest in checked_paths:
                continue
            checked_paths.add(mod_manifest)
            findings.extend(_validate_mod_pack(mod_manifest, ctx, plugin_map))

    return findings


def check_mdd_004(ctx: GateContext) -> list[Finding]:
    """Verify every XLP plugin ships a substantive docs/modding.md guide."""
    findings: list[Finding] = []
    min_words = int(ctx.policy.get("documentation", {}).get("min_doc_words", 40))

    for comp in ctx.components:
        if comp.layer != "plugins" or not comp.manifest:
            continue
        mod_doc_rel = comp.manifest.get("docs", {}).get("modding", "docs/modding.md")
        mod_doc_path = comp.directory / mod_doc_rel
        rel = ctx.relpath(mod_doc_path)
        if not mod_doc_path.is_file():
            findings.append(
                Finding(
                    rule_id="MDD-004",
                    severity=Severity.ERROR,
                    message=f"Plugin '{comp.name}' is missing required modding guide '{mod_doc_rel}'.",
                    path=rel,
                    remediation="Author a thorough docs/modding.md covering surfaces, sandbox limits, and examples.",
                )
            )
            continue

        text = mod_doc_path.read_text(encoding="utf-8", errors="replace")
        words = word_count(text)
        if words < min_words:
            findings.append(
                Finding(
                    rule_id="MDD-004",
                    severity=Severity.ERROR,
                    message=f"Plugin modding guide '{rel}' has only {words} words (minimum {min_words}).",
                    path=rel,
                    remediation="Expand docs/modding.md with surface specifications, sandbox rules, and load examples.",
                )
            )
        lower = text.lower()
        for required_topic in ("sandbox", "surface"):
            if required_topic not in lower:
                findings.append(
                    Finding(
                        rule_id="MDD-004",
                        severity=Severity.ERROR,
                        message=f"Plugin modding guide '{rel}' must document '{required_topic}' boundaries.",
                        path=rel,
                        remediation=f"Document mod {required_topic} capabilities and limits in '{rel}'.",
                    )
                )

    return findings


def register(registry: RuleRegistry) -> None:
    registry.register(
        RuleSpec(
            rule_id="MDD-001",
            domain="moddability",
            title="Mandatory Plugin Modding Surfaces & Conflict Resolution",
            summary="Every XLP plugin must enable modding with >= 2 surfaces and deterministic conflict resolution.",
        ),
        check_mdd_001,
    )
    registry.register(
        RuleSpec(
            rule_id="MDD-002",
            domain="moddability",
            title="Mod Sandbox Isolation & Crash-Safe Fallback Contract",
            summary="Mod surfaces must forbid filesystem/network access, enforce RT bounds on audio hooks, and fail safely.",
        ),
        check_mdd_002,
    )
    registry.register(
        RuleSpec(
            rule_id="MDD-003",
            domain="moddability",
            title="Mod Pack Schema & Reference Mod Verification",
            summary="All mod packs and each plugin's bundled reference mod must pass schema, path, and capability checks.",
        ),
        check_mdd_003,
    )
    registry.register(
        RuleSpec(
            rule_id="MDD-004",
            domain="moddability",
            title="Plugin Modding Documentation Completeness",
            summary="Every XLP plugin must provide a substantive docs/modding.md detailing surfaces and sandbox rules.",
        ),
        check_mdd_004,
    )
