"""Ruthless Diátaxis, MADR 4.0 ADR, link integrity, rule parity, and zero-placeholder checks (DOC-001..DOC-006)."""

from __future__ import annotations

import re
from pathlib import Path

from tools.xlp_gate.markdown_utils import (
    extract_heading_slugs,
    extract_markdown_links,
    extract_sections,
    parse_frontmatter,
    strip_fenced_code_blocks,
    word_count,
)
from tools.xlp_gate.models import Finding, GateContext, RuleSpec, Severity
from tools.xlp_gate.registry import RuleRegistry

ADR_FILENAME_RE = re.compile(r"^(ADR-\d{4})-[a-z0-9-]+\.md$")
RULE_HEADING_RE = re.compile(r"^###\s+([A-Z]{3}-\d{3})\b", re.MULTILINE)
VALID_ADR_STATUSES = {"proposed", "accepted", "deprecated", "superseded", "rejected"}


def check_doc_001(ctx: GateContext) -> list[Finding]:
    """Verify Diátaxis documentation structure and prohibit misfiled ADRs."""
    findings: list[Finding] = []
    doc_cfg = ctx.policy.get("documentation", {})
    docs_root = ctx.repo_root / "docs"
    if not docs_root.is_dir():
        return [
            Finding(
                rule_id="DOC-001",
                severity=Severity.ERROR,
                message="Repository is missing required 'docs/' directory.",
                path="docs",
                remediation="Create docs/ with Diátaxis quadrants, adr/, and research/.",
            )
        ]

    if not (docs_root / "README.md").is_file():
        findings.append(
            Finding(
                rule_id="DOC-001",
                severity=Severity.ERROR,
                message="Missing documentation index 'docs/README.md'.",
                path="docs/README.md",
                remediation="Create docs/README.md indexing all Diátaxis quadrants, ADRs, and research.",
            )
        )

    for quadrant in doc_cfg.get("diataxis_quadrants", ["tutorials", "how-to", "reference", "explanation"]):
        qdir = docs_root / quadrant
        if not qdir.is_dir():
            findings.append(
                Finding(
                    rule_id="DOC-001",
                    severity=Severity.ERROR,
                    message=f"Missing Diátaxis quadrant directory 'docs/{quadrant}/'.",
                    path=f"docs/{quadrant}",
                    remediation=f"Create 'docs/{quadrant}/' and populate with quadrant-appropriate docs.",
                )
            )
            continue
        md_files = list(qdir.glob("*.md"))
        if not md_files:
            findings.append(
                Finding(
                    rule_id="DOC-001",
                    severity=Severity.ERROR,
                    message=f"Diátaxis quadrant 'docs/{quadrant}/' contains no Markdown documentation.",
                    path=f"docs/{quadrant}",
                    remediation=f"Add at least one substantive document to 'docs/{quadrant}/'.",
                )
            )
        for md in md_files:
            if md.name.upper().startswith("ADR-"):
                findings.append(
                    Finding(
                        rule_id="DOC-001",
                        severity=Severity.ERROR,
                        message=f"ADR '{md.name}' is misfiled inside Diátaxis quadrant 'docs/{quadrant}/'.",
                        path=ctx.relpath(md),
                        remediation="Move ADRs strictly into 'docs/adr/'.",
                    )
                )

    return findings


