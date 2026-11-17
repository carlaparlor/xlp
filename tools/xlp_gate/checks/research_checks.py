"""Ruthless research dossier structure, citation, depth, and coverage checks (RES-001..RES-004)."""

from __future__ import annotations

import re
from pathlib import Path

from tools.xlp_gate.markdown_utils import (
    extract_sections,
    parse_frontmatter,
    strip_fenced_code_blocks,
    word_count,
)
from tools.xlp_gate.models import Finding, GateContext, RuleSpec, Severity
from tools.xlp_gate.registry import RuleRegistry

RES_FILENAME_RE = re.compile(r"^(RES-\d{4})-[a-z0-9-]+\.md$")
REF_LINE_RE = re.compile(r"^\s*(\d+)\.\s+(.+)$")
SOURCE_INDICATOR_RE = re.compile(r"(https?://\S+|\bdoi:\S+|\bRFC\s*\d+|\bISBN[\s:-]*[\dX-]+|\bISO[\s/-]*\d+)", re.I)
INLINE_CITE_RE = re.compile(r"\[(\d+)\](?!\()")


def _discover_research_files(ctx: GateContext) -> list[Path]:
    res_dir = ctx.repo_root / ctx.policy.get("research", {}).get("directory", "docs/research")
    files: list[Path] = []
    if res_dir.is_dir():
        for path in sorted(res_dir.glob("RES-*.md")):
            if path.is_file():
                files.append(path)
    return files


def check_res_001(ctx: GateContext) -> list[Finding]:
    """Validate research dossier filenames, YAML frontmatter, and mandatory sections."""
    findings: list[Finding] = []
    res_cfg = ctx.policy.get("research", {})
    req_fm = res_cfg.get("required_frontmatter_fields", [])
    req_sections = res_cfg.get("required_sections", [])
    files = _discover_research_files(ctx)

    if not files:
        return [
            Finding(
                rule_id="RES-001",
                severity=Severity.ERROR,
                message="No research dossiers (RES-XXXX-*.md) found in docs/research/.",
                path=res_cfg.get("directory", "docs/research"),
                remediation="Author at least one grounded research dossier before proceeding.",
            )
        ]

    seen_ids: dict[str, str] = {}
    for path in files:
        rel = ctx.relpath(path)
        m = RES_FILENAME_RE.match(path.name)
        if not m:
            findings.append(
                Finding(
                    rule_id="RES-001",
                    severity=Severity.ERROR,
                    message=f"Research dossier filename '{path.name}' must match 'RES-XXXX-<kebab-slug>.md'.",
                    path=rel,
                    remediation="Rename dossier to follow 'RES-0001-topic-slug.md'.",
                )
            )
            continue

        file_id = m.group(1)
        if file_id in seen_ids:
            findings.append(
                Finding(
                    rule_id="RES-001",
                    severity=Severity.ERROR,
                    message=f"Duplicate research dossier ID '{file_id}' collides with '{seen_ids[file_id]}'.",
                    path=rel,
                    remediation="Assign sequential unique RES-XXXX identifiers.",
                )
            )
        seen_ids[file_id] = rel

        text = path.read_text(encoding="utf-8", errors="replace")
        fm, body, fm_err = parse_frontmatter(text)
        if fm_err or fm is None:
            findings.append(
                Finding(
                    rule_id="RES-001",
                    severity=Severity.ERROR,
                    message=f"Missing or malformed YAML frontmatter: {fm_err or 'missing leading ---'}",
                    path=rel,
                    remediation="Add valid YAML frontmatter per governance/templates/research-dossier.template.md.",
                )
            )
            continue

        for field in req_fm:
            if field not in fm or fm[field] in ("", None, []):
                findings.append(
                    Finding(
                        rule_id="RES-001",
                        severity=Severity.ERROR,
                        message=f"Research dossier frontmatter missing required non-empty field '{field}'.",
                        path=rel,
                        remediation=f"Populate '{field}' in frontmatter.",
                    )
                )

        if fm.get("id") != file_id:
            findings.append(
                Finding(
                    rule_id="RES-001",
                    severity=Severity.ERROR,
                    message=f"Frontmatter id '{fm.get('id')}' does not match filename id '{file_id}'.",
                    path=rel,
                    remediation=f"Set frontmatter id to '{file_id}'.",
                )
            )

        sections = extract_sections(body, level=2)
        for sec in req_sections:
            if sec not in sections:
                findings.append(
                    Finding(
                        rule_id="RES-001",
                        severity=Severity.ERROR,
                        message=f"Research dossier missing mandatory section '## {sec}'.",
                        path=rel,
                        remediation=f"Add substantive '## {sec}' section to '{rel}'.",
                    )
                )

    return findings


