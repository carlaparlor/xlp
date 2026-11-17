# XLP Enforcement Gate (`xlp.tools.xlp_gate`)

`xlp-gate` is the zero-dependency architectural fitness engine for the XLP VST plugin repository. It enforces all 39 governance rules across nine domains—Brand (`BRD`), Modularity (`MOD`), Scalability & Real-Time Safety (`SCA`), Extensibility (`EXT`), Moddability (`MDD`), Research (`RES`), Testing (`TST`), Documentation (`DOC`), and Governance (`GOV`).

## Quick Invocation

```bash
./xlp-gate check --strict --run-tests
./xlp-gate list-rules
./xlp-gate verify-hooks
```

## Documentation

- [Internal Architecture](docs/architecture.md)
- [Public API & Extension Points](docs/api.md)
- [Testing & Adversarial Self-Test Matrix](docs/testing.md)
- [Complete Rule Reference](../../docs/reference/enforcement-rules.md)
- [CLI Reference](../../docs/reference/cli-reference.md)
