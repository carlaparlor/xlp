---
id: ADR-0002
title: Enforce Strict Five-Layer Modular Plugin Topology
status: accepted
date: 2026-11-15
deciders:
  - xlp-architecture
research_refs:
  - RES-0001
  - RES-0004
enforced_by:
  - BRD-002
  - BRD-003
  - MOD-001
  - MOD-002
  - MOD-003
  - MOD-004
  - MOD-005
  - MOD-006
---

# ADR-0002: Enforce Strict Five-Layer Modular Plugin Topology

## Context and Problem Statement

XLP is a brand for a multi-plugin audio software line targeting VST3 (with optional CLAP, AU, LV2, and standalone builds). Without strict structural boundaries, audio plugins rapidly degenerate into framework-coupled monoliths where DSP math directly references GUI widgets or DAW format headers, making reuse impossible and testing brittle. How should XLP organize components and enforce dependency boundaries across the repository?

## Decision Drivers

- Clean reuse of DSP, parameter, state, and UI building blocks across multiple XLP plugins.
- Headless testability of all DSP engines without GUI toolkits or DAW host SDKs.
- Zero format lock-in: VST3 (SDK >= 3.8.0 MIT), CLAP, AU, and LV2 remain replaceable thin adapters.
- Prevention of circular dependencies, undeclared coupling, cross-plugin private imports, and monolithic god-files.

## Considered Options

1. Strict five-layer acyclic monorepo (`core/`, `modules/`, `adapters/`, `plugins/`, `mods/`) with manifest-backed dependency verification.
2. Flat per-plugin repositories duplicating DSP and adapter scaffolding across each plugin.
3. Single shared library where DSP, UI, and VST3/JUCE code share headers freely.

## Decision Outcome

Chosen option: Option 1 (Strict five-layer acyclic monorepo topology), because it guarantees clean separation of DSP, UI, host adapters, plugins, and user mods while allowing automated static enforcement of layer direction, acyclicity, and manifest parity.

## Consequences

- Positive: Pure DSP modules in `core/` and `modules/` compile and test headlessly in milliseconds without host or GUI dependencies.
- Positive: Cross-plugin capabilities are automatically promoted to reusable modules instead of copy-pasted.
- Positive: Brand identity (`xlp_*` directory names, `xlp.*` IDs, unique 4-char codes, distinct VST3 component/controller UUIDs) stays collision-free across the entire XLP line.
- Negative: Every new component requires a manifest file (`module.manifest.json` or `plugin.manifest.json`) declaring its explicit dependencies.
- Neutral: Source files are capped at 600 lines (`MOD-006`) to encourage cohesive modular decomposition.

## Confirmation

Compliance is verified continuously by `xlp-gate` rules:

- `BRD-002` and `BRD-003`: Plugin and module naming, `xlp` brand identity, unique 4-char plugin codes, and distinct VST3 component/controller UIDs.
- `MOD-001`: Schema validation of every component manifest across all layers.
- `MOD-002`, `MOD-003`, `MOD-004`: Allowed layer dependency matrix, zero circular dependencies (DAG), and 100% parity between source imports and manifest `dependencies`.
- `MOD-005` and `MOD-006`: Strict DSP/UI/adapter separation and source file line-count ceilings.

## Pros and Cons of the Options

### Option 1: Strict five-layer acyclic monorepo

- Good, because all shared DSP primitives live in one versioned dependency graph with deterministic boundary enforcement.
- Good, because format adapters remain thin shells easily extended from VST3 to CLAP/AU/LV2.
- Bad, because engineers must explicitly register dependencies in component manifests.

### Option 2: Flat per-plugin repositories

- Good, because each plugin builds independently.
- Bad, because shared DSP and mod-runtime fixes fragment across repositories and governance drift multiplies.

### Option 3: Unconstrained shared library

- Good, because initial prototyping is marginally faster.
- Bad, because GUI and host SDK types leak into DSP code, destroying headless testing and portability.
