# Tutorial 01: Onboarding and Running `xlp-gate`

This learning-oriented walkthrough introduces the XLP enforcement workflow from a fresh checkout through running strict checks, inspecting rules, and verifying local Git hooks.

## Prerequisites

- Python 3.11 or newer (`python3 --version`).
- Git (`git --version`).
- Zero external Python packages are required—`xlp-gate` runs purely on the Python standard library.

## Step 1: Install and Verify Git Hooks

Install the versioned hooks stored in `.githooks/` into `.git/hooks/`:

```bash
./scripts/install-hooks.sh
./xlp-gate verify-hooks
```

You should see `[OK]` for `pre-commit`, `commit-msg`, and `pre-push`.

## Step 2: Inspect the Registered Rule Catalog

List every architectural, real-time safety, moddability, research, testing, and documentation rule currently enforced:

```bash
./xlp-gate list-rules
```

You can also filter by any of the nine domains (`brand`, `modularity`, `scalability`, `extensibility`, `moddability`, `research`, `testing`, `documentation`, `governance`):

```bash
./xlp-gate list-rules --domain scalability
```

## Step 3: Run the Full Strict Enforcement Gate

Execute all static checks plus live component test suites:

```bash
./xlp-gate check --strict --run-tests
```

To export a machine-readable JSON audit report:

```bash
./xlp-gate check --strict --run-tests --format json --json-out gate-report.json
```

## Step 4: Explore How Violations Are Reported

When a rule fails, `xlp-gate` prints the exact `RULE-ID`, file path, line number (where applicable), reason, and concrete remediation steps, returning exit code `1`. Every rule's full contract and remediation pattern is documented in the [Enforcement Rules Reference](../reference/enforcement-rules.md).
