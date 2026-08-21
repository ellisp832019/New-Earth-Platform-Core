# New Earth MCP Read-Only V1 Runtime Architecture and Threat Boundary

## Decision

**Status:** `PASS_WITH_CONTROLLED_DEFERRED_ITEMS`

This document is an architecture and threat-model decision only. It does not
implement an MCP client, MCP server, transport, authorization evaluator,
approval workflow, audit store, query executor, or write capability.

The frozen declarative authority is:

`NE-MCP-READONLY-V1-DECLARATIVE-2026-08-21`

The protected baseline tag is:

`mcp-readonly-v1-declarative-baseline`

Platform Core remains the authority for identity, contracts, capabilities,
topology, compatibility, and declarative policy. NEOS remains engineering-truth
authority. GAIA remains the future consumer/client owner. Command Centre may
surface runtime and governance summaries but is not a contract, engineering
truth, or inference authority.

## Inspection Evidence

Platform Core was inspected at baseline HEAD `11b1f95204ef5380d9f7f82eb7e9e009c3e32a56`
on `main`; `origin/main...HEAD` was `0 0` and the tree was clean. The required
tag resolves to the baseline commit. The closure document is present in HEAD.

The related folders were inspected read-only. NEOS and Command Centre are
folder-based deliveries without a Git directory at their inspected roots, so no
Git branch or dirty-state claim is made for them. No related repository was
modified.

### NEOS evidence

- Runtime language: Python.
- Service implementation: standard-library `ThreadingHTTPServer` in
  `src/neos/service/app.py`.
- CLI entrypoint: `neos service start`; the service calls `serve_service`.
- Default endpoint: `http://127.0.0.1:8765`.
- `create_service_server` rejects non-local hosts; the default host is
  `127.0.0.1`.
- Existing owner-PID watchdog can stop the service when its owner exits.
- Verified read routes include `GET /health` and
  `GET /projects/{project_id}/summary`.
- Existing test coverage uses a bounded HTTP client timeout of ten seconds for
  test requests. Runtime MCP timeouts must be stricter and independently
  bounded.
- Existing JSON responses include service version, API version, schema version,
  instance identity, project identity, health, and freshness-related data.

### GAIA evidence

- Runtime language/framework: Python, FastAPI, Uvicorn.
- Existing NEOS boundary: `gaia.governance_context.NEOS`-side client services.
- HTTP abstraction: `httpx` with `trust_env=False`.
- Default NEOS URL: `http://127.0.0.1:8765`.
- Existing configured timeout: `GAIA_NEOS_TIMEOUT_SECONDS`, default `3.0`.
- Existing configuration is environment/settings based and composed through GAIA
  service construction.
- Existing errors distinguish timeout and HTTP/request failures; future MCP
  errors must preserve this boundary rather than infer engineering truth.

### Command Centre evidence

Command Centre has NEOS integration, health probes, governance status/findings,
approval-oriented surfaces, process management, and audit-log concepts. Its
future MCP role is display and operational coordination only. It must not
evaluate itself as approver, replace Platform Core policy, or rewrite NEOS
observations.

## Canonical Runtime Identity Table

| Role | Canonical ID | Authority / note |
|---|---|---|
| GAIA client | `gaia-mcp-client` | Platform Core declaration; owner `gaia` |
| NEOS server | `neos-engineering-read-server` | Platform Core declaration; owner `neos` |
| NEOS manifest | `neos.engineering.read.manifest` | Declared server exposure |
| Capability | `neos.engineering.read` | Read-only capability |
| Tools | `neos.health.read`, `neos.project.summary.read` | Declared read tools |
| Resources | `neos.health`, `neos.project.summary` | Declared read resources |
| Queries | `neos.health.query`, `neos.project.summary.query` | Declared read queries |
| Consumption | `gaia.neos.engineering.read` | GAIA-to-NEOS consumption declaration |
| Discovery | `neos.engineering.read.local` | Deterministic local declaration |
| Allow policy | `gaia.neos.engineering.read.allow` | Declarative planned allowance |
| Deny policy | `gaia.neos.project.summary.deny` | Explicit deny example |
| Approval policy | `command-centre.elevated.read.approval` | Future approval surface |
| Invocation example | `gaia.neos.health.read.invocation.example` | Record contract example |
| Decision example | `gaia.neos.health.read.authorization-decision.example` | Record contract example |

