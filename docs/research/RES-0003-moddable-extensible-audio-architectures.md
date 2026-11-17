---
id: RES-0003
title: Extensible and Moddable Audio Plugin Architectures and Sandboxing
status: verified
date: 2026-11-15
scope: extensibility-moddability
confidence: high
last_verified: 2026-11-15
related_adrs:
  - ADR-0004
related_components:
  - xlp.tools.xlp_gate
---

# RES-0003: Extensible and Moddable Audio Plugin Architectures and Sandboxing

## Problem & Research Questions

Every XLP plugin must be extensible by core developers without architectural rewrites and genuinely moddable by end users and third-party creators without jeopardizing DAW stability or real-time audio safety. This dossier investigates: How do successful open-source audio ecosystems enable deep user moddability (skins, modulation scripts, custom DSP nodes, microtunings, presets)? How can plugin ABI and parameter schemas evolve across versions without corrupting saved DAW sessions? What sandboxing and fault-isolation boundaries prevent a malformed or malicious third-party mod pack from crashing the host or stalling the audio thread? And how should mod conflict resolution and hot-reload contracts be standardized across all XLP plugins [1][2][3][4]?

## Prior Art & Industry Standards

Surge XT provides an instructive industry benchmark for user-extensible audio plugins: it supports swappable visual skins and color themes, a category-based preset browser, microtuning scales, a Lua-scripted formula modulator allowing users to author custom modulation shapes, and a modular decomposition of its entire DSP engine into 36+ standalone VCV Rack modules communicating via standardized polyphonic control signals [1][2]. In parallel, the CLAP plugin standard models extensibility through immutable, version-qualified extension identifiers (`clap/<extension>` with explicit semantic/ABI versioning) queried dynamically at runtime rather than brittle monolithic inheritance hierarchies [3]. WebAssembly (`wasmtime` / AudioWorklet) and FAUST-compiled DSP modules further demonstrate how user-authored signal graphs can run inside memory-isolated sandboxes with bounded execution cost and deterministic numeric output [4].

## Technical Deep Dive

XLP separates **developer extensibility** from **end-user moddability** while unifying both under machine-validated JSON contracts:

1. **Developer Extensibility (`EXT-001`..`EXT-004`)**:
   - Every module and plugin exposes explicit SemVer `version`, `api_version`, and integer `abi_version` fields alongside a `stability` tier (`experimental`, `beta`, `stable`).
   - Plugins declare named `extension_points` (e.g., `dsp.stages`, `modulation.sources`, `ui.widgets`, `presets.serializers`), each binding an interface contract name, SemVer version, and lifecycle phase (`compile_time`, `init`, `runtime`, `hot_reload`) [3].
   - Plugin parameters are defined declaratively in `params.json` (`governance/schemas/params.schema.json`) with stable string `id`, immutable 32-bit `uid`, valid numeric bounds (`min <= default <= max`), automation/modulation flags, and human-readable descriptions. State snapshots carry an integer `state_schema_version` plus an explicit `migration_strategy`, and baseline snapshots (`governance/baselines/<component>.params.json`) prevent silent parameter deletion or UID reassignment that would break DAW project recall.
2. **End-User Moddability (`MDD-001`..`MDD-004`)**:
   - Every XLP plugin must enable `modding` with at least two concrete mod surfaces drawn from a standardized taxonomy: `themes`, `presets`, `macros`, `dsp_graph`, `scripts`, `wavetables`, `impulse_responses`, `modulation_curves`, and `tunings` [1][2].
   - Every mod surface explicitly declares its execution sandbox (`declarative_schema`, `lua_sandbox`, or `wasm_sandbox`), hard prohibitions (`allow_filesystem: false`, `allow_network: false`), real-time enforcement flag (`rt_safe_enforced`), deterministic CPU (`cpu_budget_us`) and memory (`memory_limit_kb`) ceilings, and a non-crashing `fallback_on_error` policy (`bypass_mod_and_warn`, `revert_default`, or `disable_mod_safely`) [4].
   - Load-order determinism is guaranteed via `conflict_resolution` (`deterministic_priority` or `explicit_load_order`) paired with integer `priority` fields in `mod.manifest.json`.

## Comparative Trade-offs

