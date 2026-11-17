# How to Create a Compliant XLP Plugin or Module

This guide walks through creating a new XLP plugin (`plugins/xlp_<slug>/`) or reusable module (`core/<name>/`, `modules/<name>/`, `adapters/<name>/`) that satisfies all 39 `xlp-gate` rules from the first commit.

## Step 1: Complete Grounding Research and Decisions First

Before scaffolding code, ensure the algorithm, host format, or modding surface is researched and decided:

```bash
./xlp-gate scaffold research filter-topology-analysis --title "Zero-Delay Feedback Filter Topologies"
./xlp-gate scaffold adr adopt-zdf-svf-core --title "Adopt Zero-Delay Feedback State-Variable Filter Core"
```

Complete all eight research sections with >= 3 verifiable primary references (`RES-001`..`RES-003`) and fill out all MADR 4.0 ADR sections (`DOC-002`).

## Step 2: Scaffold the Component Skeleton

For a reusable DSP module in `modules/`:

```bash
./xlp-gate scaffold module zdf_svf --layer modules --module-kind dsp
```

For a new XLP VST3 plugin in `plugins/`:

```bash
./xlp-gate scaffold plugin resonant_filter --category effect
```

The scaffolder generates:

- `plugin.manifest.json` or `module.manifest.json` pre-populated with unique UUIDs, SemVer API/ABI metadata, `realtime_contract`, `performance_budget`, `extension_points`, and `modding` surfaces.
- `params.json` with immutable `id` and `uid` fields (for plugins).
- Separated `dsp/` and `ui/` directories plus a bundled reference mod pack under `mods/reference_theme/` (for plugins).
- Required documentation files (`README.md`, `docs/architecture.md`, `docs/api.md`, `docs/testing.md`, and `docs/modding.md`).
- Starter contract test files annotated with every required `@category:` tag.

## Step 3: Implement Under Strict Boundaries

1. Keep DSP audio-thread code free of allocations, mutexes, blocking I/O, thread sleeps, throws, and container growth (`SCA-001`). Pre-allocate only inside `prepare()`/`prepareToPlay()`/`activate()` or explicit `XLP_NON_RT_BEGIN`..`XLP_NON_RT_END` blocks.
2. Never import UI headers into `dsp/`, never put DSP loops in `adapters/`, and never import across sibling `plugins/` (`MOD-002`, `MOD-005`).
3. Declare every cross-component dependency in the component's manifest (`MOD-004`).
4. Replace starter contract tests with thorough unit, DSP invariant, RT-safety, regression, fuzz, state round-trip, mod fault-isolation, and host validation suites (`TST-001`..`TST-003`).

## Step 4: Verify Strictly

```bash
./xlp-gate check --strict --run-tests
```

Commit only when `xlp-gate` exits with `0` and zero warnings.
