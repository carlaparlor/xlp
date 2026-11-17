"""Scalability and hard real-time audio safety checks (SCA-001..SCA-004)."""

from __future__ import annotations

import re
from pathlib import Path

from tools.xlp_gate.models import Component, Finding, GateContext, RuleSpec, Severity
from tools.xlp_gate.registry import RuleRegistry


def _strip_comments_and_strings(text: str) -> list[str]:
    """Strip C/C++/Rust comments and string literals while preserving exact line count."""
    result: list[str] = []
    i = 0
    n = len(text)
    in_block = False
    in_line = False
    in_str = False
    str_quote = ""

    while i < n:
        ch = text[i]
        nxt = text[i + 1] if i + 1 < n else ""

        if in_line:
            if ch == "\n":
                in_line = False
                result.append("\n")
            else:
                result.append(" ")
            i += 1
            continue

        if in_block:
            if ch == "*" and nxt == "/":
                in_block = False
                result.append("  ")
                i += 2
            else:
                result.append("\n" if ch == "\n" else " ")
                i += 1
            continue

        if in_str:
            if ch == "\\" and i + 1 < n:
                result.append("  ")
                i += 2
                continue
            if ch == str_quote:
                in_str = False
                result.append(" ")
            else:
                result.append("\n" if ch == "\n" else " ")
            i += 1
            continue

        if ch == "/" and nxt == "/":
            in_line = True
            result.append("  ")
            i += 2
            continue
        if ch == "/" and nxt == "*":
            in_block = True
            result.append("  ")
            i += 2
            continue
        if ch in ('"', "'"):
            in_str = True
            str_quote = ch
            result.append(" ")
            i += 1
            continue

        result.append(ch)
        i += 1

    return "".join(result).splitlines()


def _is_rt_source_file(path: Path, comp: Component, rt_segments: set[str], rt_exts: set[str]) -> bool:
    if path.suffix.lower() not in rt_exts:
        return False
    rel_parts = [p.lower() for p in path.relative_to(comp.directory).parts]
    if any(part in ("tests", "test", "fixtures", "build") for part in rel_parts):
        return False
    if any(seg in rel_parts for seg in rt_segments):
        return True
    if comp.manifest and comp.manifest.get("kind") == "dsp":
        return True
    return False


def check_sca_001(ctx: GateContext) -> list[Finding]:
    """Scope-aware static real-time audio safety analysis."""
    findings: list[Finding] = []
    rt_cfg = ctx.policy.get("realtime_safety", {})
    rt_segments = {s.lower() for s in rt_cfg.get("rt_path_segments", ["dsp", "realtime", "audio_thread"])}
    rt_exts = {e.lower() for e in rt_cfg.get("rt_source_extensions", [".c", ".cpp", ".h", ".hpp", ".rs"])}
    markers = rt_cfg.get("non_rt_scope_markers", {})
    begin_marker = markers.get("begin", "XLP_NON_RT_BEGIN")
    end_marker = markers.get("end", "XLP_NON_RT_END")
    line_allow = markers.get("line_allow", "XLP_NON_RT_INIT")
    non_rt_fns = markers.get("function_names", [])
    fn_sig_re = (
        re.compile(r"\b(?:" + "|".join(re.escape(fn) for fn in non_rt_fns) + r")\s*\(")
        if non_rt_fns
        else None
    )

    compiled_patterns = [
        (item["id"], re.compile(item["pattern"]), item["reason"])
        for item in rt_cfg.get("forbidden_patterns", [])
    ]

    for comp in ctx.components:
        if not comp.directory.is_dir():
            continue
        for src in sorted(comp.directory.rglob("*")):
            if not src.is_file() or not _is_rt_source_file(src, comp, rt_segments, rt_exts):
                continue
            try:
                raw_text = src.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue

            raw_lines = raw_text.splitlines()
            clean_lines = _strip_comments_and_strings(raw_text)
            rel = ctx.relpath(src)

            in_explicit_non_rt = False
            in_non_rt_fn = False
            pending_non_rt_fn = False
            fn_brace_depth = 0

            for idx, clean_line in enumerate(clean_lines):
                lineno = idx + 1
                raw_line = raw_lines[idx] if idx < len(raw_lines) else ""

                if begin_marker in raw_line:
                    in_explicit_non_rt = True
                    continue
                if end_marker in raw_line:
                    in_explicit_non_rt = False
                    continue

                if not in_non_rt_fn and fn_sig_re and fn_sig_re.search(clean_line):
                    if "{" in clean_line:
                        in_non_rt_fn = True
                        fn_brace_depth = clean_line.count("{") - clean_line.count("}")
                        if fn_brace_depth <= 0:
                            in_non_rt_fn = False
                            fn_brace_depth = 0
                        continue
                    if not clean_line.rstrip().endswith(";"):
                        pending_non_rt_fn = True
                        continue
                elif pending_non_rt_fn:
                    if "{" in clean_line:
                        pending_non_rt_fn = False
                        in_non_rt_fn = True
                        fn_brace_depth = clean_line.count("{") - clean_line.count("}")
                        if fn_brace_depth <= 0:
                            in_non_rt_fn = False
                            fn_brace_depth = 0
                        continue
                    if ";" in clean_line:
                        pending_non_rt_fn = False
                        continue
                elif in_non_rt_fn:
                    fn_brace_depth += clean_line.count("{") - clean_line.count("}")
                    if fn_brace_depth <= 0:
                        in_non_rt_fn = False
                        fn_brace_depth = 0
                    continue

                if in_explicit_non_rt or line_allow in raw_line:
                    continue

                for pat_id, regex, reason in compiled_patterns:
                    if regex.search(clean_line):
                        findings.append(
                            Finding(
                                rule_id="SCA-001",
                                severity=Severity.ERROR,
                                message=f"Real-time safety violation ({pat_id}): {reason}",
                                path=rel,
                                line=lineno,
                                remediation=(
                                    "Eliminate blocking/allocating calls from audio-thread paths; pre-allocate in "
                                    "prepare()/activate() or communicate via lock-free queues/atomics."
                                ),
                            )
                        )

    return findings


