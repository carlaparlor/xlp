---
id: ADR-0005
title: Enforce Ruthless Research Dossiers, MADR 4.0, and Diátaxis Documentation
status: accepted
date: 2026-11-15
deciders:
  - xlp-architecture
research_refs:
  - RES-0004
enforced_by:
  - RES-001
  - RES-002
  - RES-003
  - RES-004
  - DOC-001
  - DOC-002
  - DOC-003
  - DOC-004
  - DOC-005
  - DOC-006
---

# ADR-0005: Enforce Ruthless Research Dossiers, MADR 4.0, and Diátaxis Documentation

## Context and Problem Statement

XLP mandates that every architectural decision, DSP algorithm, plugin, and tool be researched and documented ruthlessly and extensively. Without structural verification, documentation decays into broken links, hollow stub files, uncited claims, orphaned ADRs, and forgotten placeholders. What documentation taxonomy and automated verification rules should enforce research and documentation rigor across the entire repository?

## Decision Drivers

- Every technical claim in research must be backed by verifiable primary references cited accurately inline.
- Every accepted architectural decision must trace both backward to research (`research_refs`) and forward to automated enforcement (`enforced_by`).
- Readers must be able to navigate tutorials, how-to guides, references, and explanations predictably.
- Broken internal links, undocumented enforcement rules, stub sections, and leftover placeholders must fail builds deterministically.

## Considered Options

1. Structured Research Dossiers (`docs/research/RES-*.md`) + MADR 4.0 ADRs (`docs/adr/ADR-*.md`) + Diátaxis four-quadrant documentation (`docs/{tutorials,how-to,reference,explanation}/`) enforced automatically by `RES-001`..`RES-004` and `DOC-001`..`DOC-006`.
2. Free-form wiki or unstructured Markdown files under `docs/`.
3. Auto-generated API comments only without architectural research or guides.

## Decision Outcome

Chosen option: Option 1 (Research Dossiers + MADR 4.0 + Diátaxis with automated `xlp-gate` checks), because combining orthogonal reader-focused quadrants with machine-checked citation integrity, link resolution, rule-doc parity, and anti-placeholder scanning guarantees living, trustworthy documentation.

## Consequences

- Positive: Every component, plugin, and accepted ADR is backed by substantive, verifiable research with bidirectional citation checks (`RES-001`..`RES-004`).
- Positive: Zero broken Markdown links or heading anchors (`DOC-005`), zero undocumented gate rules (`DOC-004`), and zero committed placeholder stubs (`DOC-006`).
- Negative: Authors must complete full documentation and research artifacts before merging rather than deferring documentation to later commits.
- Neutral: Templates in `governance/templates/` and scaffolding in `xlp-gate scaffold` reduce mechanical formatting effort.

## Confirmation

Compliance is verified continuously by `xlp-gate` rules:

- `RES-001`..`RES-004`: Frontmatter, eight mandatory sections, bidirectional citation verification (>= 3 verifiable references), per-section word depth, and component/ADR coverage.
- `DOC-001`..`DOC-006`: Diátaxis layout, MADR 4.0 validation with live `enforced_by` binding (`DOC-002` non-waivable), component doc completeness, 1:1 rule-to-reference parity, internal link/anchor validation, and zero forbidden placeholders.

## Pros and Cons of the Options

### Option 1: Research Dossiers + MADR 4.0 + Diátaxis with automated enforcement

- Good, because documentation quality, accuracy, and structural coherence are verified on every commit and PR.
- Good, because Diátaxis prevents conflating lookup reference tables with conceptual essays or beginner tutorials.
- Bad, because trivial stub files are strictly rejected until substantive prose and citations are authored.

### Option 2: Unstructured Markdown docs

- Good, because authors can write arbitrary files quickly.
- Bad, because navigation degrades rapidly, links rot, and research rationale disappears.

### Option 3: Code-comment-only documentation

- Good, because comments live beside functions.
- Bad, because cross-cutting DSP math, trade-offs, prior art, modding workflows, and architectural decisions cannot be captured adequately in inline comments.
