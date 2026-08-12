# Architecture Governance v1

Platform Core v1 governance is the declared architecture model for the New Earth ecosystem.

## Locked Ownership Model

- Platform Core answers what should exist and how it should connect.
- NEOS answers what technically exists and what is true.
- GAIA answers what it means and what should happen next.
- Command Centre is the thin front door.
- Command Dashboard is the visual operations layer and bridge surface.

## Role Vocabulary

Supported architecture roles are:

- PLATFORM
- ENGINEERING_INTELLIGENCE
- AI_SYSTEM
- SHELL
- OPERATIONS_UI
- PRODUCT
- LAB
- PROGRAMME
- ENGINE
- SERVICE
- TOOLING
- PROTOTYPE
- LEGACY
- REFERENCE

## Canonical State

The governance registry distinguishes canonical systems, canonical platform services, specialist canonicals, programmes, embedded systems, planned extractions, probable extractions, placeholders, prototypes, legacy systems, and reference or vendor material.

The registry also distinguishes repository identity from system identity so that an embedded or conceptual project can remain known to Platform Core without claiming a confirmed independent GitHub repository.

Local AI Runtime is modeled as a canonical platform service with a declared repository, public runtime interfaces, and consumer compatibility rules.

## Planned Extractions

Planned extractions are declared separately from active systems. They point back to a source system and must not be modeled as already active canonical repositories unless a dedicated repository truly exists and is declared as such.

An embedded system is different from a planned extraction: it is current, but still lives inside another repository boundary and does not yet have release independence.

## Validation Rules

The governance validator enforces:

- valid architecture roles and owners;
- canonical registration for canonical systems;
- controlled lifecycle and canonical-state combinations;
- successor declarations for legacy systems where known;
- resolved relationship targets where applicable;
- non-canonical ownership for reference and vendor material;
- unambiguous canonical project and repository ownership.

## Operator View

Use:

```powershell
new-earth-platform governance
new-earth-platform governance <id>
new-earth-platform planned-extractions
new-earth-platform validate
new-earth-platform doctor
```

`validate` checks the governance registry, existing project contracts, registries, compatibility rules, and project-level validations together. `doctor` reports a quick health summary without modifying anything.
