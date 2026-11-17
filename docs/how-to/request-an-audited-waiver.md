# How to Request an Audited, Time-Boxed Waiver

Bypassing Git hooks (`--no-verify`) or weakening CI is strictly forbidden in XLP. When a legitimate, temporary engineering transition requires deferring a **waivable** rule on a specific path, record a formal waiver in `governance/waivers.json`.

## Rules That Can Never Be Waived

Constitutional safety and integrity rules listed in `policy.json` under `waivers.non_waivable_rules` (and hardcoded in `GOV-003`/`GOV-004`) can **never** be waived:

- `BRD-001` (brand specification validity)
- `MOD-001` (manifest schema compliance)
- `MOD-003` (acyclic dependency graph)
- `SCA-001` (real-time audio-thread safety)
- `MDD-002` (mod sandbox isolation and safe error fallbacks)
- `TST-003` and `TST-004` (live test execution and traceability completeness)
- `DOC-002` (MADR ADR validity and live `enforced_by` binding)
- `GOV-001` through `GOV-004` (governance meta-schemas, CI/hooks, waiver validity, constitutional floors)

## Steps to Record a Valid Waiver

1. Ensure an existing ADR (`ADR-XXXX`) documents why the temporary exception exists and the concrete exit plan.
2. Add an entry to `governance/waivers.json` conforming to `governance/schemas/waivers.schema.json`:

```json
{
  "id": "WAV-0001",
  "rule_id": "MOD-006",
  "target_path": "modules/legacy_fft/src/fft_kernel.cpp",
  "adr_id": "ADR-0002",
  "justification": "Temporary 30-day transition while splitting radix-4 SIMD tables into dedicated header files.",
  "created_on": "2026-11-15",
  "expires_on": "2026-12-15",
  "owner": "xlp-dsp-team"
}
```

3. Verify the waiver with `./xlp-gate check --strict --run-tests`. `GOV-003` automatically validates duration (<= 90 days), justification length (>= 40 characters), ADR existence, waivability, and expiration.
4. Once expired, `GOV-003` automatically fails the build until the underlying issue is fixed and the waiver is deleted.
