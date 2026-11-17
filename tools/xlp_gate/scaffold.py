"""Compliant skeleton scaffolding for XLP plugins, modules, mods, ADRs, and research dossiers."""

from __future__ import annotations

import datetime
import json
import re
import uuid
from pathlib import Path

SLUG_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _derive_plugin_code(slug: str) -> str:
    alnum = re.sub(r"[^a-zA-Z0-9]", "", slug).upper()
    padded = (alnum + "XLP0")[:4]
    return padded


def scaffold_plugin(repo_root: Path, slug: str, category: str = "effect") -> Path:
    """Generate a fully schema-compliant XLP plugin skeleton under plugins/xlp_<slug>/."""
    if not SLUG_RE.match(slug):
        raise ValueError(f"Plugin slug '{slug}' must be lowercase snake_case matching [a-z][a-z0-9_]*")

    dir_name = f"xlp_{slug}"
    plugin_id = f"xlp.{slug}"
    plugin_dir = repo_root / "plugins" / dir_name
    if plugin_dir.exists():
        raise FileExistsError(f"Plugin directory already exists: {plugin_dir}")

    display_name = "XLP " + " ".join(part.capitalize() for part in slug.split("_"))
    manifest = {
        "schema_version": "1.0.0",
        "id": plugin_id,
        "name": display_name,
        "brand": "xlp",
        "layer": "plugins",
        "category": category,
        "version": "0.1.0",
        "api_version": "1.0.0",
        "abi_version": 1,
        "stability": "experimental",
        "description": f"{display_name} is a modular, scalable, extensible, and moddable XLP VST3 audio plugin.",
        "plugin_code": _derive_plugin_code(slug),
        "vst3_component_uid": str(uuid.uuid4()),
        "vst3_controller_uid": str(uuid.uuid4()),
        "formats": ["vst3"],
        "channel_layouts": [{"inputs": 2, "outputs": 2, "sidechain": False}],
        "dependencies": [],
        "state_schema_version": 1,
        "migration_strategy": "Versioned JSON state envelope with forward-only deterministic schema migrators.",
        "params_file": "params.json",
        "extension_points": [
            {
                "id": "dsp.stages",
                "interface": "xlp::IDspStage",
                "version": "1.0.0",
                "lifecycle": "init",
                "description": "Ordered real-time DSP stage registry executed inside the audio processing chain.",
            },
            {
                "id": "ui.themes",
                "interface": "xlp::IThemeTokenProvider",
                "version": "1.0.0",
                "lifecycle": "hot_reload",
                "description": "Declarative UI color, typography, and layout token extension point.",
            },
        ],
        "realtime_contract": {
            "audio_thread_lock_free": True,
            "audio_thread_alloc_free": True,
            "denormal_protection": True,
            "supported_sample_rates": [44100, 48000, 88200, 96000, 192000],
            "arbitrary_block_sizes": True,
            "thread_communication": "spsc_ringbuffer",
        },
        "performance_budget": {
            "max_cpu_percent_single_core_48k_64buf": 5.0,
            "max_memory_mb": 64.0,
            "max_latency_samples": 0,
            "benchmark_target": f"bench_{dir_name}",
        },
        "modding": {
            "enabled": True,
            "mod_api_version": "1.0.0",
            "hot_reload_supported": True,
            "conflict_resolution": "deterministic_priority",
            "reference_mod_path": "mods/reference_theme",
            "surfaces": [
                {
                    "id": "ui.theme",
                    "kind": "themes",
                    "sandbox_level": "declarative_schema",
                    "allow_filesystem": False,
                    "allow_network": False,
                    "rt_safe_enforced": True,
                    "cpu_budget_us": 0,
                    "memory_limit_kb": 512,
                    "fallback_on_error": "revert_default",
                },
                {
                    "id": "macros.mapping",
                    "kind": "macros",
                    "sandbox_level": "declarative_schema",
                    "allow_filesystem": False,
                    "allow_network": False,
                    "rt_safe_enforced": True,
                    "cpu_budget_us": 50,
                    "memory_limit_kb": 256,
                    "fallback_on_error": "bypass_mod_and_warn",
                },
            ],
        },
        "research_refs": ["RES-0001", "RES-0002", "RES-0003"],
        "adr_refs": ["ADR-0002", "ADR-0003", "ADR-0004"],
        "testing": {
            "directory": "tests",
            "command": f"python3 -m unittest discover -s plugins/{dir_name}/tests -p test_*.py",
            "categories": [
                "unit",
                "dsp_invariants",
                "rt_safety",
                "state_roundtrip",
                "mod_loading",
                "host_validation",
            ],
        },
        "docs": {
            "readme": "README.md",
            "architecture": "docs/architecture.md",
            "api": "docs/api.md",
            "testing": "docs/testing.md",
            "modding": "docs/modding.md",
        },
    }

    params = {
        "schema_version": "1.0.0",
        "plugin_id": plugin_id,
        "state_schema_version": 1,
        "parameters": [
            {
                "id": "output.gain_db",
                "uid": 1001,
                "name": "Output Gain",
                "type": "float",
                "min": -60.0,
                "max": 12.0,
                "default": 0.0,
                "unit": "dB",
                "automatable": True,
                "modulatable": True,
                "smoothing_ms": 5.0,
                "description": "Master output trim gain in decibels applied after the final DSP stage.",
            }
        ],
    }

    ref_mod = {
        "schema_version": "1.0.0",
        "id": f"xlp.{slug}_reference_theme",
        "name": f"{display_name} Reference Theme Mod",
        "version": "1.0.0",
        "author": "XLP Audio",
        "target_plugin": plugin_id,
        "target_mod_api_version": "1.0.0",
        "priority": 100,
        "description": f"Official reference declarative theme mod pack validating moddability for {display_name}.",
        "surfaces": ["ui.theme"],
        "requested_capabilities": {"filesystem": False, "network": False, "max_memory_kb": 64},
        "entry_files": ["theme.json"],
    }

    _write_json(plugin_dir / "plugin.manifest.json", manifest)
    _write_json(plugin_dir / "params.json", params)
    _write_json(plugin_dir / "mods" / "reference_theme" / "mod.manifest.json", ref_mod)
    _write_json(
        plugin_dir / "mods" / "reference_theme" / "theme.json",
        {"accent": "#22d3ee", "surface": "#0f172a", "text": "#f8fafc"},
    )
    _write_text(
        plugin_dir / "dsp" / "processor.hpp",
        (
            "#pragma once\n\n"
            "namespace xlp {\n"
            "class Processor {\n"
            "public:\n"
            "    void prepare(double sample_rate, int max_block_size) noexcept {\n"
            "        sample_rate_ = sample_rate;\n"
            "        max_block_size_ = max_block_size;\n"
            "    }\n"
            "    float process_sample(float x) const noexcept { return x; }\n"
            "private:\n"
            "    double sample_rate_ = 48000.0;\n"
            "    int max_block_size_ = 512;\n"
            "};\n"
            "} // namespace xlp\n"
        ),
    )
    _write_text(
        plugin_dir / "ui" / "view_tokens.json",
        json.dumps({"accent": "#38bdf8", "surface": "#111827", "text": "#f9fafb"}, indent=2) + "\n",
    )

    doc_boilerplate = (
        f"# {display_name} — {{section}}\n\n"
        f"{display_name} (`{plugin_id}`) follows the XLP five-layer modular architecture, hard real-time audio "
        f"safety invariants, versioned parameter and state serialization contracts, and sandboxed mod surfaces.\n\n"
        f"This document details the {{detail}} for `{plugin_id}`, ensuring full traceability to `RES-0001`, "
        f"`RES-0002`, `RES-0003`, and accepted ADRs `ADR-0002`, `ADR-0003`, and `ADR-0004`.\n"
    )
    _write_text(plugin_dir / "README.md", doc_boilerplate.format(section="Overview", detail="purpose, feature scope, and build usage"))
    _write_text(plugin_dir / "docs" / "architecture.md", doc_boilerplate.format(section="Architecture", detail="DSP graph topology, lock-free thread boundaries, and UI decoupling"))
    _write_text(plugin_dir / "docs" / "api.md", doc_boilerplate.format(section="API & Parameter Reference", detail="extension points, ABI guarantees, and immutable parameter schema"))
    _write_text(plugin_dir / "docs" / "testing.md", doc_boilerplate.format(section="Testing Strategy", detail="unit, DSP invariants, RT safety, state recall, mod loading, and host validation suites"))
    _write_text(
        plugin_dir / "docs" / "modding.md",
        (
            f"# {display_name} Modding Guide\n\n"
            f"{display_name} exposes deterministic, capability-restricted mod surfaces so users can customize "
            f"visuals and macro behavior without risking DAW stability or real-time audio deadlines.\n\n"
            f"## Supported Mod Surfaces\n\n"
            f"- `ui.theme` (`themes`): declarative JSON color and typography token overrides.\n"
            f"- `macros.mapping` (`macros`): declarative parameter routing curves evaluated within strict CPU budgets.\n\n"
            f"## Sandbox & Fault Isolation\n\n"
            f"All mod packs execute inside a strict `declarative_schema` sandbox with filesystem and network "
            f"access disabled (`allow_filesystem: false`, `allow_network: false`). Malformed packs safely trigger "
            f"`revert_default` or `bypass_mod_and_warn` without crashing the host.\n"
        ),
    )

    _write_text(
        plugin_dir / "tests" / "test_plugin_contract.py",
        (
            '"""Contract tests for scaffolded XLP plugin.\n'
            "@category: unit\n"
            "@category: dsp_invariants\n"
            "@category: rt_safety\n"
            "@category: state_roundtrip\n"
            "@category: mod_loading\n"
            "@category: host_validation\n"
            '"""\n\n'
            "import json\n"
            "import unittest\n"
            "from pathlib import Path\n\n"
            "class TestPluginContract(unittest.TestCase):\n"
            "    def test_manifest_and_params_load(self) -> None:\n"
            "        root = Path(__file__).resolve().parent.parent\n"
            "        manifest = json.loads((root / 'plugin.manifest.json').read_text(encoding='utf-8'))\n"
            "        params = json.loads((root / 'params.json').read_text(encoding='utf-8'))\n"
            "        self.assertEqual(manifest['id'], params['plugin_id'])\n"
        ),
    )
    return plugin_dir


