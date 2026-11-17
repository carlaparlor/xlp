# XLP Research Archive

Every architecturally significant decision, DSP module, host adapter, modding runtime, and XLP plugin MUST be grounded in a peer-verifiable Research Dossier stored in this directory before implementation is merged.

## Standards

All research dossiers conform to the `RES-001` through `RES-004` enforcement rules verified by `xlp-gate`:

- Structured YAML frontmatter binding the dossier to concrete ADRs and XLP components.
- Eight mandatory technical sections with substantive depth.
- Verifiable external primary references with bidirectional inline citation matching (no uncited bibliography entries and no dangling citation numbers).

## Index

| ID | Title | Status | Scope | Related ADRs |
| --- | --- | --- | --- | --- |
| [RES-0001](RES-0001-vst3-clap-plugin-architecture.md) | VST3 3.8, CLAP, and Modular Multi-Format Audio Plugin Architecture | verified | plugin-architecture | [ADR-0002](../adr/ADR-0002-modular-layered-plugin-topology.md) |
| [RES-0002](RES-0002-realtime-audio-safety-and-testing.md) | Real-Time Audio Safety, RTSan, and Multi-Tier DSP Verification | verified | realtime-and-testing | [ADR-0003](../adr/ADR-0003-realtime-safety-and-verification-contract.md) |
| [RES-0003](RES-0003-moddable-extensible-audio-architectures.md) | Extensible and Moddable Audio Plugin Architectures and Sandboxing | verified | extensibility-moddability | [ADR-0004](../adr/ADR-0004-moddability-and-extensibility-contract.md) |
| [RES-0004](RES-0004-architectural-fitness-enforcement.md) | Architectural Fitness Functions, MADR 4.0, and Diátaxis Governance | verified | governance-enforcement | [ADR-0001](../adr/ADR-0001-xlp-governance-enforcement-gate.md), [ADR-0005](../adr/ADR-0005-research-and-documentation-standards.md) |