No replacement identity is introduced. Project IDs must be resolved through
declared NEOS project mappings; display names must never be converted into IDs.

## Recommended Topology

### Options considered

| Option | Assessment |
|---|---|
| A: GAIA MCP adapter directly to existing NEOS HTTP | Smallest code path, but couples MCP semantics directly to the existing API and leaves provider enforcement ambiguous. |
| B: GAIA MCP client to a thin NEOS MCP adapter, then NEOS internal API | Slightly more work, but preserves MCP contracts, provider-side enforcement, test seams, rollback, and clean ownership. **Recommended.** |
| C: Separate local MCP gateway to NEOS HTTP | Adds a process, lifecycle, attack surface, and failure boundary without a V1 need. Deferred. |

### Decision

Use **Option B**:

`GAIA MCP client -> local stdio MCP adapter owned by NEOS -> existing NEOS read API/service layer`

The adapter is a thin provider boundary. It must not become a second NEOS truth
store, a general proxy, a shell, an arbitrary URL client, or a write gateway.

## Ownership and Lifecycle

- **NEOS MCP provider:** owned by the NEOS repository, adjacent to the NEOS
  service/provider boundary. Platform Core must not host it.
- **GAIA MCP client:** owned inside the GAIA runtime boundary or a clearly owned
  GAIA adapter module. Platform Core must not execute it.
- **Initial server lifecycle:** explicit NEOS-owned/manual developer process,
  later NEOS desktop/engine-manager ownership. GAIA must not silently spawn
  arbitrary processes.
- **Initial client lifecycle:** explicit GAIA startup configuration loads the
  pinned bundle, validates identity and compatibility, resolves deterministic
  discovery, verifies health, then permits only declared reads. Shutdown must
  disconnect and clear the ready state.
- **Command Centre lifecycle:** future status/approval/audit consumer; it does
  not own either MCP process in V1.

## Transport and Local Boundary

The recommended V1 runtime transport is **stdio**. It avoids a network listener,
LAN exposure, firewall changes, discovery broadcasts, and origin ambiguity while
matching the existing declarative `transport: stdio` choice.

Mandatory rules:

- No remote internet, LAN-wide listener, `0.0.0.0`, cloud broker, mDNS,
  broadcast discovery, or open WebSocket listener.
- If a later HTTP transport is justified, it must bind only to
  `127.0.0.1`/`localhost`, with no automatic firewall or UPnP changes.
- Any remote binding configuration fails closed before startup.
- Remote binding is not allowed: `FALSE`.

## Contract Delivery and Compatibility

Runtime components should consume a versioned, read-only installed contract
bundle generated or exported from Platform Core. A developer checkout must not
be a runtime dependency. The bundle must carry:

- baseline ID `NE-MCP-READONLY-V1-DECLARATIVE-2026-08-21`;
- schema versions;
- manifest version `1.0.0`;
- capability/tool/resource/query versions; and
- the compatibility rules for the supported baseline.

There is no `latest` resolution. Startup and connection fail closed when the
baseline, manifest, server version, capability versions, or target declarations
are unsupported or mismatched.

Discovery is deterministic local configuration only: load the declared
discovery record, validate server identity, transport, local scope, and pinned
endpoint/process configuration, then resolve exactly one expected provider.
There is no scanning, guessing, remote registry, or fallback provider.

## Policy, Approval, and Request Flow

GAIA may perform local prechecks, but the NEOS provider boundary must enforce
the final authorization decision. Unknown client, server, tool, query, resource,
unexposed target, missing policy, incompatible contract, unsafe/write contract,
or invalid project mapping is denied.

Ordinary approved reads do not require interactive approval in this baseline.
For a future `approval_required` result, the conceptual path is:

`GAIA request -> policy evaluation -> Command Centre approval surface -> approval decision -> NEOS provider enforcement`

GAIA cannot self-approve. Command Centre cannot bypass provider enforcement.

Safe project-summary flow:

1. Select canonical tool/query.
2. Validate input and contract target locally.
3. Resolve deterministic local discovery.
4. Verify NEOS identity, manifest, and compatibility.
5. Construct a bounded request with correlation identifiers.
6. NEOS validates client, exposure, authorization, project identity, and input.
7. NEOS maps only to an approved read API.
8. Return observed NEOS data with provenance, partial, and stale state intact.
9. Classify failures without fabricating engineering truth.
10. Create one authoritative provider-side invocation/result record in a future
    audit layer.

