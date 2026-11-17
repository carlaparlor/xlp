"""Pure-Python Markdown and YAML frontmatter utilities for XLP governance checks."""

from __future__ import annotations

import re
from typing import Any

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
LINK_RE = re.compile(r"(?<!!)\[([^\]]+)\]\(([^)]+)\)")
FENCE_RE = re.compile(r"^\s*(```|~~~)")


def _parse_scalar(raw: str) -> Any:
    val = raw.strip()
    if not val:
        return ""
    if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
        return val[1:-1]
    lower = val.lower()
    if lower == "true":
        return True
    if lower == "false":
        return False
    if lower in ("null", "~"):
        return None
    if val.startswith("[") and val.endswith("]"):
        inner = val[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(item) for item in inner.split(",")]
    if re.fullmatch(r"-?\d+", val):
        return int(val)
    if re.fullmatch(r"-?\d+\.\d+", val):
        return float(val)
    return val


def parse_frontmatter(text: str) -> tuple[dict[str, Any] | None, str, str | None]:
    """Parse leading YAML frontmatter (`--- ... ---`).

    Returns `(metadata_dict_or_none, body_without_frontmatter, error_message_or_none)`.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, text, None

    end_idx = None
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            end_idx = idx
            break
    if end_idx is None:
        return None, text, "Unterminated YAML frontmatter block (missing closing '---')."

    fm_lines = lines[1:end_idx]
    body = "\n".join(lines[end_idx + 1 :])
    data: dict[str, Any] = {}
    current_list_key: str | None = None

    for raw_line in fm_lines:
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("- "):
            if current_list_key is None:
                return None, body, f"Unexpected YAML list item without key: {raw_line}"
            if not isinstance(data[current_list_key], list):
                data[current_list_key] = []
            data[current_list_key].append(_parse_scalar(stripped[2:]))
            continue

        if ":" not in raw_line:
            return None, body, f"Invalid YAML frontmatter line: {raw_line}"

        key, rest = raw_line.split(":", 1)
        key = key.strip()
        rest = rest.strip()
        if not key:
            return None, body, f"Empty key in YAML frontmatter line: {raw_line}"
        if rest == "":
            data[key] = []
            current_list_key = key
        else:
            data[key] = _parse_scalar(rest)
            current_list_key = key if isinstance(data[key], list) else None

    return data, body, None


def strip_fenced_code_blocks(text: str) -> str:
    """Replace lines inside fenced code blocks with empty lines to preserve line numbers."""
    out: list[str] = []
    in_fence = False
    fence_marker = ""
    for line in text.splitlines():
        m = FENCE_RE.match(line)
        if m:
            marker = m.group(1)
            if not in_fence:
                in_fence = True
                fence_marker = marker
                out.append("")
                continue
            if marker == fence_marker:
                in_fence = False
                fence_marker = ""
                out.append("")
                continue
        out.append("" if in_fence else line)
    return "\n".join(out)


def extract_sections(body: str, level: int = 2) -> dict[str, str]:
    """Extract mapping of heading title -> section text for headings of `level`."""
    sections: dict[str, list[str]] = {}
    current_title: str | None = None
    in_fence = False
    fence_marker = ""
    prefix = "#" * level + " "

    for line in body.splitlines():
        m = FENCE_RE.match(line)
        if m:
            marker = m.group(1)
            if not in_fence:
                in_fence = True
                fence_marker = marker
            elif marker == fence_marker:
                in_fence = False
                fence_marker = ""
            if current_title is not None:
                sections[current_title].append(line)
            continue

        if not in_fence and line.startswith(prefix) and not line.startswith("#" * (level + 1)):
            current_title = line[len(prefix) :].strip()
            sections.setdefault(current_title, [])
            continue
        if not in_fence and current_title is not None and re.match(r"^#{1," + str(level - 1) + r"}\s+", line):
            current_title = None
            continue

        if current_title is not None:
            sections[current_title].append(line)

    return {title: "\n".join(content).strip() for title, content in sections.items()}


def slugify_heading(heading: str) -> str:
    """GitHub-compatible Markdown heading anchor slugifier."""
    cleaned = re.sub(r"`([^`]*)`", r"\1", heading)
    cleaned = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", cleaned)
    cleaned = cleaned.strip().lower()
    cleaned = re.sub(r"[^\w\s-]", "", cleaned)
    cleaned = re.sub(r"\s+", "-", cleaned)
    return cleaned


def extract_heading_slugs(text: str) -> set[str]:
    """Return all GitHub-style heading anchor slugs present in a Markdown document."""
    slugs: set[str] = set()
    counts: dict[str, int] = {}
    stripped = strip_fenced_code_blocks(text)
    for line in stripped.splitlines():
        m = HEADING_RE.match(line)
        if not m:
            continue
        base = slugify_heading(m.group(2))
        if not base:
            continue
        idx = counts.get(base, 0)
        counts[base] = idx + 1
        slugs.add(base if idx == 0 else f"{base}-{idx}")
    return slugs


def extract_markdown_links(text: str) -> list[tuple[int, str, str]]:
    """Return list of `(line_number, link_text, target)` outside fenced code blocks."""
    results: list[tuple[int, str, str]] = []
    stripped = strip_fenced_code_blocks(text)
    for lineno, line in enumerate(stripped.splitlines(), start=1):
        # Mask inline code spans so syntax examples like `[text](path)` do not fire.
        line_no_code = re.sub(r"`[^`]*`", "", line)
        for match in LINK_RE.finditer(line_no_code):
            results.append((lineno, match.group(1), match.group(2).strip()))
    return results


def word_count(text: str) -> int:
    cleaned = strip_fenced_code_blocks(text)
    tokens = re.findall(r"[A-Za-z0-9_'-]+", cleaned)
    return len(tokens)
