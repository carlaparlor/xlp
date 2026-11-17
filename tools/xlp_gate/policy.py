"""Policy, schema, and component discovery loader for the XLP enforcement gate."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tools.xlp_gate.models import Component, GateContext, RuleSpec

IGNORED_DIRS = {
    "__pycache__",
    ".git",
    ".venv",
    "node_modules",
    "build",
    "dist",
    "out",
    "target",
}


def load_json_file(path: Path) -> tuple[Any | None, str | None]:
    if not path.exists():
        return None, f"File does not exist: {path}"
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except json.JSONDecodeError as exc:
        return None, f"Invalid JSON in {path.name} (line {exc.lineno}, col {exc.colno}): {exc.msg}"
    except OSError as exc:
        return None, f"Unable to read {path}: {exc}"


def load_schemas(repo_root: Path) -> dict[str, dict[str, Any]]:
    schemas_dir = repo_root / "governance" / "schemas"
    schemas: dict[str, dict[str, Any]] = {}
    if not schemas_dir.is_dir():
        return schemas
    for schema_file in sorted(schemas_dir.glob("*.schema.json")):
        data, err = load_json_file(schema_file)
        if err is None and isinstance(data, dict):
            key = schema_file.name.removesuffix(".schema.json")
            schemas[key] = data
    return schemas


def discover_components(repo_root: Path, policy: dict[str, Any]) -> list[Component]:
    components: list[Component] = []
    layers = policy.get("layers", {})
    for layer_name, layer_cfg in layers.items():
        layer_dir = repo_root / layer_cfg.get("directory", layer_name)
        manifest_filename = layer_cfg.get("manifest_filename", "module.manifest.json")
        if not layer_dir.is_dir():
            continue
        for child in sorted(layer_dir.iterdir()):
            if not child.is_dir():
                continue
            if child.name.startswith(".") or child.name in IGNORED_DIRS:
                continue
            manifest_path = child / manifest_filename
            manifest_data: dict[str, Any] | None = None
            manifest_error: str | None = None
            if manifest_path.exists():
                raw, err = load_json_file(manifest_path)
                if err:
                    manifest_error = err
                elif isinstance(raw, dict):
                    manifest_data = raw
                else:
                    manifest_error = f"Manifest root must be a JSON object: {manifest_path}"
            else:
                manifest_error = f"Missing required manifest '{manifest_filename}'"
            components.append(
                Component(
                    layer=layer_name,
                    name=child.name,
                    directory=child,
                    manifest_path=manifest_path,
                    manifest=manifest_data,
                    manifest_error=manifest_error,
                )
            )
    return components


def build_context(
    repo_root: Path,
    registered_rules: dict[str, RuleSpec],
    *,
    run_tests: bool = False,
    strict: bool = True,
    today_iso: str | None = None,
) -> GateContext:
    policy_path = repo_root / "governance" / "policy.json"
    policy_raw, policy_err = load_json_file(policy_path)
    policy = policy_raw if (policy_err is None and isinstance(policy_raw, dict)) else {}

    brand_rel = policy.get("brand_file", "governance/brand.json")
    brand_raw, _ = load_json_file(repo_root / brand_rel)
    brand = brand_raw if isinstance(brand_raw, dict) else None

    waivers_rel = policy.get("waivers_file", "governance/waivers.json")
    waivers_raw, _ = load_json_file(repo_root / waivers_rel)
    waivers = (
        waivers_raw.get("waivers", [])
        if isinstance(waivers_raw, dict) and isinstance(waivers_raw.get("waivers"), list)
        else []
    )

    trace_rel = policy.get("traceability_file", "governance/traceability.json")
    trace_raw, _ = load_json_file(repo_root / trace_rel)
    traceability = trace_raw if isinstance(trace_raw, dict) else None

    schemas = load_schemas(repo_root)
    components = discover_components(repo_root, policy) if policy else []

    return GateContext(
        repo_root=repo_root.resolve(),
        policy=policy,
        brand=brand,
        waivers=waivers,
        traceability=traceability,
        schemas=schemas,
        components=components,
        registered_rules=registered_rules,
        run_tests=run_tests,
        strict=strict,
        today_iso=today_iso,
    )