def _requires_rt_contract(comp: Component) -> bool:
    if comp.layer == "plugins":
        return True
    if comp.manifest and comp.manifest.get("kind") == "dsp":
        return True
    return False


def check_sca_002(ctx: GateContext) -> list[Finding]:
    """Verify real-time safety and threading contract declarations on DSP modules and plugins."""
    findings: list[Finding] = []
    rt_cfg = ctx.policy.get("realtime_safety", {})
    required_rates = set(rt_cfg.get("required_sample_rates", [44100, 48000, 96000]))
    allowed_comms = set(rt_cfg.get("allowed_thread_communication", []))

    for comp in ctx.components:
        if not comp.manifest or not _requires_rt_contract(comp):
            continue
        rel = ctx.relpath(comp.manifest_path)
        contract = comp.manifest.get("realtime_contract")
        if not isinstance(contract, dict):
            findings.append(
                Finding(
                    rule_id="SCA-002",
                    severity=Severity.ERROR,
                    message=f"DSP/plugin component '{comp.name}' must declare 'realtime_contract' in manifest.",
                    path=rel,
                    remediation="Add a compliant 'realtime_contract' section to the manifest.",
                )
            )
            continue

        for flag in ("audio_thread_lock_free", "audio_thread_alloc_free", "denormal_protection", "arbitrary_block_sizes"):
            if contract.get(flag) is not True:
                findings.append(
                    Finding(
                        rule_id="SCA-002",
                        severity=Severity.ERROR,
                        message=f"realtime_contract.{flag} must be true for hard real-time audio safety.",
                        path=rel,
                        remediation=f"Implement and declare realtime_contract.{flag} = true.",
                    )
                )

        rates = set(contract.get("supported_sample_rates", []))
        missing_rates = sorted(required_rates - rates)
        if missing_rates:
            findings.append(
                Finding(
                    rule_id="SCA-002",
                    severity=Severity.ERROR,
                    message=f"realtime_contract.supported_sample_rates missing mandatory rates: {missing_rates}.",
                    path=rel,
                    remediation=f"Support and declare sample rates including {sorted(required_rates)}.",
                )
            )

        comm = contract.get("thread_communication")
        if comm not in allowed_comms:
            findings.append(
                Finding(
                    rule_id="SCA-002",
                    severity=Severity.ERROR,
                    message=(
                        f"realtime_contract.thread_communication '{comm}' is not a permitted lock-free mechanism "
                        f"(allowed: {sorted(allowed_comms)})."
                    ),
                    path=rel,
                    remediation="Use lock-free atomics, SPSC ringbuffers, or double/triple buffering.",
                )
            )

    return findings


