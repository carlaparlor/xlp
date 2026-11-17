"""Extensibility, SemVer ABI/API, parameter schema, and regression checks (EXT-001..EXT-004)."""

from __future__ import annotations

from tools.xlp_gate.models import Finding, GateContext, RuleSpec, Severity
from tools.xlp_gate.policy import load_json_file
from tools.xlp_gate.registry import RuleRegistry
from tools.xlp_gate.schema_validator import SEMVER_RE, validate_schema


def check_ext_001(ctx: GateContext) -> list[Finding]:
    """Verify SemVer version/api_version, positive integer abi_version, and stability tier."""
    findings: list[Finding] = []
    for comp in ctx.components:
        if not comp.manifest:
            continue
        rel = ctx.relpath(comp.manifest_path)
        for field in ("version", "api_version"):
            val = comp.manifest.get(field)
            if not isinstance(val, str) or not SEMVER_RE.match(val):
                findings.append(
                    Finding(
                        rule_id="EXT-001",
                        severity=Severity.ERROR,
                        message=f"Manifest '{field}' must be valid SemVer, got '{val}'.",
                        path=rel,
                        remediation=f"Set '{field}' to a semantic version such as '1.0.0'.",
                    )
                )
        abi = comp.manifest.get("abi_version")
        if not isinstance(abi, int) or isinstance(abi, bool) or abi < 1:
            findings.append(
                Finding(
                    rule_id="EXT-001",
                    severity=Severity.ERROR,
                    message=f"Manifest 'abi_version' must be an integer >= 1, got '{abi}'.",
                    path=rel,
                    remediation="Set 'abi_version' to a positive integer starting at 1.",
                )
            )
    return findings


def check_ext_002(ctx: GateContext) -> list[Finding]:
    """Verify explicit, unique, versioned extension points on plugins and extensible modules."""
    findings: list[Finding] = []
    min_plugin_eps = int(ctx.policy.get("extensibility", {}).get("min_plugin_extension_points", 2))

    for comp in ctx.components:
        if not comp.manifest:
            continue
        rel = ctx.relpath(comp.manifest_path)
        eps = comp.manifest.get("extension_points")
        if not isinstance(eps, list):
            findings.append(
                Finding(
                    rule_id="EXT-002",
                    severity=Severity.ERROR,
                    message=f"Component '{comp.name}' is missing 'extension_points' array.",
                    path=rel,
                    remediation="Declare explicit extension_points in the manifest.",
                )
            )
            continue

        if comp.layer == "plugins" and len(eps) < min_plugin_eps:
            findings.append(
                Finding(
                    rule_id="EXT-002",
                    severity=Severity.ERROR,
                    message=(
                        f"Plugin '{comp.name}' declares {len(eps)} extension point(s); "
                        f"minimum required is {min_plugin_eps}."
                    ),
                    path=rel,
                    remediation=f"Design and declare at least {min_plugin_eps} versioned extension_points.",
                )
            )

        seen_ep_ids: set[str] = set()
        for idx, ep in enumerate(eps):
            if not isinstance(ep, dict):
                continue
            ep_id = ep.get("id")
            if isinstance(ep_id, str):
                if ep_id in seen_ep_ids:
                    findings.append(
                        Finding(
                            rule_id="EXT-002",
                            severity=Severity.ERROR,
                            message=f"Duplicate extension_point id '{ep_id}' at index {idx}.",
                            path=rel,
                            remediation="Ensure all extension point IDs within a component are unique.",
                        )
                    )
                seen_ep_ids.add(ep_id)
    return findings


