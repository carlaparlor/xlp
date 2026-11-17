---
id: RES-0004
title: Architectural Fitness Functions, MADR 4.0, and Diátaxis Governance
status: verified
date: 2026-11-15
scope: governance-enforcement
confidence: high
last_verified: 2026-11-15
related_adrs:
  - ADR-0001
  - ADR-0005
related_components:
  - xlp.tools.xlp_gate
---

# RES-0004: Architectural Fitness Functions, MADR 4.0, and Diátaxis Governance

## Problem & Research Questions

Architectural intentions recorded only in prose documents inevitably decay under schedule pressure—a phenomenon well documented as architectural drift. Before writing a single audio plugin, XLP must construct a strict enforcement mechanism capable of governing modularity, scalability, extensibility, moddability, research rigor, testing rigor, and documentation completeness automatically. This dossier investigates: How do evolutionary architectural fitness functions turn design decisions into deterministic build gates? How should Architecture Decision Records (ADRs) be structured so every decision is bound to an automated check? How should long-form technical documentation be organized to prevent structural chaos? And how do we verify that the enforcement rules themselves cannot pass vacuously or be silently weakened [1][2][3][4]?

## Prior Art & Industry Standards

Neal Ford, Rebecca Parsons, and Patrick Kua's *Building Evolutionary Architectures* formalizes **architectural fitness functions**: objective, automated checks evaluated continuously on every change to verify whether a codebase still satisfies its stated architectural invariants [1][2]. Contemporary architecture governance literature highlights a critical maxim: *"a decision nothing enforces is a wish"* [1]. To operationalize this maxim, mature teams pair **MADR 4.0** (Markdown Any Decision Records)—which extends Michael Nygard's classic Context/Decision/Consequences structure with YAML frontmatter, Decision Drivers, Considered Options, Pros/Cons, and an explicit Confirmation/Validation section—with an `enforced_by` binding pointing directly to concrete CI rule IDs [1][4].

For non-ADR documentation, the **Diátaxis** framework organizes technical documentation into four orthogonal quadrants based on reader need: **tutorials** (learning-oriented), **how-to guides** (task-oriented), **reference** (information-oriented lookup), and **explanation** (understanding-oriented context), keeping ADRs in a dedicated sibling directory [5]. Finally, architecture testing benchmarks (e.g., ArchUnit self-test suites) establish a crucial meta-invariant: every architectural rule must be tested **twice**—once against the real repository and once against deliberately broken **adversarial fixtures**—to prove the rule genuinely detects the violation it claims to enforce rather than passing vacuously [3].

## Technical Deep Dive

XLP's enforcement mechanism (`xlp-gate`) implements a five-layer defense-in-depth governance model:

1. **Machine-Readable Constitution (`governance/policy.json`)**: Centralizes all thresholds, layer dependency matrices, real-time forbidden patterns, required test categories, required doc sections, and constitutional floor invariants, validated against `governance/schemas/policy.schema.json` (`GOV-001`, `GOV-004`).
2. **Deterministic Fitness Engine (`tools/xlp_gate/`)**: Implemented in zero-dependency Python 3.11+ with a built-in Draft 2020-12 JSON Schema core validator and YAML frontmatter parser so it runs identically in air-gapped sandboxes, developer workstations, git hooks, and CI pipelines without external package installation drift.
3. **Bidirectional Traceability (`governance/traceability.json`)**: Maps 100% of registered rules (`BRD-*` through `GOV-*`) across four mandatory dimensions: parent ADR (`ADR-XXXX`), grounding research dossier (`RES-XXXX`), live check module, reference doc anchor (`docs/reference/enforcement-rules.md`), and named positive + adversarial test cases (`TST-004`, `DOC-004`).
4. **Defense-in-Depth Execution Points**:
   - Local `pre-commit` hook runs strict static checks; `commit-msg` validates Conventional Commits while preserving platform trailers; `pre-push` executes full checks plus live test suites (`GOV-002`).
   - GitHub Actions CI (`.github/workflows/xlp-gate.yml`) executes `./xlp-gate check --strict --run-tests` with zero `continue-on-error` bypasses.
5. **Audited Waiver Ledger (`governance/waivers.json`)**: Rather than encouraging developers to bypass hooks with `--no-verify`, temporary exceptions require a schema-validated waiver tied to an existing ADR, a >= 40-character justification, a strict <= 90-day expiration date, and cannot ever waive `non_waivable_rules` such as acyclic dependencies, RT-safety, mod sandboxing, test execution, or governance integrity (`GOV-003`).

