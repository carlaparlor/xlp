# XLP Enforcement Rules Reference

This document is the authoritative 1:1 specification of all 39 rules enforced by `xlp-gate`. Rule `DOC-004` strictly verifies that every registered rule appears below as a `### <RULE-ID>` heading and that zero obsolete rules remain.

## Brand & Identity (`BRD`)

### BRD-001

- **Title**: XLP Brand Specification Validity
- **Waivable**: No (constitutional)
- **Governing ADR**: [ADR-0001](../adr/ADR-0001-xlp-governance-enforcement-gate.md)
- **Check**: Verifies `governance/brand.json` exists, parses cleanly, and conforms strictly to `governance/schemas/brand.schema.json` with `brand_name == "xlp"`, valid 4-character `manufacturer_code`, and reverse-DNS prefix ending in `.xlp`.
- **Remediation**: Restore or fix `governance/brand.json` to satisfy `brand.schema.json`.

### BRD-002

- **Title**: XLP Plugin Identity & UID Uniqueness
- **Waivable**: Yes (ADR-backed)
- **Governing ADR**: [ADR-0002](../adr/ADR-0002-modular-layered-plugin-topology.md)
- **Check**: Verifies every plugin under `plugins/` uses `xlp_<slug>` directory naming, `id == "xlp.<slug>"`, `brand == "xlp"`, a globally unique 4-character alphanumeric `plugin_code`, and distinct globally unique 128-bit UUIDs for `vst3_component_uid` and `vst3_controller_uid`.
- **Remediation**: Rename the directory/ID to match `xlp_<slug>` / `xlp.<slug>` and assign unique `plugin_code` and UUID v4 identifiers.

### BRD-003

- **Title**: XLP Module Canonical Identifier Convention
- **Waivable**: Yes (ADR-backed)
- **Governing ADR**: [ADR-0002](../adr/ADR-0002-modular-layered-plugin-topology.md)
- **Check**: Verifies every component in `core/`, `modules/`, `adapters/`, and `tools/` declares `brand == "xlp"` and a unique canonical `id` equal to `xlp.<layer>.<directory_name>`.
- **Remediation**: Set manifest `id` to `xlp.<layer>.<name>` and `brand` to `xlp`.

## Modularity (`MOD`)

### MOD-001

- **Title**: Component Manifest Schema Compliance
- **Waivable**: No (constitutional)
- **Governing ADR**: [ADR-0002](../adr/ADR-0002-modular-layered-plugin-topology.md)
- **Check**: Verifies every component directory across `core/`, `modules/`, `adapters/`, `plugins/`, and `tools/` contains a valid `module.manifest.json` (or `plugin.manifest.json`) passing strict JSON Schema validation and matching its parent layer directory.
- **Remediation**: Add or fix the component manifest to satisfy its layer schema.

### MOD-002

- **Title**: Strict Layer Dependency Boundaries
- **Waivable**: Yes (ADR-backed)
- **Governing ADR**: [ADR-0002](../adr/ADR-0002-modular-layered-plugin-topology.md)
- **Check**: Inspects both manifest `dependencies` and source-level imports (`#include`, Python `import`/`from`, JS/TS `import`/`require`, Rust `use`) against the allowed layer dependency matrix (`core` -> `core`; `modules` -> `core, modules`; `adapters` -> `core, modules`; `plugins` -> `core, modules, adapters`; `tools` -> `tools`) and strictly forbids direct cross-plugin imports.
- **Remediation**: Refactor shared code downward into `core/` or `modules/` and remove illegal cross-layer or cross-plugin imports.

### MOD-003

- **Title**: Acyclic Component Dependency Graph (DAG)
- **Waivable**: No (constitutional)
- **Governing ADR**: [ADR-0002](../adr/ADR-0002-modular-layered-plugin-topology.md)
- **Check**: Constructs the combined directed dependency graph from all manifests and source imports and rejects any directed cycle (`A -> B -> ... -> A`).
- **Remediation**: Break circular dependencies by inverting control or extracting shared abstractions into a lower-layer module.

