# MCP Resource and Query Contracts

Platform Core declares MCP resources and queries as read-only architecture metadata.

## What is declared

- A resource is a named, read-only declaration of a queryable MCP data surface.
- A query is a read-only, declarative shape bound to exactly one resource, capability, and MCP server identity.
- Ownership is declarative: `owner_system_id`, `server_id`, and `capability_id` must be explicit.

## Read-only boundary

- Resources must declare `read_only: true`.
- Queries must declare `read_only: true` and `side_effects: false`.
- Queries do not execute anything at Platform Core level.
- Write-like operations are not part of MCP v1.

## Contract separation

- Declared resource/query contracts are not runtime MCP execution.
- Registered resource/query relationships are not authorization.
- Input/output schema references are deterministic repository paths.
- Pagination, filtering, and sorting are declarative capability metadata only.

## Validation rules

- Server, capability, resource, query, and tool IDs are unique.
- Every server `declared_tools` entry must reference a real tool.
- Every server `declared_resources` entry must reference a real resource.
- Every capability `tool_ids` entry must reference a real tool.
- Every resource must reference a real capability and server.
- Every query must reference a real resource, capability, and server.
- Resource `query_ids` and tool `query_ids` must reference real queries.
- Query pagination, filtering, and sorting declarations must stay within supported shapes.
- Schema references must exist inside the repository.

## Boundary note

DECLARED != IMPLEMENTED  
REGISTERED != AUTHORIZED  
READ-ONLY CONTRACT != RUNTIME QUERY EXECUTION
