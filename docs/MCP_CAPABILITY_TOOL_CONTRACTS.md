# MCP Capability and Tool Contracts

Platform Core declares MCP capability and tool contracts as read-only architecture metadata.

## What is declared

- A capability is a coherent read-only domain of functionality.
- A tool is a single read-only operation owned by exactly one capability and one MCP server identity.
- Ownership is declarative: `owner_system_id` and `server_id` must be explicit.

## Read-only boundary

- `mode` is `read_only`.
- `read_only` must be `true`.
- `side_effects` must be `false`.
- Write-like operations are not part of MCP v1.

## Contract separation

- Declared tool contracts are not runtime tool execution.
- Registered capability/tool relationships are not authorization.
- Input/output schema references are deterministic repository paths.
- Empty-input tools must still reference an explicit empty-input schema.

## Validation rules

- Capability IDs and tool IDs are unique.
- Every capability `tool_ids` entry must reference a real tool.
- Every tool must reference a real capability.
- Tool `server_id` and `owner_system_id` must match the owning capability.
- Operation classes are restricted to declared read-only categories.
- Schema references must exist inside the repository.

## Boundary note

DECLARED != IMPLEMENTED  
REGISTERED != AUTHORIZED  
READ-ONLY CONTRACT != RUNTIME TOOL EXECUTION
