"""Isolated temporary workspace builders for positive and adversarial xlp-gate tests."""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

from tools.xlp_gate.runner import run_gate
from tools.xlp_gate.scaffold import scaffold_module, scaffold_plugin

REAL_REPO_ROOT = Path(__file__).resolve().parents[3]


def copy_governance_skeleton(dest: Path) -> Path:
    """Create an isolated temporary copy of XLP governance, docs, hooks, CI, and gate structure."""
    for rel_file in ("README.md", "AGENTS.md", "CONTRIBUTING.md", "xlp-gate"):
        src = REAL_REPO_ROOT / rel_file
        if src.is_file():
            dst = dest / rel_file
            shutil.copy2(src, dst)

    for rel_dir in (
        "governance",
        "docs",
        ".githooks",
        "scripts",
        ".github",
        "tools/xlp_gate",
    ):
        src_dir = REAL_REPO_ROOT / rel_dir
        if src_dir.is_dir():
            shutil.copytree(
                src_dir,
                dest / rel_dir,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )
    if (REAL_REPO_ROOT / "tools" / "__init__.py").is_file():
        shutil.copy2(REAL_REPO_ROOT / "tools" / "__init__.py", dest / "tools" / "__init__.py")
    return dest


def create_compliant_workspace(
    *,
    with_plugin: bool = False,
    with_module: bool = False,
    plugin_slug: str = "filter_one",
    module_name: str = "dsp_core",
) -> tuple[tempfile.TemporaryDirectory, Path]:
    """Return `(tempdir_handle, repo_root)` containing a compliant XLP workspace."""
    tmp = tempfile.TemporaryDirectory(prefix="xlp_gate_test_")
    root = Path(tmp.name)
    copy_governance_skeleton(root)
    if with_module:
        scaffold_module(root, "core", module_name, kind="dsp")
    if with_plugin:
        scaffold_plugin(root, plugin_slug, category="effect")
    return tmp, root


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def rule_ids_in(report) -> set[str]:
    return {f.rule_id for f in report.findings}


def check_rule(repo_root: Path, rule_id: str, **kwargs):
    return run_gate(repo_root, only_rules={rule_id}, **kwargs)