## Verified Endpoint Mapping

| MCP declaration | Verified NEOS mapping | Status |
|---|---|---|
| `neos.health.read` / `neos.health.query` | `GET /health` | Verified |
| `neos.project.summary.read` / `neos.project.summary.query` | `GET /projects/{project_id}/summary` | Verified |

No other current endpoint is mapped by this decision. The declared resource,
tool, and query schemas remain the source of response-shape requirements.

NEOS is the engineering truth authority. GAIA must not fabricate records,
convert missing to zero, convert partial to complete, convert stale to current,
overwrite NEOS data, or persist inference as authoritative truth. Partial and
stale flags pass through unchanged. Unsupported detail is reported as
unavailable/unsupported; empty entities are not invented.

## Timeout, Retry, and Failure Model

Use three bounded values in a future implementation: connection timeout of one
second, request timeout of three seconds, and an overall invocation deadline of
five seconds. Make them explicit configuration values with conservative maximum
limits; never wait indefinitely. Start with no automatic retries. If one retry is
later justified, it must be a single bounded retry for an idempotent read before
the overall deadline.

Map failures to the frozen classes where applicable:

`validation_error`, `authorization_denied`, `approval_missing`,
`server_unavailable`, `timeout`, `transport_error`, `contract_mismatch`, and
`execution_error`.

No additional failure class is required for the first implementation plan.

## Audit and Correlation Boundary

GAIA creates or receives a non-secret `correlation_id` for the request. The
provider creates the authoritative `invocation_id`, result, provenance, and
execution record. A policy evaluation produces an
`authorization_decision_id`; an approval workflow, only when required,
produces an `approval_id`. All identifiers flow through the result and future
Command Centre summary without credentials or sensitive payloads.

There must be one authoritative provider execution/result record, not competing
GAIA, Command Centre, and Platform Core audit databases. Persistent audit storage
is deferred. Minimal observability may expose availability, compatibility, last
successful read, last failure class, latency, and request count, but not secrets
or full sensitive project payloads.

## Credential and Prompt Boundaries

The minimum V1 credential model is the local process/user boundary plus explicit
identity and contract validation. No token infrastructure is invented for this
local-only slice. Stronger client authentication is a later controlled phase.

NEOS/project/repository content is untrusted data when passed to GAIA:

`data != instruction`

README, code, comments, issues, and engineering text must retain provenance and
must not become privileged GAIA instructions. Future adapters need context labels
and sanitization at the data-to-model boundary.

Read-only tools may map only to approved reads. They may not invoke shell,
arbitrary commands, arbitrary URLs, filesystem mutation, Git mutation, device
actuation, or hidden side effects.

## Threat Model

| Threat | Attack surface | Impact | Current control | Required runtime control | Residual risk |
|---|---|---|---|---|---|
| Malicious local process | Local stdio/process boundary | Spoofing or data disclosure | Local-first architecture | Explicit process ownership and future authentication | Local user compromise |
| Unexpected LAN exposure | Bind/configuration | Remote invocation | NEOS localhost validation | Fail closed on non-local binding; no firewall opening | Host compromise |
| Spoofed server/client | Identity and discovery | Unauthorized reads | Canonical IDs and policies | Verify pinned identity, owner, manifest, and process endpoint | Local impersonation |
| Contract mismatch | Bundle/manifest/version | Unsafe interpretation | Baseline and schema versions | Pin versions and deny incompatibility | Delayed upgrade coordination |
| Malformed or oversized request/response | MCP boundary | Crash/resource exhaustion | Existing JSON boundaries | Strict schemas, size limits, bounded parsing | Implementation bugs |
| Path traversal / command or shell injection | Tool parameters/provider mapping | Host compromise | No current MCP runtime | Allowlisted routes and typed project IDs; never shell | Future adapter defect |
| Arbitrary URL / SSRF | Provider/network mapping | Network pivot | Local-only target | No user-controlled URL; fixed local endpoint | Local service abuse |
| Timeout, hang, replay | Transport/invocation | Availability or duplicate reads | Existing bounded GAIA timeout | Deadline, no unbounded retry, idempotency policy | Partial observations |
| Policy bypass or self-approval | Client/approval flow | Unauthorized access | Declarative deny/approval contracts | Provider-side enforcement; GAIA cannot approve | Future policy defects |
| Audit tampering or secret leakage | Logs/records | Loss of traceability | Record contracts | Redaction, one authority, protected storage later | Host-level tampering |
| Stale/partial truth misrepresentation | Result mapping | Wrong engineering decision | NEOS provenance fields | Preserve state and provenance; no fabrication | Consumers may misunderstand |
| Prompt injection | Engineering data to GAIA | Unsafe model behavior | Read-only source boundary | Label untrusted data and sanitize context | Model interpretation risk |