def check_res_002(ctx: GateContext) -> list[Finding]:
    """Enforce verifiable primary references and bidirectional inline citation integrity."""
    findings: list[Finding] = []
    min_citations = int(ctx.policy.get("research", {}).get("min_citations", 3))

    for path in _discover_research_files(ctx):
        rel = ctx.relpath(path)
        text = path.read_text(encoding="utf-8", errors="replace")
        _, body, _ = parse_frontmatter(text)
        sections = extract_sections(body, level=2)
        refs_sec = sections.get("References", "")

        ref_numbers: dict[int, str] = {}
        verifiable_count = 0
        for line in refs_sec.splitlines():
            m = REF_LINE_RE.match(line)
            if not m:
                continue
            num = int(m.group(1))
            content = m.group(2).strip()
            ref_numbers[num] = content
            if SOURCE_INDICATOR_RE.search(content):
                verifiable_count += 1
            else:
                findings.append(
                    Finding(
                        rule_id="RES-002",
                        severity=Severity.ERROR,
                        message=f"Reference [{num}] lacks a verifiable source locator (URL, DOI, RFC, ISBN, or ISO).",
                        path=rel,
                        remediation="Include a verifiable primary URL, DOI, RFC, ISBN, or standard identifier.",
                    )
                )

        if verifiable_count < min_citations:
            findings.append(
                Finding(
                    rule_id="RES-002",
                    severity=Severity.ERROR,
                    message=(
                        f"Research dossier has {verifiable_count} verifiable reference(s); "
                        f"minimum required is {min_citations}."
                    ),
                    path=rel,
                    remediation=f"Cite at least {min_citations} verifiable primary sources in '## References'.",
                )
            )

        # Gather inline citations across all sections except References.
        prose_chunks = [
            strip_fenced_code_blocks(sec_body)
            for sec_name, sec_body in sections.items()
            if sec_name != "References"
        ]
        prose_text = "\n".join(prose_chunks)
        # Strip standard markdown links `[label](url)` so numeric labels aren't misread.
        prose_text = re.sub(r"\[[^\]]+\]\([^)]+\)", "", prose_text)
        prose_text = re.sub(r"`[^`]*`", "", prose_text)
        inline_nums = {int(m.group(1)) for m in INLINE_CITE_RE.finditer(prose_text)}

        dangling = sorted(inline_nums - set(ref_numbers.keys()))
        if dangling:
            findings.append(
                Finding(
                    rule_id="RES-002",
                    severity=Severity.ERROR,
                    message=f"Dangling inline citation(s) not listed in '## References': {dangling}.",
                    path=rel,
                    remediation="Ensure every inline citation [N] matches a numbered entry in '## References'.",
                )
            )

        uncited = sorted(set(ref_numbers.keys()) - inline_nums)
        if uncited:
            findings.append(
                Finding(
                    rule_id="RES-002",
                    severity=Severity.ERROR,
                    message=f"Uncited reference(s) in '## References' never referenced in body: {uncited}.",
                    path=rel,
                    remediation="Cite every listed reference inline using [N] where it supports technical claims.",
                )
            )

    return findings


def check_res_003(ctx: GateContext) -> list[Finding]:
    """Reject hollow or stub research sections below minimum substantive word depth."""
    findings: list[Finding] = []
    res_cfg = ctx.policy.get("research", {})
    min_words = int(res_cfg.get("min_words_per_section", 25))
    req_sections = res_cfg.get("required_sections", [])

    for path in _discover_research_files(ctx):
        rel = ctx.relpath(path)
        text = path.read_text(encoding="utf-8", errors="replace")
        _, body, _ = parse_frontmatter(text)
        sections = extract_sections(body, level=2)

        for sec in req_sections:
            if sec not in sections or sec == "References":
                continue
            wc = word_count(sections[sec])
            if wc < min_words:
                findings.append(
                    Finding(
                        rule_id="RES-003",
                        severity=Severity.ERROR,
                        message=(
                            f"Research section '## {sec}' has only {wc} words "
                            f"(minimum substantive threshold is {min_words} words)."
                        ),
                        path=rel,
                        remediation=f"Provide substantive technical analysis in '## {sec}'.",
                    )
                )

    return findings