### MOD-004

- **Title**: Manifest-to-Source Dependency Parity
- **Waivable**: Yes (ADR-backed)
- **Governing ADR**: [ADR-0002](../adr/ADR-0002-modular-layered-plugin-topology.md)
- **Check**: Verifies every internal XLP component imported in production source code is explicitly listed in that component's manifest `dependencies`, and every declared internal `xlp.*` dependency resolves to an existing component.
- **Remediation**: Synchronize manifest `dependencies` with actual source imports.

### MOD-005

- **Title**: DSP, UI, and Format Adapter Separation
- **Waivable**: Yes (ADR-backed)
- **Governing ADR**: [ADR-0002](../adr/ADR-0002-modular-layered-plugin-topology.md)
- **Check**: Requires every plugin to separate `dsp/` and `ui/` directories, prohibits UI headers (`juce_gui_basics`, `visage`, `imgui`, `webview`, `ui/`) inside DSP source files, and prohibits raw DSP signal-processing patterns inside `adapters/`.
- **Remediation**: Isolate DSP math in `dsp/` / `modules/`, UI rendering in `ui/`, and host protocol translation in thin `adapters/`.

### MOD-006

- **Title**: Source File Cohesion Ceiling
- **Waivable**: Yes (ADR-backed)
- **Governing ADR**: [ADR-0002](../adr/ADR-0002-modular-layered-plugin-topology.md)
- **Check**: Rejects production source files exceeding `policy.modularity.max_source_file_lines` (default 600 lines) to prevent monolithic god-files.
- **Remediation**: Split large files into cohesive, single-responsibility modules.

## Scalability & Real-Time Audio Safety (`SCA`)

### SCA-001

- **Title**: Real-Time Audio Thread Static Safety Analysis
- **Waivable**: No (constitutional)
- **Governing ADR**: [ADR-0003](../adr/ADR-0003-realtime-safety-and-verification-contract.md)
- **Check**: Strips comments and string literals from C/C++/Rust source files inside `dsp/`, `realtime/`, `audio_thread/`, or `kind: "dsp"` modules and flags forbidden blocking/allocating calls (`malloc`/`free`/`new`/`delete`/`make_unique`/`make_shared`, mutex/lock primitives, console/file I/O, thread spawn/sleep, `throw`, dynamic container growth `.push_back`/`.resize`/`.reserve`/`.insert`). Legitimate off-thread setup is scoped to named lifecycle functions (`prepare`, `prepareToPlay`, `activate`, `releaseResources`) or explicit `XLP_NON_RT_BEGIN`/`XLP_NON_RT_END` blocks.
- **Remediation**: Pre-allocate buffers during `prepare()`/`activate()` and use lock-free atomics or SPSC ring buffers for cross-thread communication.

### SCA-002

- **Title**: Real-Time & Lock-Free Threading Contract
- **Waivable**: Yes (ADR-backed)
- **Governing ADR**: [ADR-0003](../adr/ADR-0003-realtime-safety-and-verification-contract.md)
- **Check**: Requires every DSP module and plugin manifest to declare `realtime_contract` with `audio_thread_lock_free: true`, `audio_thread_alloc_free: true`, `denormal_protection: true`, `arbitrary_block_sizes: true`, mandatory sample rates (`44100`, `48000`, `96000`), and an approved lock-free `thread_communication` mechanism.
- **Remediation**: Implement and declare all mandatory real-time contract guarantees in the manifest.

### SCA-003

- **Title**: Quantitative Performance & Resource Budget
- **Waivable**: Yes (ADR-backed)
- **Governing ADR**: [ADR-0003](../adr/ADR-0003-realtime-safety-and-verification-contract.md)
- **Check**: Requires every DSP module and plugin manifest to declare `performance_budget` with realistic single-core CPU percentage (`0 < cpu <= 50%` at 48 kHz / 64-sample buffer), memory ceiling in MB, latency in samples, and a named `benchmark_target`.
- **Remediation**: Define explicit CPU, memory, latency, and benchmark targets in the manifest.