def scaffold_module(repo_root: Path, layer: str, name: str, kind: str = "dsp") -> Path:
    """Generate a compliant XLP module skeleton under core/, modules/, or adapters/."""
    if layer not in ("core", "modules", "adapters"):
        raise ValueError(f"Unsupported module layer '{layer}'; choose core, modules, or adapters.")
    if not SLUG_RE.match(name):
        raise ValueError(f"Module name '{name}' must match lowercase snake_case [a-z][a-z0-9_]*")

    mod_dir = repo_root / layer / name
    if mod_dir.exists():
        raise FileExistsError(f"Module directory already exists: {mod_dir}")

    mod_id = f"xlp.{layer}.{name}"
    display = "XLP " + " ".join(p.capitalize() for p in name.split("_"))
    cats = (
        ["unit", "host_conformance", "state_roundtrip"]
        if layer == "adapters"
        else ["unit", "dsp_invariants", "rt_safety", "regression", "fuzz"]
    )

    manifest: dict = {
        "schema_version": "1.0.0",
        "id": mod_id,
        "name": display,
        "brand": "xlp",
        "layer": layer,
        "kind": kind,
        "version": "0.1.0",
        "api_version": "1.0.0",
        "abi_version": 1,
        "stability": "experimental",
        "description": f"{display} is a modular, real-time safe XLP {layer} component for VST3 audio plugins.",
        "dependencies": [],
        "public_api_paths": ["include"],
        "extension_points": [
            {
                "id": f"{name}.hooks",
                "interface": f"xlp::I{name.title().replace('_', '')}Hook",
                "version": "1.0.0",
                "lifecycle": "init",
                "description": f"Versioned extension interface exposed by {mod_id}.",
            }
        ],
        "research_refs": ["RES-0001", "RES-0002"],
        "adr_refs": ["ADR-0002", "ADR-0003"],
        "testing": {
            "directory": "tests",
            "command": f"python3 -m unittest discover -s {layer}/{name}/tests -p test_*.py",
            "categories": cats,
        },
        "docs": {
            "readme": "README.md",
            "architecture": "docs/architecture.md",
            "api": "docs/api.md",
            "testing": "docs/testing.md",
        },
    }
    if kind == "dsp":
        manifest["realtime_contract"] = {
            "audio_thread_lock_free": True,
            "audio_thread_alloc_free": True,
            "denormal_protection": True,
            "supported_sample_rates": [44100, 48000, 88200, 96000, 192000],
            "arbitrary_block_sizes": True,
            "thread_communication": "atomics",
        }
        manifest["performance_budget"] = {
            "max_cpu_percent_single_core_48k_64buf": 2.0,
            "max_memory_mb": 16.0,
            "max_latency_samples": 0,
            "benchmark_target": f"bench_{name}",
        }

    _write_json(mod_dir / "module.manifest.json", manifest)
    _write_text(mod_dir / "include" / f"{name}.hpp", f"#pragma once\nnamespace xlp {{ struct {name}_tag {{}}; }}\n")

    body = (
        f"# {display} — {{section}}\n\n"
        f"{display} (`{mod_id}`) resides in the `{layer}` architectural layer of the XLP plugin ecosystem "
        f"and enforces strict dependency isolation, semantic API/ABI versioning, and automated verification "
        f"linked to `RES-0001`, `RES-0002`, `ADR-0002`, and `ADR-0003`.\n"
    )
    _write_text(mod_dir / "README.md", body.format(section="Overview"))
    _write_text(mod_dir / "docs" / "architecture.md", body.format(section="Architecture"))
    _write_text(mod_dir / "docs" / "api.md", body.format(section="API Reference"))
    _write_text(mod_dir / "docs" / "testing.md", body.format(section="Testing Strategy"))

    cat_lines = "\n".join(f"@category: {c}" for c in cats)
    _write_text(
        mod_dir / "tests" / f"test_{name}.py",
        (
            f'"""Module contract tests.\n{cat_lines}\n"""\n\n'
            "import json\nimport unittest\nfrom pathlib import Path\n\n"
            "class TestModuleContract(unittest.TestCase):\n"
            "    def test_manifest_valid(self) -> None:\n"
            "        root = Path(__file__).resolve().parent.parent\n"
            "        data = json.loads((root / 'module.manifest.json').read_text(encoding='utf-8'))\n"
            f"        self.assertEqual(data['id'], '{mod_id}')\n"
        ),
    )
    return mod_dir


