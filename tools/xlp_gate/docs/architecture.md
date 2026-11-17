# `xlp-gate` Internal Architecture

`xlp-gate` is deliberately designed using the same modular, scalable, extensible, and strictly tested principles it enforces across all XLP audio plugins.

## Design Constraints

1. **Zero External Dependencies**: Implemented strictly with Python 3.11+ standard library modules (`json`, `re`, `pathlib`, `subprocess`, `datetime`, `dataclasses`, `argparse`, `unittest`) so enforcement executes identically across local machines, CI runners, and air-gapped sandboxes without external package drift.
2. **Data-Driven Policy**: Thresholds, allowed layer matrices, forbidden real-time audio patterns, required test categories, and required documentation structures live in `governance/policy.json`, validated by `governance/schemas/policy.schema.json` and protected by hardcoded constitutional floors in `checks/governance_checks.py`.
3. **Extensible Rule Registry**: Every enforcement check registers through `RuleRegistry.register(RuleSpec, CheckFunc)`, cleanly decoupling domain check modules (`checks/*.py`) from orchestration, waiver resolution, and report formatting (`runner.py`).

## Execution Pipeline

1. `cli.py` parses command flags (`--strict`, `--run-tests`, `--rule`, `--domain`, `--format`, `--json-out`).
2. `registry.py` builds the canonical `RuleRegistry` containing all 39 rules across 9 domain modules.
3. `policy.py` loads `policy.json`, `brand.json`, `waivers.json`, `traceability.json`, all JSON Schemas under `governance/schemas/`, and discovers components across `core/`, `modules/`, `adapters/`, `plugins/`, and `tools/`.
4. `runner.py` evaluates every selected rule deterministically, separates legally waived findings (for waivable rules backed by valid unexpired ADRs) from active errors, optionally runs live component test suites (`TST-003`), and renders text, Markdown, or JSON reports.
5. Exit code `0` indicates zero active findings; exit code `1` strictly blocks commits, pushes, and pull requests.

## Component Cohesion

Every production module under `tools/xlp_gate/` stays comfortably below the 600-line ceiling enforced by `MOD-006`, with pure utilities (`schema_validator.py`, `markdown_utils.py`) decoupled from domain checkers and CLI concerns.