### SCA-004

- **Title**: Mandatory VST3 Target & Channel Layout Contract
- **Waivable**: Yes (ADR-backed)
- **Governing ADR**: [ADR-0003](../adr/ADR-0003-realtime-safety-and-verification-contract.md)
- **Check**: Requires every XLP plugin manifest to include `vst3` in `formats` and declare at least one explicit input/output bus entry in `channel_layouts`.
- **Remediation**: Add `"vst3"` to `formats` and specify valid `channel_layouts`.

## Extensibility (`EXT`)

### EXT-001

- **Title**: SemVer API & Integer ABI Versioning
- **Waivable**: Yes (ADR-backed)
- **Governing ADR**: [ADR-0004](../adr/ADR-0004-moddability-and-extensibility-contract.md)
- **Check**: Verifies every component manifest declares valid semantic versions for `version` and `api_version` and an integer `abi_version >= 1`.
- **Remediation**: Use strict SemVer strings (`MAJOR.MINOR.PATCH`) and a positive integer ABI version.

### EXT-002

- **Title**: Declarative Extension Points Registry
- **Waivable**: Yes (ADR-backed)
- **Governing ADR**: [ADR-0004](../adr/ADR-0004-moddability-and-extensibility-contract.md)
- **Check**: Requires every component manifest to include an `extension_points` array with unique IDs and requires every XLP plugin to expose at least 2 versioned extension points with explicit lifecycles.
- **Remediation**: Design and declare at least two uniquely identified, versioned extension points on every plugin.

### EXT-003

- **Title**: Declarative Parameter & State Schema Integrity
- **Waivable**: Yes (ADR-backed)
- **Governing ADR**: [ADR-0004](../adr/ADR-0004-moddability-and-extensibility-contract.md)
- **Check**: Validates every plugin's `params.json` against `governance/schemas/params.schema.json`, confirming matching `plugin_id` and `state_schema_version`, globally unique parameter `id` and uint32 `uid`, valid numeric bounds (`min < max` and `min <= default <= max`), and non-empty `choices` arrays for choice parameters.
- **Remediation**: Synchronize `params.json` with `plugin.manifest.json` and fix duplicate IDs, UIDs, or out-of-range defaults.

### EXT-004

- **Title**: Immutable Parameter & ABI Regression Guard
- **Waivable**: Yes (ADR-backed)
- **Governing ADR**: [ADR-0004](../adr/ADR-0004-moddability-and-extensibility-contract.md)
- **Check**: Compares every plugin's `params.json` against committed baselines in `governance/baselines/<plugin_id>.params.json`, rejecting state schema version regressions, silent parameter removals, and parameter UID reassignments.
- **Remediation**: Preserve existing parameter IDs/UIDs for DAW project recall, or publish a major breaking release with an ADR and updated baseline.

## Moddability (`MDD`)

### MDD-001

- **Title**: Mandatory Plugin Modding Surfaces & Conflict Resolution
- **Waivable**: Yes (ADR-backed)
- **Governing ADR**: [ADR-0004](../adr/ADR-0004-moddability-and-extensibility-contract.md)
- **Check**: Requires every XLP plugin manifest to set `modding.enabled = true`, expose at least 2 mod surfaces, and declare a deterministic `conflict_resolution` strategy (`deterministic_priority` or `explicit_load_order`).
- **Remediation**: Enable modding and declare at least two mod surfaces with deterministic conflict resolution.

### MDD-002

- **Title**: Mod Sandbox Isolation & Crash-Safe Fallback Contract
- **Waivable**: No (constitutional)
- **Governing ADR**: [ADR-0004](../adr/ADR-0004-moddability-and-extensibility-contract.md)
- **Check**: Verifies every plugin mod surface enforces unique IDs, `allow_filesystem: false`, `allow_network: false`, `rt_safe_enforced: true` on audio-sensitive surfaces (`dsp_graph`, `scripts`, `modulation_curves`), and an approved crash-safe `fallback_on_error` policy (`bypass_mod_and_warn`, `revert_default`, or `disable_mod_safely`).
- **Remediation**: Lock down mod surface capabilities and configure a non-crashing fallback behavior.