def check_res_004(ctx: GateContext) -> list[Finding]:
    """Verify every component and every accepted ADR references at least one valid research dossier."""
    findings: list[Finding] = []
    existing_res_ids: set[str] = set()
    for path in _discover_research_files(ctx):
        m = RES_FILENAME_RE.match(path.name)
        if m:
            existing_res_ids.add(m.group(1))

    # 1. Check all components.
    for comp in ctx.components:
        if not comp.manifest:
            continue
        rel = ctx.relpath(comp.manifest_path)
        refs = comp.manifest.get("research_refs", [])
        if not isinstance(refs, list) or len(refs) == 0:
            findings.append(
                Finding(
                    rule_id="RES-004",
                    severity=Severity.ERROR,
                    message=f"Component '{comp.name}' must reference at least one Research Dossier in 'research_refs'.",
                    path=rel,
                    remediation="Add valid RES-XXXX IDs to manifest 'research_refs'.",
                )
            )
            continue
        for ref_id in refs:
            if ref_id not in existing_res_ids:
                findings.append(
                    Finding(
                        rule_id="RES-004",
                        severity=Severity.ERROR,
                        message=f"Component '{comp.name}' references non-existent research dossier '{ref_id}'.",
                        path=rel,
                        remediation=f"Create 'docs/research/{ref_id}-<slug>.md' or fix the ID in '{rel}'.",
                    )
                )

    # 2. Check all ADRs.
    adr_dir = ctx.repo_root / ctx.policy.get("documentation", {}).get("adr_directory", "docs/adr")
    if adr_dir.is_dir():
        for adr_path in sorted(adr_dir.glob("ADR-*.md")):
            rel = ctx.relpath(adr_path)
            fm, _, err = parse_frontmatter(adr_path.read_text(encoding="utf-8", errors="replace"))
            if err or not fm:
                continue
            refs = fm.get("research_refs", [])
            if isinstance(refs, str):
                refs = [refs]
            if not isinstance(refs, list) or len(refs) == 0:
                findings.append(
                    Finding(
                        rule_id="RES-004",
                        severity=Severity.ERROR,
                        message=f"ADR '{adr_path.name}' must cite at least one research dossier in 'research_refs'.",
                        path=rel,
                        remediation="Link supporting RES-XXXX dossiers in ADR frontmatter.",
                    )
                )
                continue
            for ref_id in refs:
                if ref_id not in existing_res_ids:
                    findings.append(
                        Finding(
                            rule_id="RES-004",
                            severity=Severity.ERROR,
                            message=f"ADR '{adr_path.name}' references non-existent research dossier '{ref_id}'.",
                            path=rel,
                            remediation=f"Create missing research dossier '{ref_id}' or fix 'research_refs'.",
                        )
                    )

    return findings


def register(registry: RuleRegistry) -> None:
    registry.register(
        RuleSpec(
            rule_id="RES-001",
            domain="research",
            title="Research Dossier Frontmatter & Section Structure",
            summary="Every RES-XXXX dossier must have valid naming, frontmatter, and all 8 mandatory technical sections.",
        ),
        check_res_001,
    )
    registry.register(
        RuleSpec(
            rule_id="RES-002",
            domain="research",
            title="Verifiable Primary Reference & Bidirectional Citation Integrity",
            summary="Research dossiers must include >= 3 verifiable sources with zero uncited or dangling inline citations.",
        ),
        check_res_002,
    )
    registry.register(
        RuleSpec(
            rule_id="RES-003",
            domain="research",
            title="Research Dossier Substantive Depth (Anti-Stub Gate)",
            summary="Each mandatory research section must exceed the configured substantive word threshold.",
        ),
        check_res_003,
    )
    registry.register(
        RuleSpec(
            rule_id="RES-004",
            domain="research",
            title="Mandatory Research Linkage for Components & ADRs",
            summary="Every component manifest and ADR must link to at least one existing valid Research Dossier.",
        ),
        check_res_004,
    )
