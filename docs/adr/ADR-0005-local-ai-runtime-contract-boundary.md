# ADR-0005: Local AI Runtime Contract Boundary

## Status

Accepted

## Decision

Platform Core will declare the canonical Local AI Runtime service, its public interfaces, compatibility expectations, declared consumers, and governance boundary.

The Local AI Runtime remains the execution authority for local model hosting, provider abstraction, routing, embeddings, diagnostics, and execution-side context handling.

## Consequences

Platform Core can describe how the runtime should be consumed without absorbing runtime implementation logic. NEOS can later verify implementation reality against the declared contract boundary, and GAIA can route governed AI workloads through the runtime without depending on provider-specific details.