### MDD-003

- **Title**: Mod Pack Schema & Reference Mod Verification
- **Waivable**: Yes (ADR-backed)
- **Governing ADR**: [ADR-0004](../adr/ADR-0004-moddability-and-extensibility-contract.md)
- **Check**: Requires every plugin to bundle a valid reference mod pack at `modding.reference_mod_path` and validates all mod packs (bundled and under `mods/`) against `mod.manifest.schema.json`, blocking privileged capabilities, path traversal (`..`), missing entry files, undeclared target surfaces, or memory requests exceeding the target plugin's sandbox limit.
- **Remediation**: Ship a compliant reference mod pack with every plugin and ensure all mod packs stay within target sandbox budgets.

### MDD-004

- **Title**: Plugin Modding Documentation Completeness
- **Waivable**: Yes (ADR-backed)
- **Governing ADR**: [ADR-0004](../adr/ADR-0004-moddability-and-extensibility-contract.md)
- **Check**: Verifies every XLP plugin ships a substantive `docs/modding.md` (>= 40 words) explicitly documenting mod surfaces and sandbox limits.
- **Remediation**: Author complete modding documentation covering every surface, sandbox limit, and loading workflow.

## Ruthless Research (`RES`)

### RES-001

- **Title**: Research Dossier Frontmatter & Section Structure
- **Waivable**: Yes (ADR-backed)
- **Governing ADR**: [ADR-0005](../adr/ADR-0005-research-and-documentation-standards.md)
- **Check**: Verifies `docs/research/` contains at least one dossier matching `RES-XXXX-<slug>.md` with unique IDs, matching YAML frontmatter containing all 9 mandatory fields, and all 8 mandatory level-2 sections.
- **Remediation**: Follow `governance/templates/research-dossier.template.md` and populate all frontmatter fields and sections.

### RES-002

- **Title**: Verifiable Primary Reference & Bidirectional Citation Integrity
- **Waivable**: Yes (ADR-backed)
- **Governing ADR**: [ADR-0005](../adr/ADR-0005-research-and-documentation-standards.md)
- **Check**: Verifies every research dossier cites at least `min_citations` (3) verifiable primary references (URL, DOI, RFC, ISBN, or ISO) in `## References`, rejects uncited references in the bibliography, and rejects dangling inline `[N]` citations missing from `## References`.
- **Remediation**: Ensure every reference includes a verifiable primary locator and is cited inline with `[N]`.

### RES-003

- **Title**: Research Dossier Substantive Depth (Anti-Stub Gate)
- **Waivable**: Yes (ADR-backed)
- **Governing ADR**: [ADR-0005](../adr/ADR-0005-research-and-documentation-standards.md)
- **Check**: Verifies each of the 7 prose sections of every research dossier meets `policy.research.min_words_per_section` (25 words minimum) to prevent hollow stub headings.
- **Remediation**: Expand thin research sections with concrete technical analysis, trade-offs, and evidence.

### RES-004

- **Title**: Mandatory Research Linkage for Components & ADRs
- **Waivable**: Yes (ADR-backed)
- **Governing ADR**: [ADR-0005](../adr/ADR-0005-research-and-documentation-standards.md)
- **Check**: Verifies every component manifest (`research_refs`) and every ADR (`research_refs`) links to at least one existing `RES-XXXX` dossier in `docs/research/`.
- **Remediation**: Author grounding research dossiers and link their IDs in component manifests and ADRs.

## Ruthless Testing (`TST`)

### TST-001

- **Title**: Universal Component Test Suite Requirement
- **Waivable**: Yes (ADR-backed)
- **Governing ADR**: [ADR-0003](../adr/ADR-0003-realtime-safety-and-verification-contract.md)
- **Check**: Verifies every component declares a valid `testing` section with an existing test directory, a non-empty runnable `command`, and at least one recognized test file (`test_*.*`, `*_test.*`, `*Tests.*`).
- **Remediation**: Add a test directory, test files, and runnable command to the component manifest.

