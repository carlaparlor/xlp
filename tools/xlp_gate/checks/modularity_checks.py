"""Modular architecture, layer boundary, acyclicity, and cohesion checks (MOD-001..MOD-006)."""

from __future__ import annotations

import re
from pathlib import Path

from tools.xlp_gate.models import Component, Finding, GateContext, RuleSpec, Severity
from tools.xlp_gate.registry import RuleRegistry
from tools.xlp_gate.schema_validator import validate_schema

SOURCE_EXTS = {".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx", ".py", ".rs", ".js", ".ts", ".tsx"}

CPP_INCLUDE_RE = re.compile(r'^\s*#\s*include\s*[<"]([^">]+)[">]')
PY_IMPORT_RE = re.compile(r"^\s*(?:from|import)\s+([a-zA-Z0-9_.]+)")
JS_IMPORT_RE = re.compile(r"""(?:import\s+.*?\s+from\s+|require\s*\(\s*)['"]([^'"]+)['"]""")
RUST_USE_RE = re.compile(r"^\s*(?:pub\s+)?use\s+([a-zA-Z0-9_:]+)")

LAYER_DIRS = ("core", "modules", "adapters", "plugins", "mods", "tools")


def _iter_production_source_files(comp: Component) -> list[Path]:
    files: list[Path] = []
    if not comp.directory.is_dir():
        return files
    for path in sorted(comp.directory.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SOURCE_EXTS:
            continue
        rel_parts = path.relative_to(comp.directory).parts
        if any(part in ("tests", "test", "__pycache__", "fixtures", "build") for part in rel_parts):
            continue
        files.append(path)
    return files


def _detect_source_component_refs(comp: Component, ctx: GateContext) -> list[tuple[str, int, str, str]]:
    """Return list of `(file_rel, lineno, target_layer, target_name)` referenced by `comp`."""
    refs: list[tuple[str, int, str, str]] = []
    for src in _iter_production_source_files(comp):
        rel = ctx.relpath(src)
        try:
            lines = src.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for lineno, line in enumerate(lines, start=1):
            candidates: list[str] = []
            m_cpp = CPP_INCLUDE_RE.match(line)
            if m_cpp:
                candidates.append(m_cpp.group(1).replace("\\", "/"))
            m_py = PY_IMPORT_RE.match(line)
            if m_py:
                candidates.append(m_py.group(1).replace(".", "/"))
            for m_js in JS_IMPORT_RE.finditer(line):
                candidates.append(m_js.group(1).replace("\\", "/"))
            m_rs = RUST_USE_RE.match(line)
            if m_rs:
                candidates.append(m_rs.group(1).replace("::", "/"))

            for cand in candidates:
                parts = [p for p in cand.split("/") if p and p not in (".", "..")]
                for idx, part in enumerate(parts):
                    if part in LAYER_DIRS and idx + 1 < len(parts):
                        target_layer = part
                        target_name = parts[idx + 1]
                        if target_layer == comp.layer and target_name == comp.name:
                            continue
                        refs.append((rel, lineno, target_layer, target_name))
                        break
    return refs


def check_mod_001(ctx: GateContext) -> list[Finding]:
    findings: list[Finding] = []
    for comp in ctx.components:
        rel = ctx.relpath(comp.manifest_path)
        if comp.manifest_error:
            findings.append(
                Finding(
                    rule_id="MOD-001",
                    severity=Severity.ERROR,
                    message=f"Component '{comp.layer}/{comp.name}': {comp.manifest_error}",
                    path=rel,
                    remediation="Create a valid manifest file matching the layer's JSON schema.",
                )
            )
            continue

        schema_key = "plugin.manifest" if comp.layer == "plugins" else "module.manifest"
        schema = ctx.schemas.get(schema_key)
        if schema is None:
            findings.append(
                Finding(
                    rule_id="MOD-001",
                    severity=Severity.ERROR,
                    message=f"Missing schema '{schema_key}.schema.json'.",
                    path=f"governance/schemas/{schema_key}.schema.json",
                    remediation="Restore the missing manifest JSON schema.",
                )
            )
            continue

        assert comp.manifest is not None
        for err in validate_schema(comp.manifest, schema):
            findings.append(
                Finding(
                    rule_id="MOD-001",
                    severity=Severity.ERROR,
                    message=f"Manifest schema violation: {err}",
                    path=rel,
                    remediation=f"Fix '{rel}' to satisfy governance/schemas/{schema_key}.schema.json.",
                )
            )
        if comp.manifest.get("layer") != comp.layer:
            findings.append(
                Finding(
                    rule_id="MOD-001",
                    severity=Severity.ERROR,
                    message=f"Manifest layer '{comp.manifest.get('layer')}' does not match directory layer '{comp.layer}'.",
                    path=rel,
                    remediation=f"Set manifest 'layer' to '{comp.layer}'.",
                )
            )
    return findings


def check_mod_002(ctx: GateContext) -> list[Finding]:
    findings: list[Finding] = []
    layers_cfg = ctx.policy.get("layers", {})

    for comp in ctx.components:
        allowed = set(layers_cfg.get(comp.layer, {}).get("allowed_dependencies", []))
        rel_manifest = ctx.relpath(comp.manifest_path)

        # 1. Check declared manifest dependencies.
        if comp.manifest and isinstance(comp.manifest.get("dependencies"), list):
            for dep_id in comp.manifest["dependencies"]:
                if not isinstance(dep_id, str):
                    continue
                parts = dep_id.split(".")
                if len(parts) < 3 or parts[0] != "xlp":
                    continue
                dep_layer = parts[1]
                if dep_layer not in allowed:
                    findings.append(
                        Finding(
                            rule_id="MOD-002",
                            severity=Severity.ERROR,
                            message=(
                                f"Forbidden layer dependency: '{comp.layer}/{comp.name}' declares dependency "
                                f"'{dep_id}' in layer '{dep_layer}' (allowed: {sorted(allowed)})."
                            ),
                            path=rel_manifest,
                            remediation="Refactor shared functionality downward into 'core/' or 'modules/'.",
                        )
                    )

        # 2. Check source-level cross-layer imports & cross-plugin imports.
        for file_rel, lineno, target_layer, target_name in _detect_source_component_refs(comp, ctx):
            if target_layer == "plugins" and comp.layer == "plugins":
                findings.append(
                    Finding(
                        rule_id="MOD-002",
                        severity=Severity.ERROR,
                        message=(
                            f"Cross-plugin internal import forbidden: '{comp.name}' imports "
                            f"'plugins/{target_name}'."
                        ),
                        path=file_rel,
                        line=lineno,
                        remediation="Extract shared code into 'core/' or 'modules/' and declare the dependency.",
                    )
                )
            elif target_layer not in allowed:
                findings.append(
                    Finding(
                        rule_id="MOD-002",
                        severity=Severity.ERROR,
                        message=(
                            f"Layer boundary violation: '{comp.layer}/{comp.name}' imports "
                            f"'{target_layer}/{target_name}' (allowed layers: {sorted(allowed)})."
                        ),
                        path=file_rel,
                        line=lineno,
                        remediation="Remove upward/sideways layer import and depend only on allowed lower layers.",
                    )
                )

    return findings


def check_mod_003(ctx: GateContext) -> list[Finding]:
    """Detect any directed cycle across manifest dependencies and source-level component imports."""
    findings: list[Finding] = []
    graph: dict[str, set[str]] = {}
    comp_paths: dict[str, str] = {}

    for comp in ctx.components:
        node_id = comp.component_id or f"xlp.{comp.layer}.{comp.name}"
        graph.setdefault(node_id, set())
        comp_paths[node_id] = ctx.relpath(comp.manifest_path)

        if comp.manifest and isinstance(comp.manifest.get("dependencies"), list):
            for dep in comp.manifest["dependencies"]:
                if isinstance(dep, str):
                    graph[node_id].add(dep)

        for _, _, target_layer, target_name in _detect_source_component_refs(comp, ctx):
            target_id = (
                f"xlp.{target_name.removeprefix('xlp_')}"
                if target_layer == "plugins"
                else f"xlp.{target_layer}.{target_name}"
            )
            graph[node_id].add(target_id)

    state: dict[str, int] = {}  # 0=unvisited, 1=visiting, 2=done
    reported_cycles: set[tuple[str, ...]] = set()

    def dfs(node: str, stack: list[str]) -> None:
        state[node] = 1
        stack.append(node)
        for nxt in sorted(graph.get(node, set())):
            if nxt not in graph:
                continue
            nxt_state = state.get(nxt, 0)
            if nxt_state == 1:
                idx = stack.index(nxt)
                cycle = stack[idx:] + [nxt]
                canonical = tuple(sorted(set(cycle)))
                if canonical not in reported_cycles:
                    reported_cycles.add(canonical)
                    findings.append(
                        Finding(
                            rule_id="MOD-003",
                            severity=Severity.ERROR,
                            message=f"Circular dependency detected: {' -> '.join(cycle)}.",
                            path=comp_paths.get(node, "governance/policy.json"),
                            remediation="Break the cycle by extracting shared interfaces into a lower-layer module.",
                        )
                    )
            elif nxt_state == 0:
                dfs(nxt, stack)
        stack.pop()
        state[node] = 2

    for node in sorted(graph.keys()):
        if state.get(node, 0) == 0:
            dfs(node, [])

    return findings


def check_mod_004(ctx: GateContext) -> list[Finding]:
    """Ensure every source-level cross-component import is declared in manifest dependencies."""
    findings: list[Finding] = []
    known_ids = {c.component_id for c in ctx.components if c.component_id}
    known_layer_names = {(c.layer, c.name): c.component_id for c in ctx.components if c.component_id}

    for comp in ctx.components:
        if not comp.manifest:
            continue
        declared = set(comp.manifest.get("dependencies", []))
        rel_manifest = ctx.relpath(comp.manifest_path)

        # Ensure every declared dependency exists in the workspace if it starts with xlp.
        for dep in sorted(declared):
            if dep.startswith("xlp.") and dep not in known_ids:
                findings.append(
                    Finding(
                        rule_id="MOD-004",
                        severity=Severity.ERROR,
                        message=f"Manifest declares non-existent internal dependency '{dep}'.",
                        path=rel_manifest,
                        remediation="Remove dead dependency or create the referenced XLP component.",
                    )
                )

        # Ensure every source-imported known component is explicitly declared.
        for file_rel, lineno, target_layer, target_name in _detect_source_component_refs(comp, ctx):
            target_id = known_layer_names.get((target_layer, target_name))
            if target_id and target_id not in declared:
                findings.append(
                    Finding(
                        rule_id="MOD-004",
                        severity=Severity.ERROR,
                        message=(
                            f"Undeclared dependency: '{file_rel}' imports '{target_id}', "
                            f"which is missing from '{rel_manifest}' dependencies."
                        ),
                        path=file_rel,
                        line=lineno,
                        remediation=f"Add '{target_id}' to 'dependencies' in '{rel_manifest}'.",
                    )
                )

    return findings


def check_mod_005(ctx: GateContext) -> list[Finding]:
    """Enforce DSP / UI / Host Format Adapter separation."""
    findings: list[Finding] = []
    mod_cfg = ctx.policy.get("modularity", {})
    forbidden_ui_tokens = [tok.lower() for tok in mod_cfg.get("dsp_forbidden_ui_includes", [])]
    forbidden_dsp_in_adapter = [tok.lower() for tok in mod_cfg.get("adapter_forbidden_dsp_patterns", [])]

    for comp in ctx.components:
        if comp.layer == "plugins":
            for required_sub in ("dsp", "ui"):
                sub_dir = comp.directory / required_sub
                if not sub_dir.is_dir():
                    findings.append(
                        Finding(
                            rule_id="MOD-005",
                            severity=Severity.ERROR,
                            message=f"Plugin '{comp.name}' is missing required '{required_sub}/' separation directory.",
                            path=ctx.relpath(comp.directory),
                            remediation=f"Organize plugin code into dedicated '{required_sub}/' subdirectory.",
                        )
                    )

        for src in _iter_production_source_files(comp):
            rel = ctx.relpath(src)
            parts = [p.lower() for p in src.relative_to(comp.directory).parts]
            is_dsp = "dsp" in parts or (comp.manifest and comp.manifest.get("kind") == "dsp")
            is_adapter = comp.layer == "adapters"
            if not (is_dsp or is_adapter):
                continue

            try:
                lines = src.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                continue

            for lineno, line in enumerate(lines, start=1):
                lower = line.lower()
                if is_dsp and ("#include" in lower or "import " in lower or "use " in lower):
                    for tok in forbidden_ui_tokens:
                        if tok in lower:
                            findings.append(
                                Finding(
                                    rule_id="MOD-005",
                                    severity=Severity.ERROR,
                                    message=f"DSP code must not reference UI dependency '{tok}'.",
                                    path=rel,
                                    line=lineno,
                                    remediation="Move UI logic into 'ui/' and communicate via lock-free state/parameters.",
                                )
                            )
                            break
                if is_adapter:
                    for tok in forbidden_dsp_in_adapter:
                        if tok in lower:
                            findings.append(
                                Finding(
                                    rule_id="MOD-005",
                                    severity=Severity.ERROR,
                                    message=f"Format adapter contains raw DSP pattern '{tok}'.",
                                    path=rel,
                                    line=lineno,
                                    remediation="Keep host adapters thin and move DSP algorithms into 'core/' or 'modules/'.",
                                )
                            )
                            break

    return findings


def check_mod_006(ctx: GateContext) -> list[Finding]:
    """Enforce production source file line ceiling to prevent monolithic god-files."""
    findings: list[Finding] = []
    max_lines = int(ctx.policy.get("modularity", {}).get("max_source_file_lines", 600))

    for comp in ctx.components:
        for src in _iter_production_source_files(comp):
            try:
                line_count = len(src.read_text(encoding="utf-8", errors="replace").splitlines())
            except OSError:
                continue
            if line_count > max_lines:
                findings.append(
                    Finding(
                        rule_id="MOD-006",
                        severity=Severity.ERROR,
                        message=f"Source file has {line_count} lines, exceeding modularity ceiling of {max_lines} lines.",
                        path=ctx.relpath(src),
                        remediation="Decompose this file into smaller cohesive modules with focused responsibilities.",
                    )
                )
    return findings


def register(registry: RuleRegistry) -> None:
    registry.register(
        RuleSpec(
            rule_id="MOD-001",
            domain="modularity",
            title="Component Manifest Schema Compliance",
            summary="Every component across core/modules/adapters/plugins/tools must have a valid schema-checked manifest.",
        ),
        check_mod_001,
    )
    registry.register(
        RuleSpec(
            rule_id="MOD-002",
            domain="modularity",
            title="Strict Layer Dependency Boundaries",
            summary="Manifest and source imports must obey the allowed acyclic layer matrix with zero cross-plugin coupling.",
        ),
        check_mod_002,
    )
    registry.register(
        RuleSpec(
            rule_id="MOD-003",
            domain="modularity",
            title="Acyclic Component Dependency Graph (DAG)",
            summary="Zero circular dependencies are permitted across manifests or source-level imports.",
        ),
        check_mod_003,
    )
    registry.register(
        RuleSpec(
            rule_id="MOD-004",
            domain="modularity",
            title="Manifest-to-Source Dependency Parity",
            summary="Every cross-component source import must be explicitly declared in the component manifest.",
        ),
        check_mod_004,
    )
    registry.register(
        RuleSpec(
            rule_id="MOD-005",
            domain="modularity",
            title="DSP, UI, and Format Adapter Separation",
            summary="Plugins must isolate dsp/ and ui/; DSP files must not include UI headers; adapters must stay DSP-free.",
        ),
        check_mod_005,
    )
    registry.register(
        RuleSpec(
            rule_id="MOD-006",
            domain="modularity",
            title="Source File Cohesion Ceiling",
            summary="Production source files must remain at or below the configured line-count ceiling.",
        ),
        check_mod_006,
    )