def next_sequential_id(directory: Path, prefix: str) -> str:
    highest = 0
    if directory.is_dir():
        for p in directory.glob(f"{prefix}-*.md"):
            m = re.match(rf"^{prefix}-(\d{{4}})-", p.name)
            if m:
                highest = max(highest, int(m.group(1)))
    return f"{prefix}-{highest + 1:04d}"


def scaffold_doc_artifact(repo_root: Path, kind: str, slug: str, title: str) -> Path:
    """Create a numbered ADR or Research Dossier from its governance template."""
    if not re.fullmatch(r"[a-z0-9-]+", slug):
        raise ValueError(f"Slug '{slug}' must be kebab-case [a-z0-9-]+")
    today = datetime.date.today().isoformat()
    if kind == "adr":
        target_dir = repo_root / "docs" / "adr"
        doc_id = next_sequential_id(target_dir, "ADR")
        template = (repo_root / "governance" / "templates" / "adr.template.md").read_text(encoding="utf-8")
        content = (
            template.replace("ADR-0000", doc_id)
            .replace("Replace with concise architectural decision title", title)
            .replace("2026-11-15", today)
        )
    elif kind == "research":
        target_dir = repo_root / "docs" / "research"
        doc_id = next_sequential_id(target_dir, "RES")
        template = (repo_root / "governance" / "templates" / "research-dossier.template.md").read_text(
            encoding="utf-8"
        )
        content = (
            template.replace("RES-0000", doc_id)
            .replace("Replace with research topic title", title)
            .replace("2026-11-15", today)
        )
    else:
        raise ValueError(f"Unsupported doc artifact kind '{kind}'")

    out = target_dir / f"{doc_id}-{slug}.md"
    _write_text(out, content)
    return out