Blocking threats before runtime implementation are unresolved provider-side
enforcement, any remote binding path, arbitrary command/URL capability, missing
baseline pinning, missing bounded timeouts, or missing rollback. They are
resolved at planning level here but remain implementation acceptance gates.

## Failure Containment and Rollback

- An MCP adapter failure must not stop NEOS core reads where isolation permits.
- A GAIA client failure must not affect NEOS.
- Missing Platform Core contracts causes fail-closed startup/connection, never
  improvised contracts.
- Command Centre unavailability may not block an already-authorized ordinary
  read, but an approval-required request must remain denied pending approval.
- Disable the GAIA adapter and NEOS adapter independently through an explicit
  feature/configuration gate.
- Existing direct NEOS operation remains available.
- The declarative baseline remains unchanged and no first-slice data migration
  is required.

## Hard No-Go Review

The following must remain true before each source-changing slice:

- server ownership is NEOS;
- client ownership is GAIA;
- transport is local-only and deterministic;
- contract baseline is pinned;
- project identity uses canonical mappings;
- no write operation is exposed;
- provider-side policy enforcement exists before enabling reads;
- no arbitrary command or URL path exists;
- timeouts are bounded;
- rollback is explicit; and
- runtime/contract compatibility is tested.

## Controlled Implementation Sequence

1. **MCP-02B:** design the versioned installed contract bundle/export.
2. **MCP-02C:** add a NEOS-owned read-only provider adapter skeleton with no
   enabled operations.
3. **MCP-02D:** implement and test the NEOS health read.
4. **MCP-02E:** implement and test the NEOS project-summary read and canonical
   project-ID mapping.
5. **MCP-02F:** add the GAIA-owned client adapter skeleton behind a disabled
   feature gate.
6. **MCP-02G:** integrate the GAIA health read.
7. **MCP-02H:** integrate the GAIA project-summary read.
8. **MCP-02I:** enforce provider-side policy and deny-by-default behavior.
9. **MCP-02J:** add correlation and invocation/decision record surfaces.
10. **MCP-02K:** add Command Centre read-only runtime status and approval
    display.
11. **MCP-02L:** execute cross-repository closure, rollback, and threat audit.

Each slice must use one source-changing branch per repository, preserve the
baseline tag, and provide a rollback point. Cross-repository work is parallel
only when the dependency contract is already frozen.

## Cross-Repository Change Plan

| Slice | Repository | Likely boundary | Test boundary | Rollback / dependency |
|---|---|---|---|---|
| MCP-02B | Platform Core | Export/bundle tooling or package boundary | Contract export and compatibility tests | Revert export only; baseline tag remains |
| MCP-02C-E | NEOS | Provider adapter and two verified reads | Adapter, endpoint mapping, deny/timeout tests | Disable adapter; depends on MCP-02B |
| MCP-02F-H | GAIA | Client adapter and read integrations | Client lifecycle, compatibility, provenance tests | Feature-gate client; depends on NEOS adapter |
| MCP-02I-J | Platform Core plus provider/client owners | Policy enforcement and correlation records | Cross-boundary policy/record tests | Disable runtime path; contracts remain frozen |
| MCP-02K | Command Centre | Status and approval display only | Display/unavailable/approval tests | Disable surface; no provider dependency |
| MCP-02L | All participating repositories | Closure evidence | Full cross-repository validation | Freeze or revert the runtime slice |

## Deferred Items

The following are controlled deferred implementation items, not permission to
expand scope: actual MCP protocol library selection, provider authentication,
production audit persistence, interactive approval transport, response size
limits, secret redaction implementation, prompt-context sanitization, and
cross-repository integration testing. No runtime source slice should begin until
the relevant hard no-go gate is evidenced.

## Final Boundary

Platform Core remains declarative authority. No MCP runtime, network listener,
tool execution, query execution, authorization engine, approval workflow, audit
database, or write capability is added by this architecture decision.
