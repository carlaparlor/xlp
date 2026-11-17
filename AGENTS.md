# AGENTS.md — Mandatory XLP Engineering & AI Agent Protocol

Every human engineer and AI coding agent operating in the `xlp` repository MUST obey this protocol without exception.

## Core Mandate

1. **Brand**: All audio plugins belong to the `xlp` brand (`plugins/xlp_<slug>/`, `id: xlp.<slug>`, unique 4-char `plugin_code`, distinct 128-bit VST3 component and controller UUIDs).
2. **Architecture**: Every XLP plugin MUST be **modular, scalable, extensible, and moddable**, strictly obeying the five-layer acyclic topology (`core/` -> `modules/` -> `adapters/` -> `plugins/`, plus isolated `mods/`).
3. **Engineering Discipline**: Everything MUST be **researched, tested, and documented ruthlessly and extensively** before work is considered complete.
4. **Strict Enforcement**: `./xlp-gate check --strict --run-tests` is the authoritative gate. Never bypass hooks with `--no-verify`, never weaken `governance/policy.json` constitutional floors, and never add `continue-on-error: true` to CI.

## Mandatory Execution Sequence

Before writing production code for any new XLP module, adapter, plugin, or architectural change:

1. **Research First (`RES-001`..`RES-004`)**:
   - Investigate prior art, DSP mathematics, host standards, failure modes, and trade-offs using primary references.
   - Author or update a Research Dossier in `docs/research/RES-XXXX-<slug>.md` with >= 3 verifiable sources and 100% bidirectional inline citations (`[1]`, `[2]`, ...).
2. **Decide Explicitly (`DOC-002`)**:
   - Record architecturally significant decisions in `docs/adr/ADR-XXXX-<slug>.md` using MADR 4.0 format, linking `research_refs` and live `enforced_by` rule IDs.
3. **Scaffold & Contract (`MOD-001`, `EXT-001`..`EXT-003`, `MDD-001`..`MDD-003`)**:
   - Use `./xlp-gate scaffold <plugin|module|adr|research> <slug>` to generate compliant manifests, parameter schemas, docs, test layouts, and reference mod packs.
4. **Implement Cleanly (`MOD-002`..`MOD-006`, `SCA-001`..`SCA-004`)**:
   - Keep `core/` and `modules/` free of GUI and format-adapter dependencies.
   - Keep audio-thread paths (`dsp/`, `realtime/`) 100% free of heap allocations, locks, blocking I/O, thread sleeps, exceptions, and dynamic container growth.
   - Keep production source files cohesive (<= 600 lines).
5. **Test Ruthlessly (`TST-001`..`TST-004`)**:
   - Implement and tag (`@category: <name>`) every layer-mandated test category (including adversarial negative tests, DSP invariants, RT safety, state round-trip, and mod fault-isolation tests).
6. **Document Completely (`DOC-001`..`DOC-006`, `MDD-004`)**:
   - Update Diátaxis docs, component docs (`README.md`, `docs/architecture.md`, `docs/api.md`, `docs/testing.md`, and `docs/modding.md` for plugins), zero broken links, zero placeholder debt.
7. **Verify Strictly**:
   - Run `./xlp-gate check --strict --run-tests` and confirm exit code `0` with zero errors and zero warnings.

## Reference Links

- [Enforcement Rules Reference](docs/reference/enforcement-rules.md)
- [Architecture Pillars](docs/explanation/architecture-pillars.md)
- [Create a Compliant Plugin or Module](docs/how-to/create-a-compliant-plugin-or-module.md)
- [Request an Audited Waiver](docs/how-to/request-an-audited-waiver.md)