### TST-002

- **Title**: Layer-Specific Required Test Categories
- **Waivable**: Yes (ADR-backed)
- **Governing ADR**: [ADR-0003](../adr/ADR-0003-realtime-safety-and-verification-contract.md)
- **Check**: Verifies every component declares all required test categories for its architectural layer (`unit`, `adversarial`, `integration`, `schema` for tools; `unit`, `dsp_invariants`, `rt_safety`, `regression`, `fuzz` for core/modules; `unit`, `host_conformance`, `state_roundtrip` for adapters; plus `mod_loading` and `host_validation` for plugins) AND contains matching `@category: <name>` annotations inside its actual test files.
- **Remediation**: Implement real test cases for every missing category and tag each test file with `@category: <name>`.

### TST-003

- **Title**: Live Test Suite Execution Gate
- **Waivable**: No (constitutional)
- **Governing ADR**: [ADR-0003](../adr/ADR-0003-realtime-safety-and-verification-contract.md)
- **Check**: When invoked with `--run-tests` (mandatory in CI and `pre-push`), executes every component's declared `testing.command`, failing on non-zero exit codes, launch errors, or vacuous zero-test runs.
- **Remediation**: Fix all failing tests and ensure test discovery executes actual assertions.

### TST-004

- **Title**: End-to-End Rule Traceability & Adversarial Coverage
- **Waivable**: No (constitutional)
- **Governing ADR**: [ADR-0001](../adr/ADR-0001-xlp-governance-enforcement-gate.md)
- **Check**: Validates `governance/traceability.json` against its schema and verifies 100% of registered rules map to existing ADRs, existing Research Dossiers, existing check module paths, and actual positive + adversarial test functions present in `tools/xlp_gate/tests/`.
- **Remediation**: Update `governance/traceability.json` and implement missing positive or adversarial tests.

## Ruthless Documentation (`DOC`)

### DOC-001

- **Title**: Diátaxis Documentation Layout Integrity
- **Waivable**: Yes (ADR-backed)
- **Governing ADR**: [ADR-0005](../adr/ADR-0005-research-and-documentation-standards.md)
- **Check**: Verifies `docs/README.md` and all four Diátaxis quadrant directories (`tutorials/`, `how-to/`, `reference/`, `explanation/`) exist, contain substantive Markdown files, and contain zero misfiled `ADR-*.md` records.
- **Remediation**: Maintain all four Diátaxis quadrants and keep ADRs strictly under `docs/adr/`.

### DOC-002

- **Title**: MADR 4.0 ADR Validity & Live Enforced-By Binding
- **Waivable**: No (constitutional)
- **Governing ADR**: [ADR-0005](../adr/ADR-0005-research-and-documentation-standards.md)
- **Check**: Validates every `docs/adr/ADR-*.md` file for unique sequential naming, valid MADR 4.0 YAML frontmatter, all 7 mandatory sections, valid lifecycle status, and—for `accepted` ADRs—non-empty `enforced_by` pointing exclusively to live registered `xlp-gate` rule IDs.
- **Remediation**: Follow `governance/templates/adr.template.md` and bind accepted ADRs to live rule IDs.

### DOC-003

- **Title**: Component Documentation Completeness
- **Waivable**: Yes (ADR-backed)
- **Governing ADR**: [ADR-0005](../adr/ADR-0005-research-and-documentation-standards.md)
- **Check**: Verifies every component supplies all layer-mandated docs (`README.md`, `docs/architecture.md`, `docs/api.md`, `docs/testing.md`, plus `docs/modding.md` for plugins), each meeting the minimum substantive word count (`min_doc_words`).
- **Remediation**: Author complete documentation files for every component.

### DOC-004

