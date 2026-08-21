# MCP Audit and Invocation Record Contracts

Platform Core invocation and authorization-decision records define the minimum declarative shape a future runtime may use for provenance and audit. They are not historical events, are not written by Platform Core, and are not runtime authorization results produced by this repository.

Records carry stable IDs, correlation IDs, requester and target identity, policy references, timestamps, status, result and failure classifications, read-only safety markers, provenance, and partial/stale markers. Tool, query, and resource targets are checked against the existing MCP registry and server manifest. Client consumption and optional discovery provenance are checked when declared.

Authorization decision records describe a future policy-evaluation result. They do not evaluate policies here. Approval references describe a future relationship to an approval record; they do not create approval processing or lifecycle transitions.

Records are expected to be append-only and immutable once finalized. They must not contain tokens, passwords, API keys, secrets, raw credentials, or unrestricted secret-bearing blobs. `metadata` is intentionally limited to scalar values.

Partial and stale are independent truth markers. Partial does not automatically mean failure, stale does not mean empty, and missing data must not be reinterpreted as zero.

INVOCATION RECORD != INVOCATION EXECUTION

AUDIT CONTRACT != AUDIT LOG

AUTHORIZATION DECISION RECORD != RUNTIME AUTHORIZATION ENGINE

APPROVAL REFERENCE != APPROVAL WORKFLOW

AUDIT REQUIRED != AUDIT WRITTEN

Command Centre is the intended future approval/audit surface. GAIA and NEOS remain outside this repository's runtime boundary. The GAIA-to-NEOS examples are hypothetical declarative records only.
