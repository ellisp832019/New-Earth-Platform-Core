# MCP Client Consumption and Server Discovery Contracts

Client consumption declarations describe a client's intended dependency on one declared MCP server. They identify the expected server manifest and a deliberate subset of expected capabilities, tools, resources, and queries. Required and optional consumption are dependency semantics only; they do not define runtime failure behavior or authorization.

Consumption is checked against the server manifest. Expected objects must exist, belong to the target server, and be exposed by that manifest. Subset consumption is valid: a client may require two objects from a server that exposes ten.

Compatibility expectations use explicit SemVer values for the minimum server version, manifest version, and required capability versions. These are declarative checks and do not create a second version engine.

Discovery descriptors declare a controlled local-first way for a future runtime component to locate a server. Supported modes are `static`, `local_registry`, `stdio_command`, and `localhost_endpoint`. Transport and bind scope reuse the MCP identity vocabulary. Endpoint hints are restricted to localhost addresses; arbitrary command text is not accepted. Discovery priority is a non-runtime ordering declaration.

Discovery is not availability and does not probe, connect, launch, or execute anything.

CLIENT DECLARED != CLIENT RUNNING

SERVER DISCOVERABLE != SERVER AVAILABLE

SERVER DISCOVERED != SERVER CONNECTED

CONSUMPTION DECLARED != ACCESS AUTHORIZED

EXPECTED TOOL != EXECUTABLE TOOL

DISCOVERY CONTRACT != RUNTIME DISCOVERY

GAIA MCP CLIENT DECLARED != GAIA MCP CLIENT IMPLEMENTED

NEOS DISCOVERY DECLARED != NEOS MCP SERVER RUNNING

Platform Core declares the future GAIA-to-NEOS relationship only. It does not modify GAIA or NEOS and remains outside runtime connection and authorization boundaries.
