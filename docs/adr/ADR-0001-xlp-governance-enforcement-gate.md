---
id: ADR-0001
title: Adopt xlp-gate as the Mandatory Architectural Fitness Engine
status: accepted
date: 2026-11-15
deciders:
  - xlp-architecture
research_refs:
  - RES-0004
enforced_by:
  - BRD-001
  - GOV-001
  - GOV-002
  - GOV-003
  - GOV-004
  - TST-004
---

# ADR-0001: Adopt xlp-gate as the Mandatory Architectural Fitness Engine

## Context and Problem Statement

The XLP plugin ecosystem requires strict adherence to modular, scalable, extensible, and moddable engineering standards alongside ruthless research, testing, and documentation practices. Prose guidelines alone reliably erode across sessions and contributors. Which automated enforcement mechanism should XLP adopt before any audio plugin code is authored so that architectural invariants are verified continuously and cannot be silently bypassed?

## Decision Drivers

- Zero-dependency portability across developer machines, CI runners, and air-gapped sandboxes.
- Audio-plugin domain specificity (VST3 brand/UIDs, real-time audio safety, mod sandboxes, parameter immutability, research citations).
- Defense-in-depth enforcement across CLI, local Git hooks (`pre-commit`, `commit-msg`, `pre-push`), and GitHub Actions CI.
- Anti-tampering protections preventing silent weakening of thresholds or removal of adversarial tests.
- Controlled, time-boxed, ADR-backed waivers for non-constitutional exceptions so developers never reach for `--no-verify`.

## Considered Options

1. Repository-owned zero-dependency Python 3.11+ fitness engine (`xlp-gate`) backed by JSON Schemas, Git hooks, and CI.
2. Composite patchwork of third-party linters (ESLint, Ruff, Clang-Tidy, custom bash glue).
3. Manual pull-request checklists documented in `CONTRIBUTING.md`.

## Decision Outcome

Chosen option: Option 1 (`xlp-gate` repository-owned Python 3.11+ fitness engine), because it provides deterministic, audio-domain-specific architectural fitness enforcement with zero third-party runtime dependencies, complete rule-to-test traceability, and self-enforcing dogfooding from day one.

## Consequences

- Positive: Every architectural invariant is executed deterministically locally and in CI with machine-readable JSON reports and clear remediation output.
- Positive: `xlp-gate` is itself governed as a first-class modular component (`tools/xlp_gate/module.manifest.json`) with full adversarial test coverage.
- Negative: Maintaining the built-in JSON Schema validator and rule modules adds internal tooling code that must remain concise and well-tested.
- Neutral: Adding or relaxing any rule requires updating `governance/policy.json`, `governance/traceability.json`, `docs/reference/enforcement-rules.md`, and adversarial tests together.

## Confirmation

Compliance is verified continuously by:

- `./xlp-gate check --strict --run-tests` executing rules `BRD-001`, `GOV-001`, `GOV-002`, `GOV-003`, `GOV-004`, and `TST-004`.
- `.githooks/pre-commit`, `.githooks/commit-msg`, and `.githooks/pre-push` installed via `scripts/install-hooks.sh`.
- `.github/workflows/xlp-gate.yml` executing strictly on every push and pull request with zero `continue-on-error` flags.
- `tools/xlp_gate/tests/test_self_dogfood.py` verifying zero-violation self-compliance and 100% rule-to-doc-to-test parity.

## Pros and Cons of the Options

### Option 1: Repository-owned Python 3.11+ fitness engine (`xlp-gate`)

- Good, because Python 3.11+ standard library runs out of the box on Linux, macOS, and Windows without package manager drift.
- Good, because audio-specific checks (RT-safety, VST3 manifest contracts, mod sandboxes, research citation integrity) share one unified rule registry and report format.
- Bad, because the team owns maintenance of the built-in schema validator and check modules.

### Option 2: Composite third-party linter patchwork

- Good, because individual off-the-shelf tools cover narrow syntax checks.
- Bad, because no third-party linter validates MADR `enforced_by` bindings, research citation integrity, XLP mod sandboxes, or cross-language layer boundaries cleanly.
- Bad, because external dependencies complicate reproducible offline execution.

### Option 3: Manual pull-request checklists

- Good, because there is zero upfront engineering time.
- Bad, because unenforced prose policies inevitably drift and fail silently under time pressure.
