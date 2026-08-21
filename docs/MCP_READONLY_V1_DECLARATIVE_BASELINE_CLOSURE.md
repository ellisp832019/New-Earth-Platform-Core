# New Earth MCP Read-Only V1 Declarative Contract Baseline

## Baseline

- Baseline ID: `NE-MCP-READONLY-V1-DECLARATIVE-2026-08-21`
- Status: PASS / FROZEN
- Baseline HEAD: `e75aa9537d0a507a063aa28dc492fdf50016b42c`
- Branch: `main`
- Origin alignment before closure: `origin/main...HEAD = 0 0`

This document freezes the MCP-01A through MCP-01G declarative, read-only MCP V1 contract baseline after the MCP-01H closure audit and MCP-01H-FIX correction.

## Scope

Included controlled slices:

- MCP-01A: client and server identities
- MCP-01B: capabilities and tools
- MCP-01C: resources and queries
- MCP-01D: server manifest and exposure
- MCP-01E: client consumption and discovery
- MCP-01F: authorization and approval policies
- MCP-01G: invocation and authorization-decision records
- MCP-01H: closure audit
- MCP-01H-FIX: identity graph and record-validation correction

Platform Core is the declarative authority for MCP identities, contracts, topology, exposure, consumption, discovery, policy, approval requirements, provenance, and record shapes. The canonical MCP registry remains `registry/mcp.yaml`.

## Contract Graph

```text
GAIA MCP CLIENT
        |
        v
CLIENT CONSUMPTION
        |
        v
NEOS MCP SERVER
        |
        v
SERVER MANIFEST
        |
        v
READ-ONLY CAPABILITY
        |
        +--> TOOL
        |
        +--> QUERY
        |
        +--> RESOURCE
        |
        v
AUTHORIZATION POLICY
        |
        v
APPROVAL POLICY WHERE REQUIRED
        |
        v
INVOCATION / DECISION RECORD CONTRACTS
```

## Responsibilities

- Platform Core: declarative MCP contract, identity, topology, and policy authority.
- NEOS: future read-only engineering MCP provider and engineering truth.
- GAIA: future MCP client, requester, and consumer.
- Command Centre: future approval and audit operational surface.
- Dashboard: founder and operations UI; not MCP policy authority.

## Safety Invariants

- READ-ONLY FIRST
- DENY BY DEFAULT
- WRITE-CAPABLE MCP CONTRACTS = 0
- DECLARED != IMPLEMENTED
- REGISTERED != AUTHORIZED
- EXPOSED != EXECUTABLE
- DISCOVERED != CONNECTED
- ALLOW != ACCESS GRANTED
- APPROVAL REQUIRED != APPROVAL GRANTED
- INVOCATION RECORD != INVOCATION EXECUTION
- AUDIT CONTRACT != AUDIT LOG

The GAIA MCP client is declared but not implemented. The NEOS MCP server is declared but not running. Policies, approval requirements, invocation records, and authorization-decision records are declarative contracts only.

## MCP-01H Closure Evidence

The initial MCP-01H audit was BLOCKED by a disconnected MCP-01A server identity, five dangling target references, the absence of a canonical GAIA MCP client identity, and GAIA-labelled declarations resolving through the Platform Core client identity.

MCP-01H-FIX corrected the graph by consolidating the server identity onto the registered NEOS read-only server, removing the stale target references, registering a planned GAIA client identity, updating GAIA consumption/policy/record subjects, requiring explicit invocation type, and adding disconnected-identity and duplicate-record negative coverage.

Final MCP-01H result:

- STATUS: PASS
- ORPHAN IDENTITIES: 0
- DANGLING REFERENCES: 0
- DUPLICATE IDS: 0
- CLIENT CONSUMPTION GRAPH COHERENT: TRUE
- WRITE-CAPABLE MCP CONTRACTS: 0
- RUNTIME MCP CLIENT IMPLEMENTED: FALSE
- RUNTIME MCP SERVER IMPLEMENTED: FALSE
- AUTHORITY COLLISIONS: 0
- BLOCKERS: NONE
- READY TO FREEZE MCP DECLARATIVE V1: TRUE

## Runtime Exclusions

This frozen baseline does not include:

- runtime MCP server or client
- runtime network discovery
- runtime authorization enforcement
- runtime approval workflow
- audit persistence or an audit writer
- tool or query execution
- write capabilities
- repository mutation
- actuation or control
- runtime retries or polling
- secret or token infrastructure

## Controlled Future Work

Future work belongs to MCP-02, Controlled Read-Only Runtime Integration, and must not silently rewrite this frozen milestone. Potential later components include a NEOS read-only runtime adapter, GAIA MCP client adapter, local deterministic discovery resolver, runtime policy evaluation, Command Centre approval surface, audit persistence, correlation propagation, compatibility enforcement, and failure/recovery handling.

## Freeze Rule

This baseline is immutable as a historical architecture milestone. Future changes must occur through a new controlled MCP phase or slice. The frozen baseline must not be silently rewritten to match later implementation.