| Mod Execution Sandbox | Real-Time Audio Suitability | Security & Isolation | Authoring Ergonomics | Performance Overhead |
| --- | --- | --- | --- | --- |
| Declarative JSON/Schema (`declarative_schema`) | Excellent (parsed off-thread, immutable RT snapshot) | Very High (no arbitrary code execution) | High (easy tooling & themes/macros/graphs) | Zero on audio thread |
| Sandboxed Lua (`lua_sandbox`, e.g., Surge XT formula mod) [1] | Good for control-rate modulation with instruction-count budgets | High (restricted stdlib, zero `os`/`io` libraries) | High (concise scripting syntax) | Low (bounded VM ticks) |
| Sandboxed WebAssembly (`wasm_sandbox`) [4] | High (near-native AOT/JIT linear memory isolation) | Very High (capability-based WASI disabled) | Medium (requires compiler toolchain) | Low (1.1x–1.5x native) |
| Native C++ Shared Library (`.so`/`.dll`) | High | Poor (arbitrary memory corruption crashes entire DAW) | Low (ABI & OS matrix burden) | Zero |

XLP deliberately excludes unsandboxed native dynamic libraries from user-facing mod surfaces: third-party mods must run through `declarative_schema`, `lua_sandbox`, or `wasm_sandbox` so a buggy user mod can never dereference invalid memory or bring down a musician's DAW session [1][4].

## Benchmarks & Empirical Evidence

Surge XT demonstrates in production across macOS, Windows, and Linux DAWs that theme/skin overrides and sandboxed Lua modulation scripts operate reliably inside commercial hosts when evaluated with strict per-block execution caps and off-thread parsing [1]. Similarly, FAUST-to-WASM audio runtimes confirm deterministic bit-identical audio output inside per-voice isolated memory regions [4]. To verify moddability empirically rather than aspirationally, XLP requires every plugin to ship at least one valid **reference mod pack** (`reference_mod_path`) validated against `mod.manifest.schema.json` (`MDD-003`) and exercised by automated `mod_loading` tests (`TST-002`), including fault-injection tests confirming graceful fallback on malformed mods.

## Risks, Edge Cases & Failure Modes

- **Silent DAW Project Corruption**: Changing a parameter's 32-bit `uid`, semantic range, or removing a parameter ID across minor releases silently corrupts saved DAW automation lanes; prevented by `EXT-003` and `EXT-004` baseline regression locking.
- **Runaway Mod Loops**: An infinite loop inside a Lua or WASM mod script will freeze the audio callback unless hard instruction/fuel limits (`cpu_budget_us`) abort the script and trigger `fallback_on_error` [1][4].
- **Privilege Escalation via Mod Packs**: A community-downloaded preset/theme pack must never read local disk paths (`../` traversal) or open network sockets; prevented by enforcing `allow_filesystem: false` and `allow_network: false` on every mod surface (`MDD-002`) and validating requested capabilities in `mod.manifest.json` (`MDD-003`).
- **Non-Deterministic Mod Stacking**: Two mods modifying the same UI token or macro mapping produce unpredictable results if load order depends on OS directory traversal; prevented by mandatory `conflict_resolution` and explicit numeric `priority`.

## Recommendations & Architectural Implications

1. Enforce SemVer `version`/`api_version`, integer `abi_version`, and >= 2 declared `extension_points` on every plugin (`EXT-001`, `EXT-002`).
2. Require declarative `params.json` schemas with unique immutable parameter IDs/UIDs and baseline drift checks (`EXT-003`, `EXT-004`).
3. Mandate `modding.enabled: true`, >= 2 sandboxed mod surfaces with `allow_filesystem: false` and `allow_network: false`, non-crashing error fallbacks, a valid bundled reference mod pack, and a complete `docs/modding.md` for every XLP plugin (`MDD-001`..`MDD-004`), with `MDD-002` designated non-waivable.

## References

1. KVR Audio / Surge Synth Team, *Surge XT Architecture — Lua Formula Modulator, Scenes, and Multi-Format Support* — https://www.kvraudio.com/product/surge-xt-by-surge-synth-team
2. Surge Synth Team, *Surge XT VCV Rack Modules Manual — Modular Decomposition, Modulation Matrix, and Skins* — https://surge-synthesizer.github.io/rack_xt_manual/
3. Free Audio / CLAP Maintainers, *CLAP ABI and Versioned Extension Architecture* — https://github.com/free-audio/clap
4. GRAME / FAUST Community, *Powered By Faust — Sandboxed WASM Voice Execution and Modular DSP Graphs* — https://faust.grame.fr/community/powered-by-faust/
