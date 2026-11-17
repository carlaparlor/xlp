# `xlp-gate` Testing Strategy & Adversarial Verification Matrix

An architectural enforcement engine that is not adversarially tested creates a false sense of security—rules can silently pass vacuously when a repository contains zero plugins or when regex logic drifts. `xlp-gate` enforces four mandatory testing categories across its own suite (`unit`, `adversarial`, `integration`, `schema`).

## Verification Tiers

1. **Schema Validator Unit & Edge-Case Tests (`test_schema_validator.py`)**: Verifies type checking, `const`, `enum`, `pattern`, `minimum`/`maximum`, `exclusiveMinimum`, `uniqueItems`, `additionalProperties`, `$ref`, `allOf`/`anyOf`/`oneOf`/`not`, and format validators (`semver`, `date`, `uuid`, `uri`).
2. **Positive & Adversarial Rule Tests (`test_brand_and_governance.py`, `test_modularity.py`, `test_scalability_rt.py`, `test_extensibility_moddability.py`, `test_research_docs.py`, `test_testing_and_hooks.py`)**: Every single one of the 39 registered rules is exercised inside isolated temporary repositories against both a **compliant fixture** (must pass with zero findings for that rule) and one or more **deliberately broken adversarial fixtures** (must fail with the exact expected `RULE-ID`).
3. **Real Git Hook & CLI Integration Tests (`test_testing_and_hooks.py`)**: Initializes real temporary Git repositories, runs `scripts/install-hooks.sh`, verifies that `pre-commit` blocks bad commits and allows compliant commits, verifies `commit-msg` rejects non-Conventional Commit messages while preserving Arena's `Co-authored-by` trailer, and verifies `xlp-gate scaffold` produces components that immediately pass strict gate checks.
4. **Live Dogfood Self-Test (`test_self_dogfood.py`)**: Executes `xlp-gate` in strict mode against the actual repository root, verifies zero errors and zero warnings, and verifies 100% parity across registered rules, `docs/reference/enforcement-rules.md`, `governance/traceability.json`, and accepted ADRs.

## Execution

```bash
python3 -m unittest discover -s tools/xlp_gate/tests -p test_*.py -v
```
