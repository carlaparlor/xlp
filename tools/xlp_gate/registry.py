"""Extensible rule registry for the XLP architectural fitness gate."""

from __future__ import annotations

from dataclasses import dataclass

from tools.xlp_gate.models import CheckFunc, RuleSpec


@dataclass(frozen=True)
class RegisteredRule:
    spec: RuleSpec
    checker: CheckFunc


class RuleRegistry:
    """Central registry enabling modular registration of architectural fitness rules."""

    def __init__(self) -> None:
        self._rules: dict[str, RegisteredRule] = {}

    def register(self, spec: RuleSpec, checker: CheckFunc) -> None:
        if spec.rule_id in self._rules:
            raise ValueError(f"Duplicate rule registration attempted for '{spec.rule_id}'")
        self._rules[spec.rule_id] = RegisteredRule(spec=spec, checker=checker)

    def get(self, rule_id: str) -> RegisteredRule | None:
        return self._rules.get(rule_id)

    def all_rules(self) -> list[RegisteredRule]:
        return [self._rules[rid] for rid in sorted(self._rules.keys())]

    def specs_map(self) -> dict[str, RuleSpec]:
        return {rid: reg.spec for rid, reg in sorted(self._rules.items())}

    def rule_ids(self) -> list[str]:
        return sorted(self._rules.keys())


def build_default_registry() -> RuleRegistry:
    """Construct the canonical XLP rule registry with all 9 enforcement domains."""
    from tools.xlp_gate.checks import (
        brand_checks,
        documentation_checks,
        extensibility_checks,
        governance_checks,
        moddability_checks,
        modularity_checks,
        research_checks,
        scalability_checks,
        testing_checks,
    )

    registry = RuleRegistry()
    for module in (
        brand_checks,
        modularity_checks,
        scalability_checks,
        extensibility_checks,
        moddability_checks,
        research_checks,
        testing_checks,
        documentation_checks,
        governance_checks,
    ):
        module.register(registry)
    return registry
