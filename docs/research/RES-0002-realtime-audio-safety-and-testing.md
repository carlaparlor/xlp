---
id: RES-0002
title: Real-Time Audio Safety, RTSan, and Multi-Tier DSP Verification
status: verified
date: 2026-11-15
scope: realtime-and-testing
confidence: high
last_verified: 2026-11-15
related_adrs:
  - ADR-0003
related_components:
  - xlp.tools.xlp_gate
---

# RES-0002: Real-Time Audio Safety, RTSan, and Multi-Tier DSP Verification

## Problem & Research Questions

A real-time audio callback operating at 48 kHz with a 64-sample buffer has a hard deadline of 1.333 milliseconds to compute all DSP nodes and return without glitching. Even a single hidden heap allocation, mutex contention, console write, or denormal floating-point stall can trigger an audible buffer underrun (dropout) in a DAW. XLP must answer: Which operations are strictly forbidden on the audio thread? How can real-time safety be enforced both statically (before code compiles or merges) and dynamically (at test execution time)? And what multi-tier testing regimen guarantees DSP correctness, host compatibility, and regression stability across every XLP plugin [1][2][4]?

## Prior Art & Industry Standards

Ross Bencina's canonical specification of real-time audio programming establishes the non-negotiable baseline: audio callbacks must never allocate or free memory, acquire blocking locks, perform filesystem or console I/O, invoke blocking OS syscalls, spawn or sleep threads, or execute algorithms with unbounded worst-case execution time [1]. Instead, all memory must be pre-allocated during non-real-time preparation (`prepare` / `activate`), and communication between the audio thread and UI/control threads must use lock-free atomics or single-producer single-consumer (SPSC) ring buffers [1].

In 2024–2026, LLVM/Clang introduced **RealtimeSanitizer (RTSan)** (`-fsanitize=realtime`) paired with Clang function-effect attributes (`[[clang::nonblocking]]` and `[[clang::nonallocating]]`) [2][3]. RTSan intercepts allocator, mutex, thread, and syscall boundaries at runtime and aborts tests with full stack traces whenever an audio-thread code path transitively invokes a blocking call—even through layers of standard-library container inlining [2][3]. At the host-integration tier, the audio industry relies on Tracktion's `pluginval` (at strictness level 5 or higher, which also invokes Steinberg's VST3 validator and Apple's `auval`), Steinberg's standalone VST3 `validator`, and `clap-validator` to fuzz parameter sweeps, bus layouts, state save/restore, thread safety, and silence/denormal handling [4][5].

## Technical Deep Dive

Effective real-time safety enforcement requires defense in depth across three complementary verification tiers:

1. **Tier 1 — Static Gate Enforcement (`SCA-001` & `SCA-002`)**: Before any code is committed or merged, static scanning over `dsp/`, `realtime/`, and `audio_thread/` source files catches obvious violations immediately: `malloc`/`free`/`new`/`delete`/`std::make_unique`/`std::make_shared`, `std::mutex`/`lock_guard`/`pthread_mutex_lock`, `printf`/`std::cout`/`fopen`/`std::fstream`, `std::thread`/`sleep_for`, `throw`, and dynamic container growth (`.push_back`, `.resize`, `.emplace_back`). Legitimate pre-allocation inside lifecycle methods (`prepare`, `prepareToPlay`, `activate`, `releaseResources`) or explicit `XLP_NON_RT_BEGIN`/`XLP_NON_RT_END` regions is cleanly scoped and audited while processing paths remain airtight [1].
2. **Tier 2 — Dynamic Sanitizer & DSP Invariant Suite**: Compiled DSP modules execute headless tests covering:
   - **RTSan / Allocator Trap**: Running `process()` annotated with `[[clang::nonblocking]]` under `-fsanitize=realtime` (plus ASan/UBSan/TSan sweeps) [2][3].
   - **Numerical & Signal Invariants**: Zero-input silence stability, DC-offset rejection, NaN/Inf/subnormal (denormal) immunity, impulse & step response stability, frequency/phase verification, and sample-rate (44.1 / 48 / 88.2 / 96 / 192 kHz) plus arbitrary block-size (1, 7, 16, 64, 128, 513, 4096 samples) invariance.
   - **Randomized Parameter & Automation Fuzzing**: Sweeping parameters at sample-accurate boundaries without clicks, NaNs, or assertion failures.
3. **Tier 3 — Host Conformance Validation**: Built VST3 binaries run under `pluginval --strictness-level 5 --skip-gui-tests` and Steinberg's VST3 `validator` (and `clap-validator` when CLAP is enabled) in CI, verifying state serialization round-trips, latency reporting, tail reporting, and rapid activate/deactivate cycles [4][5].

## Comparative Trade-offs

