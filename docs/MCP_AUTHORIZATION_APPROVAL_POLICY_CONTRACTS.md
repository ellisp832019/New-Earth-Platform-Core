# MCP Authorization and Approval Policy Contracts

Platform Core authorization policies are declarative statements about what a future runtime may consider for an MCP interaction. They target canonical client subjects and explicit server, capability, tool, resource, and query IDs. A policy is not a runtime grant and does not execute or authorize a request.

MCP v1 is deny-by-default: if no matching authorization policy exists, the future runtime must deny the interaction. Effects are controlled as `allow`, `deny`, and `approval_required`. Explicit deny takes precedence over allow at equivalent or lower-precedence scope. Lower numeric priority values have higher priority. Validation detects obvious same-subject, same-target, same-priority conflicts but does not evaluate policies at runtime.

Approval policies declare an approval class, a canonical approver authority, a target scope, optional declarative expiry, and an audit obligation. Approval classes are `none`, `single_approval`, `elevated_approval`, and `explicit_founder_approval`. Expiry modes are `single_use`, `session`, and constrained `duration` declarations. No timer, workflow, approval record, or audit log is created here.

Self-approval is prohibited where the subject client is also the approver authority. Command Centre is the intended future approval and audit surface; Platform Core remains the declarative policy authority. GAIA is not self-approving.

Authorization cannot weaken MCP v1 read-only safety. Policies targeting unsafe tools, side-effecting queries, or non-read-only resources are rejected.

POLICY DECLARED != POLICY ENFORCED

ALLOW != ACCESS GRANTED

APPROVAL REQUIRED != APPROVAL GRANTED

APPROVAL GRANTED != TOOL EXECUTED

AUDIT REQUIRED != AUDIT RECORDED

The GAIA-to-NEOS example declares future read policy only. It does not modify GAIA or NEOS and does not create a token, session, authorization engine, approval workflow, or runtime connection.
