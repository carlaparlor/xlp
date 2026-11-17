"""Command-line interface for the XLP strict architectural enforcement gate."""

from __future__ import annotations

import argparse
import os
import stat
import sys
from pathlib import Path

from tools.xlp_gate import __version__
from tools.xlp_gate.registry import build_default_registry
from tools.xlp_gate.runner import (
    format_json_report,
    format_markdown_report,
    format_text_report,
    run_gate,
)
from tools.xlp_gate.scaffold import scaffold_doc_artifact, scaffold_module, scaffold_plugin


def _resolve_repo_root(raw: str | None) -> Path:
    if raw:
        return Path(raw).resolve()
    return Path.cwd().resolve()


def _cmd_check(args: argparse.Namespace) -> int:
    repo_root = _resolve_repo_root(args.root)
    only_rules = set(args.rule) if args.rule else None
    only_domains = set(args.domain) if args.domain else None

    report = run_gate(
        repo_root=repo_root,
        strict=args.strict,
        run_tests=args.run_tests,
        only_rules=only_rules,
        only_domains=only_domains,
    )

    if args.format == "json":
        output = format_json_report(report)
    elif args.format == "markdown":
        output = format_markdown_report(report)
    else:
        output = format_text_report(report)

    print(output)

    if args.json_out:
        out_path = Path(args.json_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(format_json_report(report), encoding="utf-8")

    return 0 if report.passed else 1


def _cmd_list_rules(args: argparse.Namespace) -> int:
    registry = build_default_registry()
    for reg in registry.all_rules():
        spec = reg.spec
        if args.domain and spec.domain != args.domain:
            continue
        print(f"{spec.rule_id}  [{spec.domain:13s}]  {spec.title}")
    return 0


def _cmd_verify_hooks(args: argparse.Namespace) -> int:
    repo_root = _resolve_repo_root(args.root)
    git_hooks = repo_root / ".git" / "hooks"
    required = ["pre-commit", "commit-msg", "pre-push"]
    ok = True
    for name in required:
        hook_path = git_hooks / name
        if not hook_path.is_file():
            print(f"[MISSING] .git/hooks/{name}")
            ok = False
            continue
        mode = os.stat(hook_path).st_mode
        executable = bool(mode & stat.S_IXUSR)
        content = hook_path.read_text(encoding="utf-8", errors="replace")
        has_marker = "XLP_MANAGED_HOOK" in content
        if not executable or not has_marker:
            print(f"[INVALID] .git/hooks/{name} (executable={executable}, xlp_managed={has_marker})")
            ok = False
        else:
            print(f"[OK] .git/hooks/{name}")
    if not ok:
        print("Run './scripts/install-hooks.sh' to install XLP Git enforcement hooks.")
        return 1
    return 0


def _cmd_scaffold(args: argparse.Namespace) -> int:
    repo_root = _resolve_repo_root(args.root)
    if args.kind == "plugin":
        created = scaffold_plugin(repo_root, args.name, category=args.category)
    elif args.kind == "module":
        created = scaffold_module(repo_root, args.layer, args.name, kind=args.module_kind)
    elif args.kind in ("adr", "research"):
        title = args.title or args.name.replace("-", " ").title()
        created = scaffold_doc_artifact(repo_root, args.kind, args.name, title)
    else:
        raise ValueError(f"Unknown scaffold kind: {args.kind}")
    print(f"Scaffolded compliant {args.kind}: {created}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="xlp-gate",
        description="XLP strict architectural, research, testing, and documentation enforcement gate.",
    )
    parser.add_argument("--version", action="version", version=f"xlp-gate {__version__}")
    parser.add_argument("--root", default=None, help="Repository root path (defaults to cwd).")

    sub = parser.add_subparsers(dest="command", required=True)

    p_check = sub.add_parser("check", help="Evaluate enforcement rules against the repository.")
    p_check.add_argument("--strict", action="store_true", default=True, help="Fail on errors and warnings (default).")
    p_check.add_argument("--no-strict", dest="strict", action="store_false", help="Fail on errors only.")
    p_check.add_argument("--run-tests", action="store_true", help="Execute every component's declared test suite (TST-003).")
    p_check.add_argument("--rule", action="append", help="Restrict run to specific rule ID(s).")
    p_check.add_argument("--domain", action="append", help="Restrict run to specific domain(s).")
    p_check.add_argument("--format", choices=["text", "json", "markdown"], default="text", help="Output format.")
    p_check.add_argument("--json-out", default=None, help="Write JSON report to path.")
    p_check.set_defaults(func=_cmd_check)

    p_list = sub.add_parser("list-rules", help="List all registered XLP enforcement rules.")
    p_list.add_argument("--domain", default=None, help="Filter by domain.")
    p_list.set_defaults(func=_cmd_list_rules)

    p_hooks = sub.add_parser("verify-hooks", help="Verify local .git/hooks installation.")
    p_hooks.set_defaults(func=_cmd_verify_hooks)

    p_scaf = sub.add_parser("scaffold", help="Generate compliant XLP skeletons.")
    p_scaf.add_argument("kind", choices=["plugin", "module", "adr", "research"])
    p_scaf.add_argument("name", help="Snake_case slug for plugin/module or kebab-case slug for adr/research.")
    p_scaf.add_argument("--layer", choices=["core", "modules", "adapters"], default="modules")
    p_scaf.add_argument("--category", default="effect", help="Plugin category (effect, instrument, utility, etc.).")
    p_scaf.add_argument("--module-kind", default="dsp", help="Module kind (dsp, ui, state, modding, adapter, utility).")
    p_scaf.add_argument("--title", default=None, help="Human title for ADR or Research Dossier.")
    p_scaf.set_defaults(func=_cmd_scaffold)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
