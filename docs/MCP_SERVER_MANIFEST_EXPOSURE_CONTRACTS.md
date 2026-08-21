# MCP Server Manifest and Exposure Contracts

Platform Core server manifests are declarative descriptions of the MCP surface a server may expose. A manifest references one existing MCP server identity and a deliberate subset of the server's declared capabilities, tools, resources, and queries.

The exposure graph is `server -> capability -> tool` and `server -> capability -> resource -> query`. Every exposed object must belong to the manifest server and owner. Tools and resources must reference exposed capabilities. Queries must reference exposed resources and capabilities. Subset exposure is intentional: server ownership does not automatically expose every registered object.

MCP v1 remains read-only. Exposed tools must be `read_only: true` and `side_effects: false`; exposed resources must be `read_only: true`; exposed queries must be `read_only: true` and `side_effects: false`.

`transport` and `bind_scope` are controlled declarative values reused from the MCP server identity contract. They do not create listeners or sockets. Manifest lifecycle uses the existing contract values `planned`, `declared`, `active`, and `deprecated`; `exposure_mode` is limited to `declared`, `disabled`, and `planned`. Runtime health is deliberately absent.

SERVER DECLARED != SERVER RUNNING

TOOL EXPOSED != TOOL EXECUTED

RESOURCE EXPOSED != RESOURCE SERVED

QUERY EXPOSED != QUERY EXECUTED

EXPOSED != AUTHORIZED

MANIFEST != RUNTIME CONFIGURATION

Future runtime components may consume these contracts, but Platform Core does not probe, authorize, serve, or execute them.
