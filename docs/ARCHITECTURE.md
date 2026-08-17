# Architecture

## Responsibilities

### Platform Core
Defines what the ecosystem **is**.

Owns declared project contracts, registries, dependency declarations, interface/service declarations, compatibility rules, standards, release metadata, deterministic graph generation and declared impact analysis.

### NEOS
Discovers, analyses, validates and reports whether the ecosystem is technically healthy and aligned.

Owns observed repository state, source inspection, build/test/doc/security evidence, drift detection, compliance, release readiness and observed impact.

### Gaia
Provides conversational understanding, context, recommendations and orchestration assistance.

Explains Platform Core declared state together with NEOS intelligence. Governed actions remain explicit.

### Command Centre
Provides the human-facing platform cockpit for discovery, launch, observe, summarise, notify and orchestrate.

Displays read-only Platform Core state and later NEOS health data. It is not the registry authority.

### Local AI Runtime
Provides local model execution, provider abstraction, model routing, embeddings, runtime diagnostics and execution-side context handling.

Consumes Platform Core declared contracts and is observed by NEOS. It is not the canonical registry authority and does not own GAIA reasoning or product control logic.

See [Architecture Governance v1](ARCHITECTURE_GOVERNANCE_V1.md) for the detailed declared-state model, role vocabulary, lifecycle distinctions, planned extraction handling, and validation rules.

## Rule

No one system should silently duplicate the authoritative data owned by another.

Platform Core owns contracts and registries.  
NEOS owns engineering analysis.  
Gaia owns conversational/intelligence interaction.  
Command Centre owns the primary operator experience.

## EAD-050 Constitutional Architecture Baseline

EAD-050 is the approved constitutional architecture baseline for the New Earth ecosystem.

The authority chain is:

1. **Platform Core** — declared architecture, identity, contracts, topology and governance authority.
2. **NEOS** — observed engineering truth, repository intelligence, evidence, health and drift.
3. **GAIA** — interpretation, prioritisation, recommendation and coordination.
4. **Local AI Runtime** — model execution and runtime services.
5. **CKCC / Librarian** — planned durable knowledge and retrieval authority.
6. **MCP / Tool Control** — planned governed tool-execution, approval and audit boundary.
7. **Command Centre** — thin operational front door.
8. **Command Dashboard** — founder and operations workspace; not architecture authority.
9. **Project Coherence Standard** and **Omega Mission Generator** — control infrastructure, not product architecture authorities.
10. **Backup Guardian** — protection and recovery boundary.
11. Product and domain systems remain specialist owners of their own product behaviour and data.

### Constitutional Rules

- Declared architecture belongs to Platform Core.
- Observed engineering truth belongs to NEOS.
- Interpretation and work preparation belong to GAIA.
- Model execution belongs to Local AI Runtime.
- Tool execution must move behind the MCP / Tool Control boundary when implemented.
- Durable cross-system knowledge must move behind the CKCC / Librarian boundary when implemented.
- Command Centre and Command Dashboard must not become duplicate architecture or engineering-intelligence authorities.
- Product repositories must not silently absorb shared platform authority.
- Shared capabilities are extracted only when multiple real consumers, common semantics, clear ownership and lower total complexity are demonstrated.
- Direct APIs and explicit contracts are preferred before introducing additional messaging infrastructure.
- Existing legacy, embedded and historical records are preserved until evidence supports consolidation or retirement.

This baseline governs subsequent repository reconciliation, NEOS ecosystem validation, GAIA integration, MCP implementation, CKCC/Librarian maturation and controlled simplification.
