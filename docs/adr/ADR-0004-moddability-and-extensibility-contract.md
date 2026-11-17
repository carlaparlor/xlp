---
id: ADR-0004
title: Mandate SemVer Extension Points and Sandboxed Moddability for All XLP Plugins
status: accepted
date: 2026-11-15
deciders:
  - xlp-architecture
research_refs:
  - RES-0003
enforced_by:
  - EXT-001
  - EXT-002
  - EXT-003
  - EXT-004
  - MDD-001
  - MDD-002
  - MDD-003
  - MDD-004
---

# ADR-0004: Mandate SemVer Extension Points and Sandboxed Moddability for All XLP Plugins

## Context and Problem Statement

Every XLP plugin must be architected to be both extensible by developers over long product lifecycles and moddable by musicians and community creators. Without explicit contracts, extensibility degenerates into brittle ad-hoc forks, parameter edits break saved DAW sessions, and third-party mods crash hosts or introduce security vulnerabilities. What machine-enforced contracts must govern extensibility, ABI/parameter stability, and moddability across all XLP plugins?

## Decision Drivers

- Backwards-compatible DAW session recall via immutable parameter IDs/UIDs and versioned state migrations.
- Explicit, versioned extension points enabling modular growth without modifying core engines.
- First-class user moddability (themes, presets, macros, DSP graphs, sandboxed scripts, wavetables, tunings) with deterministic load ordering.
- Hard security and real-time fault isolation: third-party mods must never access filesystem/network or crash the host audio thread.

## Considered Options

1. Schema-enforced SemVer API/ABI contracts, declarative parameter registries with baseline drift guards, and mandatory sandboxed mod surfaces backed by bundled reference mods (`EXT-001`..`EXT-004`, `MDD-001`..`MDD-004`).
2. Unsandboxed native C++ plugin-of-a-plugin DLL loading for mods.
3. Optional ad-hoc modding added per plugin after release.

## Decision Outcome

Chosen option: Option 1 (Schema-enforced SemVer extensibility and mandatory sandboxed moddability), because treating extensibility and moddability as non-optional architectural contracts guarantees every XLP plugin ships with safe, documented, tested extension and modding surfaces from version 0.1.0 onward.

## Consequences

- Positive: Every XLP plugin declares at least two versioned extension points and two sandboxed mod surfaces (`declarative_schema`, `lua_sandbox`, or `wasm_sandbox`) with `allow_filesystem: false`, `allow_network: false`, bounded CPU/memory limits, and safe non-crashing fallbacks.
- Positive: Parameter schemas (`params.json`) and baseline snapshots prevent accidental DAW automation breakage across releases.
- Positive: Requiring a validated reference mod pack (`MDD-003`) and `docs/modding.md` (`MDD-004`) ensures moddability is verified end-to-end rather than left theoretical.
- Negative: Initial plugin creation requires designing parameter schemas, extension interfaces, and a reference mod fixture upfront.
- Neutral: Mod packs carry explicit integer priorities and target `mod_api_version` constraints for deterministic conflict resolution.

## Confirmation

Compliance is verified continuously by `xlp-gate` rules:

- `EXT-001`..`EXT-004`: SemVer API/ABI declarations, >= 2 plugin extension points, validated `params.json` with immutable UID/range integrity, and baseline parameter drift checks.
- `MDD-001`, `MDD-002` (non-waivable), `MDD-003`, `MDD-004`: Mandatory plugin modding declaration, hard sandbox/fallback guarantees, schema-validated mod packs including a bundled reference mod per plugin, and complete `docs/modding.md`.

## Pros and Cons of the Options

### Option 1: Schema-enforced SemVer extensibility and sandboxed moddability

- Good, because DAW crash isolation and security boundaries are guaranteed structurally and verified in CI.
- Good, because musicians get a consistent, discoverable mod pack format across the entire XLP suite.
- Bad, because custom native C++ mod binaries are disallowed in favor of declarative, Lua, or WASM sandboxes.

### Option 2: Unsandboxed native DLL mods

- Good, because mods have unrestricted raw C++ speed.
- Bad, because a single null pointer dereference crashes the user's DAW and exposes full OS filesystem/network privileges to untrusted downloads.

### Option 3: Post-release optional modding

- Good, because early releases skip mod infrastructure.
- Bad, because retrofitting clean mod surfaces onto tightly coupled DSP/UI internals almost always forces a rewrite and violates the XLP brand mandate.
