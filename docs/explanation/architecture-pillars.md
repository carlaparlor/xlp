# The Four XLP Architectural Pillars

Every XLP audio plugin is built upon four interconnected architectural pillars enforced continuously by `xlp-gate`.

## 1. Modular (`MOD-001`..`MOD-006`)

XLP separates every responsibility into five strict acyclic layers:

- **`core/`**: Host-agnostic, framework-agnostic math, lock-free queues, parameter registries, state serialization, DSP graph engines, and mod sandboxing primitives.
- **`modules/`**: Reusable DSP processors, modulators, filters, effects, and UI design tokens composed solely from `core/` and peer `modules/`.
- **`adapters/`**: Thin host format bindings (`vst3`, plus optional `clap`, `au`, `lv2`, `standalone`) translating host audio buffers, events, and state streams without containing DSP logic.
- **`plugins/`**: Concrete XLP products (`plugins/xlp_<slug>/`) combining `core/`, `modules/`, and `adapters/` while isolating `dsp/` from `ui/` and forbidding direct imports between sibling plugins.
- **`mods/`**: User-authored or reference mod packs interacting strictly with declared public plugin mod surfaces.

## 2. Scalable (`SCA-001`..`SCA-004`)

Audio software scales across polyphony, high sample rates (96–192 kHz), tiny latency buffers (32–64 samples), and dozens of concurrent DAW track instances only when real-time execution is strictly deterministic. XLP enforces lock-free, allocation-free, denormal-safe audio-thread contracts both statically (`SCA-001`) and via declared RT contracts and quantitative CPU/memory/latency budgets (`SCA-002`, `SCA-003`), while guaranteeing VST3 and multi-channel layout readiness (`SCA-004`).

## 3. Extensible (`EXT-001`..`EXT-004`)

Long-lived audio plugins evolve without breaking user projects or core code when extension boundaries are explicit and versioned. Every XLP component publishes semantic `version` and `api_version` strings, an integer `abi_version`, and explicit named `extension_points`. Plugin parameters live in declarative `params.json` files with immutable 32-bit `uid` identifiers protected against silent breaking removals by baseline regression snapshots (`EXT-004`).

## 4. Moddable (`MDD-001`..`MDD-004`)

Moddability is not an afterthought bolted onto finished plugins—it is a mandatory first-class surface on every XLP product. Every plugin exposes at least two sandboxed mod surfaces (`themes`, `presets`, `macros`, `dsp_graph`, `scripts`, `wavetables`, `impulse_responses`, `modulation_curves`, or `tunings`) running inside `declarative_schema`, `lua_sandbox`, or `wasm_sandbox` boundaries with filesystem and network disabled, deterministic priority conflict resolution, crash-safe error fallbacks, complete modding documentation, and a verified reference mod pack.
