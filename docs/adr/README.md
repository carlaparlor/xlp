# XLP Architecture Decision Records (ADRs)

Every architecturally significant decision across the XLP plugin suite is recorded here using MADR 4.0 format with mandatory `research_refs` and machine-verified `enforced_by` bindings into `xlp-gate`.

## Lifecycle

- `proposed` — under active design review.
- `accepted` — binding architectural law; every entry in `enforced_by` must map to a live `xlp-gate` rule (`DOC-002`).
- `deprecated` / `superseded` — replaced by a newer accepted ADR.

## Index

| ID | Title | Status | Research Refs | Enforced By |
| --- | --- | --- | --- | --- |
| [ADR-0001](ADR-0001-xlp-governance-enforcement-gate.md) | Adopt `xlp-gate` as the Mandatory Architectural Fitness Engine | accepted | RES-0004 | BRD-001, GOV-001..004, TST-004 |
| [ADR-0002](ADR-0002-modular-layered-plugin-topology.md) | Enforce Strict Five-Layer Modular Plugin Topology | accepted | RES-0001, RES-0004 | BRD-002, BRD-003, MOD-001..006 |
| [ADR-0003](ADR-0003-realtime-safety-and-verification-contract.md) | Mandate Static and Runtime Real-Time Safety and Multi-Tier Testing | accepted | RES-0002 | SCA-001..004, TST-001..003 |
| [ADR-0004](ADR-0004-moddability-and-extensibility-contract.md) | Mandate SemVer Extension Points and Sandboxed Moddability for All XLP Plugins | accepted | RES-0003 | EXT-001..004, MDD-001..004 |
| [ADR-0005](ADR-0005-research-and-documentation-standards.md) | Enforce Ruthless Research Dossiers, MADR 4.0, and Diátaxis Documentation | accepted | RES-0004 | RES-001..004, DOC-001..006 |
