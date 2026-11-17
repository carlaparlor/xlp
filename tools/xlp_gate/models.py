"""Core data models for the XLP enforcement gate."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True)
class RuleSpec:
    rule_id: str
    domain: str
    title: str
    summary: str
    severity: Severity = Severity.ERROR
    requires_test_execution: bool = False


@dataclass
class Finding:
    rule_id: str
    severity: Severity
    message: str
    path: str
    line: int | None = None
    remediation: str = ""
    waived_by: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "severity": self.severity.value,
            "message": self.message,
            "path": self.path,
            "line": self.line,
            "remediation": self.remediation,
            "waived_by": self.waived_by,
        }


@dataclass
class Component:
    layer: str
    name: str
    directory: Path
    manifest_path: Path
    manifest: dict[str, Any] | None = None
    manifest_error: str | None = None

    @property
    def rel_dir(self) -> str:
        return self.directory.as_posix()

    @property
    def component_id(self) -> str | None:
        if self.manifest and isinstance(self.manifest.get("id"), str):
            return self.manifest["id"]
        return None


@dataclass
class GateContext:
    repo_root: Path
    policy: dict[str, Any]
    brand: dict[str, Any] | None
    waivers: list[dict[str, Any]]
    traceability: dict[str, Any] | None
    schemas: dict[str, dict[str, Any]]
    components: list[Component]
    registered_rules: dict[str, RuleSpec]
    run_tests: bool = False
    strict: bool = True
    today_iso: str | None = None

    def relpath(self, path: Path) -> str:
        try:
            return path.resolve().relative_to(self.repo_root.resolve()).as_posix()
        except ValueError:
            return path.as_posix()


CheckFunc = Callable[[GateContext], list[Finding]]


@dataclass
class GateReport:
    passed: bool
    strict: bool
    run_tests: bool
    rules_evaluated: list[str]
    findings: list[Finding] = field(default_factory=list)
    waived_findings: list[Finding] = field(default_factory=list)
    duration_ms: int = 0
    executed_test_commands: list[dict[str, Any]] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.WARNING)

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "strict": self.strict,
            "run_tests": self.run_tests,
            "rules_evaluated_count": len(self.rules_evaluated),
            "rules_evaluated": self.rules_evaluated,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "waived_count": len(self.waived_findings),
            "duration_ms": self.duration_ms,
            "executed_test_commands": self.executed_test_commands,
            "findings": [f.to_dict() for f in self.findings],
            "waived_findings": [f.to_dict() for f in self.waived_findings],
        }
