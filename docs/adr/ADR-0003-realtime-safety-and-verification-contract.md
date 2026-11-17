---
id: ADR-0003
title: Mandate Static and Runtime Real-Time Safety and Multi-Tier Testing
status: accepted
date: 2026-11-15
deciders:
  - xlp-architecture
research_refs:
  - RES-0002
enforced_by:
  - SCA-001
  - SCA-002
  - SCA-003
  - SCA-004
  - TST-001
  - TST-002
  - TST-003
---

# ADR-0003: Mandate Static and Runtime Real-Time Safety and Multi-Tier Testing

## Context and Problem Statement

Real-time audio callbacks operate under strict sub-millisecond deadlines where heap allocations, locks, blocking syscalls, exceptions, or denormal stalls cause audible glitches or DAW crashes. At the same time, superficial unit tests fail to catch sample-rate bugs, arbitrary block-size assumptions, state-recall corruption, or host protocol violations. How should XLP guarantee scalability, real-time safety, and ruthless testing across every module and plugin?

## Decision Drivers

- Hard real-time determinism: zero allocations, zero locks, zero blocking I/O, and denormal safety on the audio thread.
- Predictable CPU, memory, and latency budgets across sample rates (44.1 / 48 / 96+ kHz) and arbitrary block sizes.
- Mandatory multi-tier testing tailored to each architectural layer (unit, DSP invariants, RT safety, regression, fuzz, state round-trip, mod loading, and host validation).
- Actual execution of declared test suites during enforcement gates rather than checking only that test files exist.

## Considered Options

1. Multi-tier enforcement combining scope-aware static RT-safety analysis (`SCA-001`), declared RT/performance/format contracts (`SCA-002`..`SCA-004`), required layer test categories (`TST-001`, `TST-002`), and live test execution (`TST-003`).
2. Runtime-only sanitizer checks run manually before releases.
3. Informal developer discipline with ad-hoc unit tests.

## Decision Outcome

Chosen option: Option 1 (Multi-tier static + contract + live multi-category testing enforcement), because catching blocking operations statically at commit time while enforcing runtime RT-safety, DSP invariant, fuzz, and host-validation suites eliminates both trivial mistakes and subtle transitive regressions.

## Consequences

- Positive: `SCA-001` blocks heap allocation, mutex locking, blocking I/O, thread sleeps, exceptions, and container growth inside audio-thread source files before code ever enters Git history.
- Positive: Every DSP module and plugin explicitly specifies its sample-rate, block-size, lock-free thread-communication, CPU, memory, and latency contracts.
- Positive: `TST-003` executes every component's real test suite in CI and `pre-push`, ensuring zero skipped or broken suites.
- Negative: Non-real-time setup functions inside `dsp/` files must follow named lifecycle conventions (`prepare`, `prepareToPlay`, `activate`) or explicit `XLP_NON_RT_BEGIN`/`XLP_NON_RT_END` markers so the static analyzer distinguishes initialization from processing.
- Neutral: Future native C++/Rust builds will pair `SCA-001` with Clang RealtimeSanitizer (`-fsanitize=realtime`), ASan/UBSan, and `pluginval` strictness >= 5.

## Confirmation

Compliance is verified continuously by `xlp-gate` rules:

- `SCA-001` (non-waivable): Scope-aware static RT-safety analysis on all audio-thread source files.
- `SCA-002`, `SCA-003`, `SCA-004`: Validation of `realtime_contract`, `performance_budget`, VST3 format targeting, and channel layout declarations.
- `TST-001`, `TST-002`, `TST-003` (non-waivable): Verification of test suites, required test categories per layer, and live zero-failure test execution.

## Pros and Cons of the Options

### Option 1: Multi-tier static, contract, and live test enforcement

- Good, because static RT checks run in milliseconds during `pre-commit` while dynamic tests catch deeper numerical and transitive issues.
- Good, because explicit performance and latency budgets make scalability measurable and auditable.
- Bad, because every component must maintain structured test metadata and comprehensive test suites from initial creation.

### Option 2: Runtime-only release testing

- Good, because commit hooks stay minimal.
- Bad, because RT violations and host regressions accumulate unnoticed until late integration.

### Option 3: Informal ad-hoc testing

- Good, because it requires no enforcement infrastructure.
- Bad, because audio edge cases (denormals, 1-sample blocks, NaNs, state recall) reliably ship to users.