def check_sca_003(ctx: GateContext) -> list[Finding]:
    """Verify performance and resource budget declarations for DSP modules and plugins."""
    findings: list[Finding] = []
    for comp in ctx.components:
        if not comp.manifest or not _requires_rt_contract(comp):
            continue
        rel = ctx.relpath(comp.manifest_path)
        budget = comp.manifest.get("performance_budget")
        if not isinstance(budget, dict):
            findings.append(
                Finding(
                    rule_id="SCA-003",
                    severity=Severity.ERROR,
                    message=f"DSP/plugin component '{comp.name}' must declare 'performance_budget'.",
                    path=rel,
                    remediation="Declare CPU %, memory MB, latency samples, and benchmark_target in manifest.",
                )
            )
            continue

        cpu = budget.get("max_cpu_percent_single_core_48k_64buf")
        if not isinstance(cpu, (int, float)) or cpu <= 0 or cpu > 50:
            findings.append(
                Finding(
                    rule_id="SCA-003",
                    severity=Severity.ERROR,
                    message=f"Unrealistic single-instance CPU budget ({cpu}%); must be > 0 and <= 50%.",
                    path=rel,
                    remediation="Set max_cpu_percent_single_core_48k_64buf to a realistic scalable budget (<= 50%).",
                )
            )
    return findings


def check_sca_004(ctx: GateContext) -> list[Finding]:
    """Verify VST3 format targeting and channel layout declarations on plugins."""
    findings: list[Finding] = []
    default_formats = set((ctx.brand or {}).get("default_formats", ["vst3"]))

    for comp in ctx.components:
        if comp.layer != "plugins" or not comp.manifest:
            continue
        rel = ctx.relpath(comp.manifest_path)
        formats = set(comp.manifest.get("formats", []))
        missing = sorted(default_formats - formats)
        if missing:
            findings.append(
                Finding(
                    rule_id="SCA-004",
                    severity=Severity.ERROR,
                    message=f"Plugin '{comp.name}' is missing required target format(s): {missing}.",
                    path=rel,
                    remediation=f"Include {missing} in manifest 'formats'.",
                )
            )

        layouts = comp.manifest.get("channel_layouts", [])
        if not isinstance(layouts, list) or len(layouts) == 0:
            findings.append(
                Finding(
                    rule_id="SCA-004",
                    severity=Severity.ERROR,
                    message=f"Plugin '{comp.name}' must declare at least one audio channel layout.",
                    path=rel,
                    remediation="Add explicit channel_layouts (e.g. stereo 2-in/2-out) to manifest.",
                )
            )

    return findings


def register(registry: RuleRegistry) -> None:
    registry.register(
        RuleSpec(
            rule_id="SCA-001",
            domain="scalability",
            title="Real-Time Audio Thread Static Safety Analysis",
            summary="Audio-thread DSP code must contain zero heap allocations, mutex locks, blocking I/O, thread sleeps, or throws.",
        ),
        check_sca_001,
    )
    registry.register(
        RuleSpec(
            rule_id="SCA-002",
            domain="scalability",
            title="Real-Time & Lock-Free Threading Contract",
            summary="DSP modules and plugins must declare lock-free, alloc-free, denormal-safe, multi-rate, arbitrary-block contracts.",
        ),
        check_sca_002,
    )
    registry.register(
        RuleSpec(
            rule_id="SCA-003",
            domain="scalability",
            title="Quantitative Performance & Resource Budget",
            summary="DSP modules and plugins must declare CPU, memory, latency ceilings, and a benchmark target.",
        ),
        check_sca_003,
    )
    registry.register(
        RuleSpec(
            rule_id="SCA-004",
            domain="scalability",
            title="Mandatory VST3 Target & Channel Layout Contract",
            summary="Every XLP plugin must target VST3 and declare explicit multi-channel bus layouts.",
        ),
        check_sca_004,
    )