def check_doc_002(ctx: GateContext) -> list[Finding]:
    """Validate MADR 4.0 ADRs and bind `enforced_by` IDs to live registered rules."""
    findings: list[Finding] = []
    doc_cfg = ctx.policy.get("documentation", {})
    adr_dir = ctx.repo_root / doc_cfg.get("adr_directory", "docs/adr")
    req_fm = doc_cfg.get("required_adr_frontmatter_fields", [])
    req_sections = doc_cfg.get("required_adr_sections", [])

    if not adr_dir.is_dir():
        return [
            Finding(
                rule_id="DOC-002",
                severity=Severity.ERROR,
                message=f"Missing ADR directory '{ctx.relpath(adr_dir)}'.",
                path=ctx.relpath(adr_dir),
                remediation="Create docs/adr/ containing MADR 4.0 decision records.",
            )
        ]

    adr_files = sorted(adr_dir.glob("ADR-*.md"))
    if not adr_files:
        return [
            Finding(
                rule_id="DOC-002",
                severity=Severity.ERROR,
                message="No ADR files (ADR-XXXX-*.md) found in docs/adr/.",
                path=ctx.relpath(adr_dir),
                remediation="Record core architectural decisions in docs/adr/ using MADR 4.0 format.",
            )
        ]

    seen_ids: dict[str, str] = {}
    for adr_path in adr_files:
        rel = ctx.relpath(adr_path)
        m = ADR_FILENAME_RE.match(adr_path.name)
        if not m:
            findings.append(
                Finding(
                    rule_id="DOC-002",
                    severity=Severity.ERROR,
                    message=f"ADR filename '{adr_path.name}' must match 'ADR-XXXX-<kebab-slug>.md'.",
                    path=rel,
                    remediation="Rename ADR file to match 'ADR-0001-short-slug.md'.",
                )
            )
            continue

        file_id = m.group(1)
        if file_id in seen_ids:
            findings.append(
                Finding(
                    rule_id="DOC-002",
                    severity=Severity.ERROR,
                    message=f"Duplicate ADR ID '{file_id}' collides with '{seen_ids[file_id]}'.",
                    path=rel,
                    remediation="Assign unique sequential ADR-XXXX identifiers.",
                )
            )
        seen_ids[file_id] = rel

        text = adr_path.read_text(encoding="utf-8", errors="replace")
        fm, body, err = parse_frontmatter(text)
        if err or fm is None:
            findings.append(
                Finding(
                    rule_id="DOC-002",
                    severity=Severity.ERROR,
                    message=f"Malformed or missing MADR frontmatter: {err or 'missing --- block'}",
                    path=rel,
                    remediation="Add valid MADR 4.0 YAML frontmatter.",
                )
            )
            continue

        for field in req_fm:
            if field not in fm or fm[field] in ("", None, []):
                findings.append(
                    Finding(
                        rule_id="DOC-002",
                        severity=Severity.ERROR,
                        message=f"ADR frontmatter missing required non-empty field '{field}'.",
                        path=rel,
                        remediation=f"Populate '{field}' in ADR YAML frontmatter.",
                    )
                )

        if fm.get("id") != file_id:
            findings.append(
                Finding(
                    rule_id="DOC-002",
                    severity=Severity.ERROR,
                    message=f"ADR frontmatter id '{fm.get('id')}' does not match filename id '{file_id}'.",
                    path=rel,
                    remediation=f"Set frontmatter id to '{file_id}'.",
                )
            )

        status = fm.get("status")
        if status not in VALID_ADR_STATUSES:
            findings.append(
                Finding(
                    rule_id="DOC-002",
                    severity=Severity.ERROR,
                    message=f"ADR status '{status}' not in allowed lifecycle states {sorted(VALID_ADR_STATUSES)}.",
                    path=rel,
                    remediation="Use a valid MADR lifecycle status.",
                )
            )

        if status == "accepted":
            enforced = fm.get("enforced_by", [])
            if isinstance(enforced, str):
                enforced = [enforced]
            if not isinstance(enforced, list) or len(enforced) == 0:
                findings.append(
                    Finding(
                        rule_id="DOC-002",
                        severity=Severity.ERROR,
                        message=f"Accepted ADR '{file_id}' must bind at least one live rule in 'enforced_by'.",
                        path=rel,
                        remediation="Add live xlp-gate rule IDs to 'enforced_by'.",
                    )
                )
            else:
                for rid in enforced:
                    if rid not in ctx.registered_rules:
                        findings.append(
                            Finding(
                                rule_id="DOC-002",
                                severity=Severity.ERROR,
                                message=(
                                    f"Accepted ADR '{file_id}' lists unknown rule '{rid}' in 'enforced_by'."
                                ),
                                path=rel,
                                remediation="Implement and register the rule in xlp-gate or fix the rule ID.",
                            )
                        )

        sections = extract_sections(body, level=2)
        for sec in req_sections:
            if sec not in sections:
                findings.append(
                    Finding(
                        rule_id="DOC-002",
                        severity=Severity.ERROR,
                        message=f"ADR '{file_id}' is missing mandatory MADR section '## {sec}'.",
                        path=rel,
                        remediation=f"Add substantive '## {sec}' section to '{rel}'.",
                    )
                )

    return findings