| Verification Technique | Catches Hidden STL Allocations | Zero Build-Time Dependency | Catches DAW Protocol Bugs | Execution Cost |
| --- | --- | --- | --- | --- |
| Static RT-Safety Linter (`SCA-001`) | Partial (direct calls & container growth) | Yes (pure Python, runs in pre-commit) | No | Milliseconds |
| Clang RTSan (`-fsanitize=realtime`) [2][3] | Yes (full transitive call graph) | No (requires Clang compiler-rt build) | No | Seconds (CI test suite) |
| Headless DSP Invariant & Fuzz Tests | No | No (requires native test binary) | Partial | Seconds |
| `pluginval` (strictness >= 5) + VST3 validator [4][5] | Indirectly (timeout/crash checks) | No (requires compiled `.vst3` bundle) | Yes | Tens of seconds |

Because no single tool catches every failure class, XLP mandates all four layers cumulatively: static linting on every commit (`SCA-001`), declared RT contracts in manifests (`SCA-002`), required test categories per layer (`TST-002`), and live test execution in CI and `pre-push` (`TST-003`).

## Benchmarks & Empirical Evidence

LLVM's RealtimeSanitizer specification documents near-zero runtime overhead on compliant real-time paths when compiled with `-fsanitize=realtime`, making continuous CI execution practical without distorting timing behavior [3]. Tracktion's `pluginval` strictness level 5 is the industry-recommended minimum for DAW host compatibility and automatically chains Steinberg's official VST3 validator and macOS `auval` [4]. Sonore SDK's production CI workflow validates that combining headless DSP measurement tests, ASan/UBSan/TSan sanitizers, and `pluginval`/`clap-validator` catches host regressions prior to DAW testing [5]. XLP enforces a quantitative baseline protocol: every DSP module and plugin must declare `max_cpu_percent_single_core_48k_64buf`, `max_memory_mb`, and `max_latency_samples` in its manifest and back them with a named `benchmark_target` (`SCA-003`).

## Risks, Edge Cases & Failure Modes

- **Transitive Allocation Blind Spot**: Static regex/AST checks cannot detect an allocation hidden inside a third-party helper function; therefore `SCA-001` is strictly paired with mandatory `rt_safety` runtime tests (`TST-002`) using RTSan or global `operator new` traps [2][3].
- **Denormal CPU Spikes**: Decaying IIR filter tails can drop into IEEE-754 subnormal floats, causing 10x–100x CPU spikes on x86 processors if FTZ/DAZ (Flush-To-Zero / Denormals-Are-Zero) or anti-denormal DC offsets are omitted; `denormal_protection: true` is enforced in every RT contract (`SCA-002`).
- **Variable Host Buffer Sizes**: Hosts such as FL Studio and Ableton Live routinely pass non-power-of-two, 1-sample, or mid-block split buffers; assuming power-of-two blocks crashes or corrupts FFT/delay lines.
- **Multi-Bus `pluginval` Edge Case**: Known `pluginval` limitations on complex multi-bus VST3 plugins require pairing `pluginval` with Steinberg's official VST3 `validator` directly [4].

## Recommendations & Architectural Implications

1. Implement a scope-aware static RT-safety analyzer (`SCA-001`) directly inside `xlp-gate` and mark it as a **non-waivable** constitutional rule.
2. Mandate explicit `realtime_contract` and `performance_budget` declarations in all DSP module and plugin manifests (`SCA-002`, `SCA-003`), verifying `audio_thread_lock_free: true`, `audio_thread_alloc_free: true`, `denormal_protection: true`, `arbitrary_block_sizes: true`, and lock-free thread communication.
3. Enforce layer-specific required test categories (`dsp_invariants`, `rt_safety`, `regression`, `fuzz`, `state_roundtrip`, `host_validation`) via `TST-002` and execute declared test commands live via `TST-003`.

## References

1. Ross Bencina, *Real-Time Audio Programming 101: Time Waits for Nothing* — http://www.rossbencina.com/code/real-time-audio-programming-101-time-waits-for-nothing
2. WroCpp, *RealtimeSanitizer Checks the Promise That a Function Never Blocks* — https://wrocpp.github.io/posts/verification-realtime-sanitizer/
3. LLVM / Clang Project, *RealtimeSanitizer (RTSan) Codegen and Driver Documentation (PR #102622)* — https://www.mail-archive.com/cfe-commits@lists.llvm.org/msg465828.html
4. Tracktion, *pluginval — Cross-Platform Audio Plugin Validator Releases & Strictness Levels* — https://github.com/Tracktion/pluginval/releases
5. SonorieAI, *Sonore SDK — Multi-Tier Sanitizer and Validator CI Architecture* — https://github.com/SonorieAI/sonore-sdk
