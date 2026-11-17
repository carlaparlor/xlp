# `xlp-gate` Public API & Extension Points

`xlp-gate` exposes both a stable command-line interface and a clean Python programmatic API for extending enforcement rules or integrating custom reporters.

## Public Modules (`api_version: 1.0.0`, `abi_version: 1`)

- `tools.xlp_gate.models`: Immutable `RuleSpec`, `Severity`, `Finding`, `Component`, `GateContext`, and `GateReport` data structures.
- `tools.xlp_gate.registry`: `RuleRegistry` and `build_default_registry()` enabling registration of custom fitness rules via `registry.register(RuleSpec(...), checker_fn)`.
- `tools.xlp_gate.runner`: `run_gate(repo_root, strict=True, run_tests=False, ...)` plus `format_text_report`, `format_json_report`, and `format_markdown_report`.
- `tools.xlp_gate.schema_validator`: `validate_schema(instance, schema)` providing Draft 2020-12 core JSON Schema validation with `semver`, `date`, `uuid`, and `uri` format validators.
- `tools.xlp_gate.scaffold`: `scaffold_plugin`, `scaffold_module`, and `scaffold_doc_artifact` for generating schema-compliant starter components and documentation artifacts.

## Extension Points

### `gate.rules` (`v1.0.0`, lifecycle: `init`)

Custom rules implement `CheckFunc = Callable[[GateContext], list[Finding]]` and register a `RuleSpec` into `RuleRegistry`. Adding any permanent repository rule requires simultaneous updates to:

1. Its domain module under `tools/xlp_gate/checks/`.
2. `docs/reference/enforcement-rules.md` (`DOC-004`).
3. `governance/traceability.json` (`TST-004`).
4. Both positive and adversarial tests in `tools/xlp_gate/tests/`.

### `gate.report_formatters` (`v1.0.0`, lifecycle: `runtime`)

`GateReport.to_dict()` emits a stable JSON-serializable report payload containing rule counts, findings, waived findings, executed test results, and elapsed duration in milliseconds.
