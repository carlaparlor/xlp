# `xlp-gate` CLI & Report Reference

`./xlp-gate` is the canonical command-line entrypoint for running architectural fitness checks, verifying local Git hooks, inspecting rules, and scaffolding compliant XLP components.

## Global Options

| Flag | Default | Description |
| --- | --- | --- |
| `--root <path>` | repository root / cwd | Target repository root to evaluate. |
| `--version` | — | Print `xlp-gate` semantic version and exit. |

## Subcommands

### `./xlp-gate check`

Evaluates registered rules against the repository and exits `0` on pass or `1` on any violation.

| Flag | Default | Description |
| --- | --- | --- |
| `--strict` / `--no-strict` | `--strict` | Fail on both errors and warnings (`--strict`), or errors only (`--no-strict`). |
| `--run-tests` | off | Execute every component's declared `testing.command` live (`TST-003`). Mandatory in CI and `pre-push`. |
| `--rule <ID>` | all | Evaluate only the specified rule ID (repeatable). |
| `--domain <name>` | all | Evaluate only rules in the specified domain (repeatable). |
| `--format <text\|json\|markdown>` | `text` | Output format written to stdout. |
| `--json-out <path>` | none | Also write the machine-readable JSON audit report to `<path>`. |

### `./xlp-gate list-rules`

Prints all registered rules sorted by rule ID, optionally filtered with `--domain <domain>`.

### `./xlp-gate verify-hooks`

Checks that `.git/hooks/{pre-commit,commit-msg,pre-push}` exist, are executable, and contain the `XLP_MANAGED_HOOK` marker installed by `./scripts/install-hooks.sh`. Exits `0` if valid, `1` otherwise.

### `./xlp-gate scaffold`

Generates compliant starter artifacts from canonical templates:

```bash
./xlp-gate scaffold plugin <snake_slug> [--category effect|instrument|utility|analyzer|midi_fx|modular_rack]
./xlp-gate scaffold module <snake_slug> --layer core|modules|adapters [--module-kind dsp|ui|state|modding|adapter|utility]
./xlp-gate scaffold adr <kebab-slug> --title "Decision Title"
./xlp-gate scaffold research <kebab-slug> --title "Research Dossier Title"
```

## JSON Report Schema (`--format json` / `--json-out`)

```json
{
  "passed": true,
  "strict": true,
  "run_tests": true,
  "rules_evaluated_count": 39,
  "rules_evaluated": ["BRD-001", "..."],
  "error_count": 0,
  "warning_count": 0,
  "waived_count": 0,
  "duration_ms": 420,
  "executed_test_commands": [
    {
      "component": "xlp.tools.xlp_gate",
      "command": "python3 -m unittest discover -s tools/xlp_gate/tests -p test_*.py -v",
      "exit_code": 0
    }
  ],
  "findings": [],
  "waived_findings": []
}
```