- **Title**: 1:1 Rule-to-Reference Documentation Parity
- **Waivable**: Yes (ADR-backed)
- **Governing ADR**: [ADR-0005](../adr/ADR-0005-research-and-documentation-standards.md)
- **Check**: Verifies exact set equality between rule IDs registered in `xlp-gate` and `### <RULE-ID>` headings in `docs/reference/enforcement-rules.md`.
- **Remediation**: Document new rules or remove obsolete rule entries from `docs/reference/enforcement-rules.md`.

### DOC-005

- **Title**: Internal Markdown Link & Heading Anchor Integrity
- **Waivable**: Yes (ADR-backed)
- **Governing ADR**: [ADR-0005](../adr/ADR-0005-research-and-documentation-standards.md)
- **Check**: Scans root governance guides, `docs/**/*.md`, and component Markdown files and verifies every relative link resolves to an existing file and every `#anchor` matches an actual heading slug in the target file.
- **Remediation**: Fix broken relative paths or anchor slugs.

### DOC-006

- **Title**: Zero Placeholder & Unfinished Debt Policy
- **Waivable**: Yes (ADR-backed)
- **Governing ADR**: [ADR-0005](../adr/ADR-0005-research-and-documentation-standards.md)
- **Check**: Rejects unfinished placeholder markers (`TBD`, `TODO`, `FIXME`, `XXX`, `PLACEHOLDER`, `COMING SOON`, `LOREM IPSUM`, `FILL THIS IN`) across Markdown documentation, ADRs, research dossiers, templates, and governance/component JSON files.
- **Remediation**: Replace every incomplete placeholder with finished, verified content before committing.

## Governance & Anti-Tampering (`GOV`)

### GOV-001

- **Title**: Governance Meta-Schema Validation
- **Waivable**: No (constitutional)
- **Governing ADR**: [ADR-0001](../adr/ADR-0001-xlp-governance-enforcement-gate.md)
- **Check**: Validates `governance/policy.json`, `governance/brand.json`, `governance/waivers.json`, and `governance/traceability.json` against their strict JSON Schemas under `governance/schemas/`.
- **Remediation**: Correct schema violations in the governance JSON files.

### GOV-002

- **Title**: Enforcement Infrastructure Integrity (CI, Hooks, Docs)
- **Waivable**: No (constitutional)
- **Governing ADR**: [ADR-0001](../adr/ADR-0001-xlp-governance-enforcement-gate.md)
- **Check**: Verifies executable `./xlp-gate`, executable `.githooks/{pre-commit,commit-msg,pre-push}` and `scripts/install-hooks.sh`, `.github/workflows/xlp-gate.yml` running `--strict --run-tests` with zero `continue-on-error: true` bypasses, and root `README.md`, `AGENTS.md`, and `CONTRIBUTING.md` referencing `xlp-gate`.
- **Remediation**: Restore missing or modified enforcement hooks, CI steps, or root governance docs.

### GOV-003

- **Title**: Audited Waiver Validity & Expiration Enforcement
- **Waivable**: No (constitutional)
- **Governing ADR**: [ADR-0001](../adr/ADR-0001-xlp-governance-enforcement-gate.md)
- **Check**: Validates every entry in `governance/waivers.json`: unique ID, valid waivable `rule_id`, existing `ADR-XXXX`, justification >= 40 characters, duration <= 90 days, valid chronological ISO dates, and non-expired `expires_on >= today`.
- **Remediation**: Fix invalid waivers, resolve expired violations, and never attempt to waive constitutional rules.

### GOV-004

- **Title**: Constitutional Floor Anti-Tampering Protection
- **Waivable**: No (constitutional)
- **Governing ADR**: [ADR-0001](../adr/ADR-0001-xlp-governance-enforcement-gate.md)
- **Check**: Enforces hardcoded constitutional minimums inside `xlp-gate` so `governance/policy.json` cannot be silently edited to allow circular dependencies, cross-plugin imports, disabled RT-safety or modding checks, fewer than 3 research citations, fewer than 2 mod surfaces or extension points, source file ceilings > 800 lines, or removal of mandatory `non_waivable_rules`.
- **Remediation**: Restore all weakened fields in `governance/policy.json` to or above constitutional floors.