## Comparative Trade-offs

| Governance Mechanism | Bypass Resistance | Zero-Dependency Portability | Audio-Domain Specificity | Maintenance Burden |
| --- | --- | --- | --- | --- |
| Prose guidelines (`CONTRIBUTING.md` only) | Very Low | High | High | Low (but ineffective) [1] |
| Generic linters (ESLint / Ruff / Clang-Tidy alone) | Medium | Medium | Low (no ADR, research, mod, or manifest checks) | Medium |
| Custom Python Fitness Engine (`xlp-gate`) + Hooks + CI [1][2][3] | Very High | Very High (stdlib Python 3.11+) | Exact (DSP RT-safety, VST3/mod/param schemas, research citations) | Low–Medium (self-tested) |

Preferring a small, repository-owned, adversarially self-tested fitness engine avoids brittle third-party plugin mismatches while allowing deterministic checks tailored directly to XLP's VST3/audio domain [2][3].

## Benchmarks & Empirical Evidence

Industry case studies on modular monoliths and agent-governed repositories confirm that deterministic fitness functions running in under two seconds locally prevent boundary drift before review, while adversarial fixture suites catch silent false-negative bugs in rule logic (such as overly narrow dependency checks that miss indirect imports) [2][3]. For `xlp-gate`, the empirical verification bar is: (1) full static suite runs in under 2 seconds on the repository, (2) 100% of registered rules have passing positive tests and passing adversarial negative tests verifying the exact `RULE-ID` fires on violation, and (3) `xlp-gate` dogfoods itself strictly with zero warnings and zero waivers.

## Risks, Edge Cases & Failure Modes

- **Vacuous Passes**: A rule inspecting `plugins/*` will trivially pass when zero plugins exist yet unless explicitly tested against synthetic compliant and broken plugin fixtures in `tools/xlp_gate/tests/` [3].
- **Silent Policy Weakening**: A contributor could lower `min_research_citations` to `0` or remove `SCA-001` from `non_waivable_rules` in `policy.json` to make a failing check pass; mitigated by hardcoded `constitutional_floors` verified inside `GOV-004` and CI anti-tampering tests.
- **Checkbox Citation Gaming**: An author might append fake URLs to `## References` without citing them, or insert empty headings; mitigated by `RES-002` bidirectional citation verification and `RES-003` per-section word minimums plus `DOC-006` forbidden placeholder detection.
- **Hook Erosion**: Git `.git/hooks/` files are not tracked by Git; mitigated by versioning hooks in `.githooks/`, providing `scripts/install-hooks.sh`, checking hook files in `GOV-002`, and enforcing identically in GitHub Actions CI.

## Recommendations & Architectural Implications

1. Build `xlp-gate` first—before any plugin code—and dogfood it on itself (`tools/xlp_gate/module.manifest.json`) so every subsequent commit is governed from day one (`ADR-0001`).
2. Enforce MADR 4.0 ADRs with mandatory `research_refs` and verified `enforced_by` rule IDs (`DOC-002`), Diátaxis documentation quadrants (`DOC-001`), link/anchor integrity (`DOC-005`), and zero placeholder debt (`DOC-006`) (`ADR-0005`).
3. Require bidirectional rule-to-doc parity (`DOC-004`) and rule-to-test traceability (`TST-004`) backed by adversarial fixtures proving every rule catches violations [3].

## References

1. Pharos Production, *Architecture Decision Records: Governance and Enforcement via Fitness Functions* — https://pharosproduction.com/insights/engineering/architecture-decision-records-governance/
2. InfoQ, *Agentic Fitness Functions: Extending Evolutionary Architecture Beyond Deterministic Rules* — https://www.infoq.com/articles/agentic-fitness-functions-evolutionary-architecture/
3. Skpandey15 / system-design-lab, *Modular Boundaries, ArchUnit Fitness Functions, and Deliberately-Broken Fixture Self-Tests (PR #1)* — https://github.com/Skpandey15/system-design-lab/pull/1
4. Olaf Zimmermann, *The Markdown ADR (MADR) Template Explained and Distilled* — https://www.ozimmer.ch/practices/2022/11/22/MADRTemplatePrimer.html
5. nwarila-platform, *ADR-0002: Adopt Diátaxis as the Documentation Framework* — https://github.com/nwarila-platform/rancher-terraform-framework/blob/main/docs/decision-records/org/0002-adopt-diataxis-documentation-framework.md