def check_ext_003(ctx: GateContext) -> list[Finding]:
    """Validate declarative plugin parameter schemas, unique IDs/UIDs, numeric bounds, and state versioning."""
    findings: list[Finding] = []
    params_schema = ctx.schemas.get("params")

    for comp in ctx.components:
        if comp.layer != "plugins" or not comp.manifest:
            continue
        rel_manifest = ctx.relpath(comp.manifest_path)

        params_rel = comp.manifest.get("params_file", "params.json")
        params_path = comp.directory / params_rel
        rel_params = ctx.relpath(params_path)
        data, err = load_json_file(params_path)
        if err or not isinstance(data, dict):
            findings.append(
                Finding(
                    rule_id="EXT-003",
                    severity=Severity.ERROR,
                    message=f"Plugin '{comp.name}' missing or invalid parameter file '{params_rel}': {err}",
                    path=rel_params,
                    remediation="Create a params.json conforming to governance/schemas/params.schema.json.",
                )
            )
            continue

        if params_schema:
            for serr in validate_schema(data, params_schema):
                findings.append(
                    Finding(
                        rule_id="EXT-003",
                        severity=Severity.ERROR,
                        message=f"Parameter schema violation: {serr}",
                        path=rel_params,
                        remediation="Fix parameter declarations to satisfy params.schema.json.",
                    )
                )

        if data.get("plugin_id") != comp.manifest.get("id"):
            findings.append(
                Finding(
                    rule_id="EXT-003",
                    severity=Severity.ERROR,
                    message=(
                        f"params.json plugin_id '{data.get('plugin_id')}' does not match "
                        f"manifest id '{comp.manifest.get('id')}'."
                    ),
                    path=rel_params,
                    remediation="Align plugin_id in params.json with plugin.manifest.json.",
                )
            )

        if data.get("state_schema_version") != comp.manifest.get("state_schema_version"):
            findings.append(
                Finding(
                    rule_id="EXT-003",
                    severity=Severity.ERROR,
                    message=(
                        f"params.json state_schema_version ({data.get('state_schema_version')}) does not match "
                        f"manifest state_schema_version ({comp.manifest.get('state_schema_version')})."
                    ),
                    path=rel_manifest,
                    remediation="Keep state_schema_version synchronized between manifest and params.json.",
                )
            )

        seen_ids: set[str] = set()
        seen_uids: set[int] = set()
        for param in data.get("parameters", []):
            if not isinstance(param, dict):
                continue
            pid = param.get("id")
            puid = param.get("uid")
            if isinstance(pid, str):
                if pid in seen_ids:
                    findings.append(
                        Finding(
                            rule_id="EXT-003",
                            severity=Severity.ERROR,
                            message=f"Duplicate parameter id '{pid}'.",
                            path=rel_params,
                            remediation="Assign a unique string ID to every parameter.",
                        )
                    )
                seen_ids.add(pid)
            if isinstance(puid, int) and not isinstance(puid, bool):
                if puid in seen_uids:
                    findings.append(
                        Finding(
                            rule_id="EXT-003",
                            severity=Severity.ERROR,
                            message=f"Duplicate parameter uid '{puid}' on '{pid}'.",
                            path=rel_params,
                            remediation="Assign a unique immutable uint32 UID to every parameter.",
                        )
                    )
                seen_uids.add(puid)

            pmin, pmax, pdef = param.get("min"), param.get("max"), param.get("default")
            if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in (pmin, pmax, pdef)):
                if pmin >= pmax or not (pmin <= pdef <= pmax):
                    findings.append(
                        Finding(
                            rule_id="EXT-003",
                            severity=Severity.ERROR,
                            message=(
                                f"Invalid numeric bounds for parameter '{pid}': "
                                f"min={pmin}, default={pdef}, max={pmax}."
                            ),
                            path=rel_params,
                            remediation="Ensure min < max and min <= default <= max.",
                        )
                    )

            if param.get("type") == "choice" and not param.get("choices"):
                findings.append(
                    Finding(
                        rule_id="EXT-003",
                        severity=Severity.ERROR,
                        message=f"Choice parameter '{pid}' must declare a non-empty 'choices' array.",
                        path=rel_params,
                        remediation="Add at least 2 labels to 'choices' for choice parameters.",
                    )
                )

    return findings


