# ADR-0004: Lock The Ownership Model For Governance v1

Status: Accepted

## Decision

Platform Core owns declared architecture and governance truth. NEOS owns observed engineering truth. GAIA owns reasoning and human-facing recommendations. Command Centre owns the thin operator front door. The Command Dashboard owns visual operations and bridge surfaces.

## Why

The ecosystem needs a deterministic place where declared architecture is recorded without collapsing it into observation, reasoning, or operator UI concerns.

## Consequences

- governance validation can stay local and machine-readable;
- planned extractions can be declared without pretending they are active repos;
- legacy and reference material can remain visible without being treated as canonical;
- future NEOS, GAIA, and Command Centre work can consume a stable contract instead of guessing at the model.
