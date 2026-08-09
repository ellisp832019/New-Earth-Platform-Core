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

## Rule

No one system should silently duplicate the authoritative data owned by another.

Platform Core owns contracts and registries.  
NEOS owns engineering analysis.  
Gaia owns conversational/intelligence interaction.  
Command Centre owns the primary operator experience.