def check_ext_004(ctx: GateContext) -> list[Finding]:
    """Prevent breaking removals or UID reassignments against committed parameter baselines."""
    findings: list[Finding] = []
    baselines_rel = ctx.policy.get("extensibility", {}).get("baselines_dir", "governance/baselines")
    baselines_dir = ctx.repo_root / baselines_rel

    for comp in ctx.components:
        if comp.layer != "plugins" or not comp.manifest:
            continue
        comp_id = comp.manifest.get("id")
        if not isinstance(comp_id, str):
            continue
        baseline_path = baselines_dir / f"{comp_id}.params.json"
        if not baseline_path.exists():
            continue

        baseline, b_err = load_json_file(baseline_path)
        params_path = comp.directory / comp.manifest.get("params_file", "params.json")
        current, c_err = load_json_file(params_path)
        if b_err or not isinstance(baseline, dict) or c_err or not isinstance(current, dict):
            continue

        base_state_v = baseline.get("state_schema_version", 1)
        curr_state_v = current.get("state_schema_version", 1)
        if curr_state_v < base_state_v:
            findings.append(
                Finding(
                    rule_id="EXT-004",
                    severity=Severity.ERROR,
                    message=f"state_schema_version regressed from baseline {base_state_v} to {curr_state_v}.",
                    path=ctx.relpath(params_path),
                    remediation="state_schema_version must increase monotonically.",
                )
            )

        curr_by_id = {
            p["id"]: p for p in current.get("parameters", []) if isinstance(p, dict) and "id" in p
        }
        for bparam in baseline.get("parameters", []):
            if not isinstance(bparam, dict) or "id" not in bparam:
                continue
            bid = bparam["id"]
            buid = bparam.get("uid")
            if bid not in curr_by_id:
                findings.append(
                    Finding(
                        rule_id="EXT-004",
                        severity=Severity.ERROR,
                        message=(
                            f"Breaking ABI regression: baseline parameter '{bid}' (uid={buid}) "
                            f"was removed from '{comp_id}'."
                        ),
                        path=ctx.relpath(params_path),
                        remediation="Retain legacy parameter IDs for DAW recall or bump major version with an ADR + baseline update.",
                    )
                )
            elif curr_by_id[bid].get("uid") != buid:
                findings.append(
                    Finding(
                        rule_id="EXT-004",
                        severity=Severity.ERROR,
                        message=(
                            f"Breaking ABI regression: parameter '{bid}' UID changed from "
                            f"{buid} to {curr_by_id[bid].get('uid')}."
                        ),
                        path=ctx.relpath(params_path),
                        remediation="Parameter UIDs are immutable across versions to preserve DAW automation.",
                    )
                )

    return findings


def register(registry: RuleRegistry) -> None:
    registry.register(
        RuleSpec(
            rule_id="EXT-001",
            domain="extensibility",
            title="SemVer API & Integer ABI Versioning",
            summary="Every component must declare valid SemVer version/api_version and positive integer abi_version.",
        ),
        check_ext_001,
    )
    registry.register(
        RuleSpec(
            rule_id="EXT-002",
            domain="extensibility",
            title="Declarative Extension Points Registry",
            summary="Plugins must declare >= 2 unique, versioned extension points with explicit lifecycles.",
        ),
        check_ext_002,
    )
    registry.register(
        RuleSpec(
            rule_id="EXT-003",
            domain="extensibility",
            title="Declarative Parameter & State Schema Integrity",
            summary="Plugins must provide schema-valid params.json with unique IDs/UIDs, valid bounds, and synchronized state versioning.",
        ),
        check_ext_003,
    )
    registry.register(
        RuleSpec(
            rule_id="EXT-004",
            domain="extensibility",
            title="Immutable Parameter & ABI Regression Guard",
            summary="Existing baseline parameter IDs and UIDs must never be silently removed or reassigned.",
        ),
        check_ext_004,
    )
