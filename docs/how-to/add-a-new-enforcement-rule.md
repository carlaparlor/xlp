# How to Add a New Enforcement Rule to `xlp-gate`

`xlp-gate` enforces strict parity across code, documentation, ADRs, and tests. Adding a new rule requires updating five artifacts together so zero undocumented or untested rules can ever exist.

## Step 1: Implement and Register the Rule

1. Choose the appropriate domain module under `tools/xlp_gate/checks/` (e.g., `scalability_checks.py` for a new `SCA-005` rule).
2. Implement `check_<id>(ctx: GateContext) -> list[Finding]` returning crisp `Finding` objects with exact file paths, line numbers (when applicable), and actionable remediation strings.
3. Register the `RuleSpec` and checker function in that module's `register(registry: RuleRegistry)` function.

## Step 2: Document the Rule (`DOC-004`)

Add a matching `### <RULE-ID>: <Title>` section in [docs/reference/enforcement-rules.md](../reference/enforcement-rules.md) explaining severity, waivability, enforcement rationale, exact checks performed, and remediation guidance.

## Step 3: Bind to an Accepted ADR (`DOC-002`)

Add the new `<RULE-ID>` to the `enforced_by` frontmatter list of the governing accepted ADR in `docs/adr/` (or author a new MADR 4.0 ADR backed by a Research Dossier).

## Step 4: Write Positive and Adversarial Tests (`TST-004`)

Add at least two test methods in `tools/xlp_gate/tests/`:

- A **positive test** proving a compliant repository fixture triggers zero findings for `<RULE-ID>`.
- An **adversarial test** proving a deliberately broken fixture triggers `<RULE-ID>` explicitly.

## Step 5: Update Traceability & Verify (`TST-004`)

Add the rule entry to `governance/traceability.json` linking `rule_id`, `domain`, `adr_ids`, `research_ids`, `check_module`, `doc_anchor`, `positive_tests`, and `adversarial_tests`. Then execute:

```bash
./xlp-gate check --strict --run-tests
```
