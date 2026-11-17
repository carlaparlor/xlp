# Why Strict Enforcement Comes Before the First Plugin

Most audio software repositories adopt a "build features first, add tests and architecture rules later" trajectory. By the time the second or third plugin ships, DSP math is intertwined with GUI toolkits, undocumented parameters break saved DAW projects, audio-thread allocations cause intermittent glitches, and prose style guides are ignored under deadline pressure.

## Architectural Fitness From Commit One

Grounded in Neal Ford's evolutionary architecture principles ([RES-0004](../research/RES-0004-architectural-fitness-enforcement.md)), XLP reverses that sequence by constructing `xlp-gate` **before** authoring any audio plugin:

1. **Zero Architectural Debt at Inception**: Every module, adapter, plugin, and mod pack starts compliant via `./xlp-gate scaffold` and stays compliant on every commit via `.githooks/` and `.github/workflows/xlp-gate.yml`.
2. **Dogfooding Proves Practicality**: `xlp-gate` governs itself as `xlp.tools.xlp_gate` (`tools/xlp_gate/module.manifest.json`), verifying that the rules are crisp, fast, and ergonomically workable in day-to-day engineering.
3. **Adversarial Self-Testing Eliminates Vacuous Rules**: Because no plugins exist in `plugins/` yet, rules targeting `plugins/*` could easily pass vacuously while hiding bugs. `xlp-gate` solves this structurally by testing every single one of its 39 rules against both compliant and deliberately broken synthetic plugin/module/mod fixtures inside `tools/xlp_gate/tests/`.
4. **Constitutional Anti-Tampering**: Hardcoded minimum floors (`GOV-004`) and mandatory traceability (`TST-004`, `DOC-004`) ensure that rules cannot be quietly weakened or bypassed without deliberate architectural review and superseding ADRs.