def check_doc_003(ctx: GateContext) -> list[Finding]:
    """Verify every component provides all required substantive documentation files."""
    findings: list[Finding] = []
    layers_cfg = ctx.policy.get("layers", {})
    min_words = int(ctx.policy.get("documentation", {}).get("min_doc_words", 40))

    for comp in ctx.components:
        req_docs = layers_cfg.get(comp.layer, {}).get("required_docs", [])
        for rel_doc in req_docs:
            doc_path = comp.directory / rel_doc
            rel = ctx.relpath(doc_path)
            if not doc_path.is_file():
                findings.append(
                    Finding(
                        rule_id="DOC-003",
                        severity=Severity.ERROR,
                        message=f"Component '{comp.name}' missing required documentation file '{rel_doc}'.",
                        path=rel,
                        remediation=f"Author substantive documentation at '{rel}'.",
                    )
                )
                continue
            wc = word_count(doc_path.read_text(encoding="utf-8", errors="replace"))
            if wc < min_words:
                findings.append(
                    Finding(
                        rule_id="DOC-003",
                        severity=Severity.ERROR,
                        message=f"Component doc '{rel}' has only {wc} words (minimum {min_words}).",
                        path=rel,
                        remediation=f"Expand '{rel}' with complete technical details and examples.",
                    )
                )

    return findings


def check_doc_004(ctx: GateContext) -> list[Finding]:
    """Enforce exact 1:1 parity between registered rules and docs/reference/enforcement-rules.md."""
    findings: list[Finding] = []
    ref_rel = ctx.policy.get("documentation", {}).get(
        "rules_reference_doc", "docs/reference/enforcement-rules.md"
    )
    ref_path = ctx.repo_root / ref_rel
    if not ref_path.is_file():
        return [
            Finding(
                rule_id="DOC-004",
                severity=Severity.ERROR,
                message=f"Missing enforcement rules reference document '{ref_rel}'.",
                path=ref_rel,
                remediation="Create docs/reference/enforcement-rules.md documenting every rule ID.",
            )
        ]

    text = ref_path.read_text(encoding="utf-8", errors="replace")
    documented_ids = set(RULE_HEADING_RE.findall(text))
    registered_ids = set(ctx.registered_rules.keys())

    for rid in sorted(registered_ids - documented_ids):
        findings.append(
            Finding(
                rule_id="DOC-004",
                severity=Severity.ERROR,
                message=f"Registered rule '{rid}' is undocumented in '{ref_rel}'.",
                path=ref_rel,
                remediation=f"Add a '### {rid}' reference section in '{ref_rel}'.",
            )
        )

    for rid in sorted(documented_ids - registered_ids):
        findings.append(
            Finding(
                rule_id="DOC-004",
                severity=Severity.ERROR,
                message=f"Orphaned/unregistered rule '{rid}' documented in '{ref_rel}'.",
                path=ref_rel,
                remediation=f"Remove obsolete documentation for '{rid}' or restore its rule implementation.",
            )
        )

    return findings


def _iter_repo_markdown_files(ctx: GateContext) -> list[Path]:
    md_files: list[Path] = []
    for root_file in ("README.md", "AGENTS.md", "CONTRIBUTING.md"):
        p = ctx.repo_root / root_file
        if p.is_file():
            md_files.append(p)
    for folder in ("docs", "core", "modules", "adapters", "plugins", "tools", "mods"):
        base = ctx.repo_root / folder
        if not base.is_dir():
            continue
        for p in sorted(base.rglob("*.md")):
            rel_parts = p.relative_to(ctx.repo_root).parts
            if any(part in ("tests", "fixtures", "build", ".git", "node_modules") for part in rel_parts):
                continue
            md_files.append(p)
    return md_files


def check_doc_005(ctx: GateContext) -> list[Finding]:
    """Verify every internal relative Markdown link and heading anchor resolves cleanly."""
    findings: list[Finding] = []
    slug_cache: dict[Path, set[str]] = {}

    def get_slugs(target: Path) -> set[str]:
        resolved = target.resolve()
        if resolved not in slug_cache:
            slug_cache[resolved] = extract_heading_slugs(
                resolved.read_text(encoding="utf-8", errors="replace")
            )
        return slug_cache[resolved]

    for md_path in _iter_repo_markdown_files(ctx):
        rel = ctx.relpath(md_path)
        text = md_path.read_text(encoding="utf-8", errors="replace")
        for lineno, _, raw_target in extract_markdown_links(text):
            target = raw_target.split()[0].strip("<>")
            if not target or target.startswith(("http://", "https://", "mailto:", "tel:")):
                continue

            if "#" in target:
                file_part, anchor = target.split("#", 1)
            else:
                file_part, anchor = target, ""

            if file_part == "":
                resolved_target = md_path
            else:
                resolved_target = (md_path.parent / file_part).resolve()

            if not resolved_target.exists():
                findings.append(
                    Finding(
                        rule_id="DOC-005",
                        severity=Severity.ERROR,
                        message=f"Broken internal link '{raw_target}' (target does not exist).",
                        path=rel,
                        line=lineno,
                        remediation="Fix the relative file path or create the missing target document.",
                    )
                )
                continue

            if anchor and resolved_target.is_file() and resolved_target.suffix.lower() == ".md":
                slugs = get_slugs(resolved_target)
                if anchor.lower() not in slugs:
                    findings.append(
                        Finding(
                            rule_id="DOC-005",
                            severity=Severity.ERROR,
                            message=f"Broken heading anchor '#{anchor}' in link '{raw_target}'.",
                            path=rel,
                            line=lineno,
                            remediation=f"Update '#{anchor}' to match an existing heading in '{ctx.relpath(resolved_target)}'.",
                        )
                    )

    return findings


