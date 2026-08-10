# Command Dashboard Integration Boundary

The Command Dashboard is the visual operations layer for the New Earth estate.

## Intended Scope

- status views;
- permissions;
- adapters;
- bridges;
- operator controls;
- read-only surfacing of Platform Core declarations;
- future surfacing of NEOS evidence.

## Not In Scope

- repository scanning;
- AI reasoning;
- authoritative registry writes;
- backend engines that should live in NEOS or Platform Core.

## Relationship To Platform Core

The dashboard consumes Platform Core declarations and will later consume NEOS evidence. It must not become a parallel source of truth.
