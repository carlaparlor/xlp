# Contributing to XLP

Welcome to the XLP VST plugin repository. Every contribution is governed by the automated [`xlp-gate`](docs/reference/cli-reference.md) enforcement engine so architectural quality never degrades as the plugin suite grows.

## First-Time Setup

```bash
./scripts/install-hooks.sh
./xlp-gate verify-hooks
./xlp-gate check --strict --run-tests
```

## Commit Message Convention

The `commit-msg` hook enforces Conventional Commits:

```text
<type>(<optional-scope>): <imperative summary>
```

Allowed types: `feat`, `fix`, `docs`, `research`, `test`, `refactor`, `arch`, `chore`, `ci`, `mod`, `perf`, `build`.

## Pull Request Acceptance Criteria

A pull request can be merged only when all of the following succeed without bypasses:

1. `./xlp-gate check --strict --run-tests` exits with code `0` locally and in `.github/workflows/xlp-gate.yml`.
2. Every new module, adapter, or plugin links to verified research (`RES-XXXX`), accepted ADRs (`ADR-XXXX`), complete Diátaxis/component documentation, and passing multi-category tests.
3. Zero unresolved placeholder markers (`DOC-006`) and zero broken internal links (`DOC-005`).
4. Any temporary exception to a waivable rule follows the [audited waiver process](docs/how-to/request-an-audited-waiver.md) backed by an ADR and an expiration date <= 90 days.

## Further Reading

- [Onboarding Tutorial](docs/tutorials/01-onboarding-and-running-the-gate.md)
- [Add a New Enforcement Rule](docs/how-to/add-a-new-enforcement-rule.md)
- [Enforcement Rules Catalog](docs/reference/enforcement-rules.md)
