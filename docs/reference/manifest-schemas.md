# Manifest & Governance Schema Reference

All XLP governance files and component manifests are validated strictly against JSON Schemas (Draft 2020-12 core subset) stored in `governance/schemas/`.

## Schema Catalog

| Schema File | Target Document(s) | Governing Rules |
| --- | --- | --- |
| `governance/schemas/brand.schema.json` | `governance/brand.json` | `BRD-001`, `GOV-001` |
| `governance/schemas/policy.schema.json` | `governance/policy.json` | `GOV-001`, `GOV-004` |
| `governance/schemas/waivers.schema.json` | `governance/waivers.json` | `GOV-001`, `GOV-003` |
| `governance/schemas/traceability.schema.json` | `governance/traceability.json` | `GOV-001`, `TST-004` |
| `governance/schemas/module.manifest.schema.json` | `{core,modules,adapters,tools}/*/module.manifest.json` | `BRD-003`, `MOD-001`, `SCA-002`, `SCA-003`, `EXT-001`, `EXT-002` |
| `governance/schemas/plugin.manifest.schema.json` | `plugins/xlp_*/plugin.manifest.json` | `BRD-002`, `MOD-001`, `SCA-002`..`004`, `EXT-001`..`003`, `MDD-001`..`003` |
| `governance/schemas/mod.manifest.schema.json` | `mods/*/mod.manifest.json` and plugin reference mods | `MDD-003` |
| `governance/schemas/params.schema.json` | `plugins/xlp_*/params.json` | `EXT-003`, `EXT-004` |

## Supported Built-In JSON Schema Features

The zero-dependency validator (`tools/xlp_gate/schema_validator.py`) enforces:

- **Structural Keywords**: `type`, `required`, `properties`, `patternProperties`, `additionalProperties`, `items`, `minItems`, `maxItems`, `uniqueItems`.
- **Value Keywords**: `const`, `enum`, `minLength`, `maxLength`, `pattern`, `minimum`, `maximum`, `exclusiveMinimum`, `exclusiveMaximum`.
- **Combinators & References**: `allOf`, `anyOf`, `oneOf`, `not`, local `$ref` (`#/$defs/...`).
- **Custom & Standard Formats**: `semver` (`MAJOR.MINOR.PATCH` with optional prerelease/build), `date` (ISO-8601 `YYYY-MM-DD`), `uuid` (canonical 128-bit hyphenated UUID), and `uri` (`scheme://...`).

## Strictness Policy

Every schema sets `"additionalProperties": false` on top-level and nested objects so typos (such as `realtime_contracts` instead of `realtime_contract`) fail immediately rather than being ignored silently.
