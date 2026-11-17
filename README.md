# xlp

**XLP** is an audio software brand for a line of VST3 (and multi-format) plugins engineered from day one around four non-negotiable architectural pillars and three non-negotiable engineering disciplines:

- **Modular**: Strict five-layer acyclic monorepo (`core/`, `modules/`, `adapters/`, `plugins/`, `mods/`) with complete DSP, UI, and host-adapter separation.
- **Scalable**: Hard real-time audio safety (lock-free, allocation-free, denormal-safe, multi-sample-rate, arbitrary block sizes) backed by static analysis and explicit CPU/memory/latency budgets.
- **Extensible**: SemVer API/ABI contracts, declarative extension points, immutable parameter schemas (`params.json`), and versioned state migrations.
- **Moddable**: First-class sandboxed mod surfaces (`declarative_schema`, `lua_sandbox`, `wasm_sandbox`) with zero filesystem/network access, crash-safe fallbacks, and bundled reference mod packs on every plugin.
- **Ruthlessly Researched, Tested, and Documented**: Verifiable primary-source Research Dossiers, MADR 4.0 ADRs bound to live fitness checks, multi-tier automated test execution, and Diátaxis documentation.

## Strict Enforcement Gate (`xlp-gate`)

Every invariant above is enforced automatically by [`./xlp-gate`](tools/xlp_gate/README.md) across CLI runs, local Git hooks (`.githooks/`), and GitHub Actions CI (`.github/workflows/xlp-gate.yml`).

```bash
# Install local pre-commit, commit-msg, and pre-push enforcement hooks
./scripts/install-hooks.sh
./xlp-gate verify-hooks

# Run all 39 enforcement rules in strict mode + execute all test suites
./xlp-gate check --strict --run-tests

# List all registered rules across the 9 domains
./xlp-gate list-rules
```

## Documentation Hub

- [Documentation Index (Diátaxis)](docs/README.md)
- [Enforcement Rules Reference (all 39 rules)](docs/reference/enforcement-rules.md)
- [Manifest & Governance Schema Reference](docs/reference/manifest-schemas.md)
- [CLI Reference](docs/reference/cli-reference.md)
- [Research Archive](docs/research/README.md)
- [Architecture Decision Records](docs/adr/README.md)
- [Agent & Engineering Protocol](AGENTS.md)
- [Contributor Guide](CONTRIBUTING.md)