def check_doc_006(ctx: GateContext) -> list[Finding]:
    """Ban unfinished placeholder markers across docs, ADRs, research dossiers, and manifests."""
    findings: list[Finding] = []
    raw_patterns = ctx.policy.get("documentation", {}).get("forbidden_placeholders", [])
    compiled = [re.compile(pat) for pat in raw_patterns]

    scan_paths: list[Path] = _iter_repo_markdown_files(ctx)
    for comp in ctx.components:
        if comp.manifest_path.is_file():
            scan_paths.append(comp.manifest_path)
    for gov_json in ("governance/brand.json", "governance/waivers.json", "governance/traceability.json"):
        p = ctx.repo_root / gov_json
        if p.is_file():
            scan_paths.append(p)
    templates_dir = ctx.repo_root / "governance" / "templates"
    if templates_dir.is_dir():
        scan_paths.extend(sorted(templates_dir.glob("*.md")))

    for path in scan_paths:
        rel = ctx.relpath(path)
        text = path.read_text(encoding="utf-8", errors="replace")
        cleaned = strip_fenced_code_blocks(text) if path.suffix.lower() == ".md" else text
        for lineno, line in enumerate(cleaned.splitlines(), start=1):
            scan_line = re.sub(r"`[^`]*`", "", line) if path.suffix.lower() == ".md" else line
            for regex in compiled:
                m = regex.search(scan_line)
                if m:
                    findings.append(
                        Finding(
                            rule_id="DOC-006",
                            severity=Severity.ERROR,
                            message=f"Forbidden incomplete placeholder '{m.group(0)}' detected.",
                            path=rel,
                            line=lineno,
                            remediation="Replace placeholder text with complete, verified documentation or specification.",
                        )
                    )
                    break

    return findings


def register(registry: RuleRegistry) -> None:
    registry.register(
        RuleSpec(
            rule_id="DOC-001",
            domain="documentation",
            title="Diátaxis Documentation Layout Integrity",
            summary="docs/ must maintain README.md and all four Diátaxis quadrants with zero misfiled ADRs.",
        ),
        check_doc_001,
    )
    registry.register(
        RuleSpec(
            rule_id="DOC-002",
            domain="documentation",
            title="MADR 4.0 ADR Validity & Live Enforced-By Binding",
            summary="Every ADR must satisfy MADR 4.0 structure and accepted ADRs must bind to live xlp-gate rules.",
        ),
        check_doc_002,
    )
    registry.register(
        RuleSpec(
            rule_id="DOC-003",
            domain="documentation",
            title="Component Documentation Completeness",
            summary="Every component must supply all layer-mandated documentation files with substantive prose.",
        ),
        check_doc_003,
    )
    registry.register(
        RuleSpec(
            rule_id="DOC-004",
            domain="documentation",
            title="1:1 Rule-to-Reference Documentation Parity",
            summary="Every registered xlp-gate rule must be documented in docs/reference/enforcement-rules.md with zero orphans.",
        ),
        check_doc_004,
    )
    registry.register(
        RuleSpec(
            rule_id="DOC-005",
            domain="documentation",
            title="Internal Markdown Link & Heading Anchor Integrity",
            summary="Every relative Markdown link and heading anchor across docs and root guides must resolve cleanly.",
        ),
        check_doc_005,
    )
    registry.register(
        RuleSpec(
            rule_id="DOC-006",
            domain="documentation",
            title="Zero Placeholder & Unfinished Debt Policy",
            summary="Docs, ADRs, research dossiers, templates, and manifests must contain zero TBD/TODO/FIXME/PLACEHOLDER debt.",
        ),
        check_doc_006,
    )
