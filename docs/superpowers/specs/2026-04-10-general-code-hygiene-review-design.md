# General Code Hygiene Review Design

Date: 2026-04-10
Project: Chorus
Scope: Moderate cleanup and general review across the existing codebase

## Goal

Run a full code hygiene pass across the current Chorus codebase, combining:

- a prioritized review of issues, risks, and weak spots
- a safe round of structural cleanup
- removal of obvious redundancy
- consistency improvements in typing, naming, module boundaries, and basic best practices

This pass should improve maintainability and clarity without turning into a large redesign.

## Non-Goals

This round will not:

- rewrite the product architecture from scratch
- introduce major new features
- change the intended pipeline behavior unless a small public adjustment is clearly justified
- expand test coverage broadly beyond what is needed to support touched areas

## Requested Change Limit

The user selected a moderate change level:

- hygiene and redundancy removal are in scope
- small API or CLI adjustments are allowed when they clearly improve design
- broad structural rewrites are out of scope

## Current Context

The codebase is already split into logical areas:

- `core` for execution and domain logic
- `db` for persistence
- `web` for HTTP and rendering
- `graph` and `agents` for orchestration
- `tests` for coverage

Initial review suggests the code is small and reasonably modular, but there are early signs of drift:

- inconsistent style and typing across files
- some blurred responsibility boundaries between runner, services, and web layer
- potentially unnecessary indirection, including dynamic imports
- lightweight duplication in payload construction and flow control
- comments that describe temporary intent without making behavior explicit

## Recommended Approach

Use a layer-guided cleanup.

This approach focuses on clarifying boundaries between `core`, `db`, `web`, and orchestration code instead of reorganizing the project around a new domain model or limiting changes only to failing tests.

Why this approach:

- it gives the best maintenance gain for the lowest structural risk
- it keeps cleanup aligned with the current architecture
- it supports small public improvements without triggering unnecessary churn

## Design Overview

### 1. Core Execution Contracts

Review and tighten the execution flow in `core/runner.py`.

Goals:

- make input validation explicit
- keep run lifecycle updates consistent
- reduce loosely shaped return payloads where practical
- ensure orchestration owns execution concerns, not transport concerns

Expected direction:

- centralize run status transitions more clearly
- reduce incidental coupling between persistence details and caller-facing payload assembly
- improve type clarity for run execution results

### 2. Persistence Layer Hygiene

Review `db/database.py` and `db/operations.py` as persistence-only modules.

Goals:

- keep persistence functions focused on storing and retrieving data
- remove vague or stale implementation comments
- normalize style and typing
- avoid embedding workflow decisions in DB helpers

Expected direction:

- make artifact persistence helpers more explicit
- preserve current behavior unless a defect or ambiguity is found

### 3. Web Layer Simplification

Review `web/app.py`, `web/services.py`, and payload/rendering helpers.

Goals:

- keep FastAPI endpoints thin
- move application logic out of endpoint bodies where appropriate
- reduce duplication between sync and background execution paths
- remove dynamic loading or dependency synchronization only if it does not serve a real testing or runtime purpose

Expected direction:

- consolidate payload building and run retrieval behavior
- simplify control flow around create-and-return semantics
- preserve the current public API shape unless a small adjustment is clearly justified

### 4. Graph and Orchestration Clarity

Review `graph.py` and related agent orchestration boundaries.

Goals:

- improve readability of routing rules
- standardize naming and comments
- reduce any unnecessary branching complexity
- keep state expectations explicit

Expected direction:

- cleaner conditional routing helpers
- fewer ambiguous comments
- no semantic pipeline rewrite in this round

### 5. CLI, Docs, and Test Alignment

Review CLI/documentation/test alignment with the actual code behavior.

Goals:

- make sure docs describe the current system accurately
- clean up obvious naming or output inconsistencies
- update touched tests where behavior or contracts become clearer

Expected direction:

- pragmatic fixes only
- no broad docs rewrite
- no speculative test expansion

## Validation Plan

Validation will be pragmatic and environment-aware.

Planned checks:

- inspect the main modules in each layer
- apply refactors with low to moderate risk
- run the existing tests if dependencies are available
- if runtime dependencies are missing, report that constraint explicitly
- perform local sanity checks on edited paths even if the full suite cannot run

## Key Risks

1. Implicit contract breakage between `core.runner`, `web.services`, and API endpoints.
2. Payload refactors accidentally changing data relied on by the UI or tests.
3. Import and initialization cleanup affecting sync versus background execution paths.
4. Over-cleaning small modules and introducing churn that does not buy clarity.

## Risk Controls

- preserve public payload fields unless a change is clearly justified
- prefer consolidation over abstraction
- keep changes local to existing layers
- avoid multi-step redesigns in this round
- verify touched behavior as directly as the environment allows

## Done Criteria

This effort is complete when:

- responsibilities between `core`, `db`, `web`, and orchestration are clearer
- obvious redundancy and ambiguous helpers are reduced
- typing, naming, and style are more consistent
- a prioritized review of issues and risks is available
- the final result includes both code changes and a concise review summary
- verification limits, if any, are stated explicitly

## Implementation Boundaries

Allowed:

- internal refactors
- helper consolidation
- improved typing and validation
- light API or CLI cleanup with strong justification
- updates to tests and docs in touched areas

Not allowed:

- broad architecture replacement
- new product scope
- speculative abstraction
- major public contract churn without necessity

## Expected Outcome

After this pass, the codebase should remain familiar but be easier to reason about:

- thinner transport layer
- clearer execution and persistence boundaries
- fewer incidental inconsistencies
- less redundancy in flow and payload handling
- a stronger baseline for future feature work and test-driven improvements
